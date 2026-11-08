"""experso extract: have an LLM extract insights from every downloaded post
(caption + transcripts + slide images) into one Markdown file per insight.

    experso extract HANDLE [--extractor claude-code] [--model opus] [--workers 4]
                    [--limit N] [--only POST_ID ...] [--render-only]
    experso list extractors              # supported agent harnesses

The LLM does the extraction (default: Claude via Claude Code; also Codex,
OpenCode, Gemini CLI, Cursor, Copilot, ... or Ollama); this step only feeds
posts in parallel and saves results:
    .experso/HANDLE/state/insights/<date>_<code>_<nn>-<slug>.md   one file per insight
    .experso/HANDLE/state/insights/_raw/<post id>.json            full LLM output per post
Re-running skips posts that already have a _raw file. --render-only rebuilds the
.md files from _raw without the LLM or the cache (run `experso group` after it
to file them back into their categories).
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


from ..downloader import REGISTRY as DOWNLOADERS, get_downloader
from ..downloader.base import Post
from ..manifest import Manifest
from ..paths import Profile
from ..extractor import NAMES as EXTRACTORS, ALIASES, describe_all, get_extractor, default_harness, default_model

RATE_LIMIT = re.compile(r"\b429\b|rate.?limit|usage limit|quota|too many requests", re.I)

SECTIONS = [  # (field, heading, style)
    ("explanation", "Explanation", "text"),
    ("when_to_use", "When to use", "bullets"),
    ("why_it_works", "Why it works", "text"),
    ("steps", "Steps", "numbered"),
    ("rules", "Rules", "bullets"),
    ("templates", "Templates", "bullets"),
    ("examples", "Examples", "bullets"),
    ("mistakes", "Mistakes to avoid", "bullets"),
    ("evidence", "Evidence", "bullets"),
    ("quotes", "Quotes", "quotes"),
    ("related_concepts", "Related concepts", "bullets"),
]


def slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "insight"


def short_code(post) -> str:
    m = re.search(r"/p/([^/]+)/", post.url or "")
    return m.group(1) if m else post.id


def render(insight: dict, post, creator: str, extractor_label: str, n: int) -> tuple[str, str]:
    insight_id = f"{post.date}_{short_code(post)}_{n:02d}"
    fm = {
        "id": insight_id,
        "title": insight["title"],
        "type": insight["type"],
        "basis": insight["basis"],
        "found_in": insight["found_in"],
        "suggested_category": insight["suggested_category"],
        "tags": insight["tags"],
        "creator": creator,
        "source": {"post": post.id, "url": post.url, "date": post.date, "format": post.kind,
                   **post.metrics},
        "extracted_with": extractor_label,
    }
    lines = ["---"]
    for k, v in fm.items():  # JSON values are valid YAML
        if isinstance(v, dict):
            lines.append(f"{k}:")
            lines += [f"  {sk}: {json.dumps(sv, ensure_ascii=False)}" for sk, sv in v.items()]
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    lines += ["---", "", f"# {insight['title']}", "", insight["summary"].strip(), ""]
    for field, heading, style in SECTIONS:
        val = insight.get(field)
        if not val:
            continue
        lines += [f"## {heading}", ""]
        if style == "text":
            lines.append(val.strip())
        elif style == "numbered":
            lines += [f"{i}. {s}" for i, s in enumerate(val, 1)]
        elif style == "quotes":
            for q in val:
                lines += [f"> {q}", ""]
            lines.pop()
        else:
            lines += [f"- {s}" for s in val]
        lines.append("")
    return f"{insight_id}.md", "\n".join(lines)  # stable name: links never break on a reworded title


def write_post_insights(result: dict, post, creator: str, out_dir: Path) -> int:
    for old in out_dir.rglob(f"{post.date}_{short_code(post)}_*.md"):
        if not any(part.startswith("_") for part in old.relative_to(out_dir).parts[:-1]):
            old.unlink()  # replace this post's files (also inside category folders)
    for n, insight in enumerate(result["insights"], 1):
        name, text = render(insight, post, creator, result.get("_extractor", "?"), n)
        (out_dir / name).write_text(text, encoding="utf-8")
    return len(result["insights"])


def post_from_raw(raw: dict) -> Post:
    m = raw["_post"]
    return Post(id=m["id"], url=m["url"], date=m["date"], kind=m["kind"], caption="",
                metrics=m.get("metrics", {}))


def run(target, source="instagram", extractor="claude-code", model=None, workers=4,
        limit=None, only=None, render_only=False, cmd=None, timeout=1200):
    dl = get_downloader(source)
    profile = Profile(target).ensure()
    data, out_dir = profile.cache, profile.insights
    raw_dir = profile.raw
    raw_dir.mkdir(parents=True, exist_ok=True)

    if render_only:  # from _raw alone: works after `experso clean`
        total = 0
        for raw_f in sorted(raw_dir.glob("*.json")):
            raw = json.loads(raw_f.read_text())
            if "_post" in raw and (not only or raw["_post"]["id"] in only):
                total += write_post_insights(raw, post_from_raw(raw), target, out_dir)
        print(f"[extract] rendered {total} insights into {out_dir}", flush=True)
        return 0

    posts = list(dl.iter_posts(data))
    if only:
        posts = [p for p in posts if p.id in only]
    print(f"[extract] {len(posts)} posts in {data}", flush=True)

    todo = [p for p in posts if not (raw_dir / f"{p.id}.json").exists()]
    todo = [p for p in todo if p.caption or p.transcripts or p.images]
    if limit:
        todo = todo[:limit]
    model = model or default_model(extractor, "strong")
    ex = get_extractor(extractor, model=model, cmd=cmd, timeout=timeout)
    print(f"[extract] {len(todo)} to extract with {ex.label}, {workers} at a time", flush=True)

    start, done, failed, n_insights, cost = time.time(), 0, 0, 0, 0.0
    rate_limited = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(ex.extract, p, target): p for p in todo}
        for f in as_completed(futures):
            if f.cancelled():  # skipped after a rate limit
                continue
            p = futures[f]
            try:
                result = f.result()
                result["_extractor"] = ex.label
                result["_post"] = {"id": p.id, "url": p.url, "date": p.date, "kind": p.kind,
                                   "metrics": p.metrics}
                (raw_dir / f"{p.id}.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                k = write_post_insights(result, p, target, out_dir)
                done += 1
                n_insights += k
                cost += result.get("_cost_usd") or 0
                print(f"[extract] {done + failed}/{len(todo)} {p.id}: {k} insights, "
                      f"{len(result['image_text'])}/{len(p.images)} images read, "
                      f"{len(result['not_extracted'])} not extracted | {time.time() - start:.0f}s",
                      flush=True)
            except Exception as e:
                failed += 1
                print(f"[extract] {done + failed}/{len(todo)} FAILED {p.id}: {e!r}"[:600], flush=True)
                if RATE_LIMIT.search(str(e)):
                    print("[extract] rate/usage limit hit: stopping. Re-run the same command "
                          "later to continue; finished posts are skipped.", flush=True)
                    for other in futures:
                        other.cancel()  # not-yet-started posts; running ones finish
                    rate_limited = True

    manifest = Manifest(profile)
    for raw_f in raw_dir.glob("*.json"):
        manifest.mark(raw_f.stem, extracted=True)
    manifest.log("extract", posts=done, insights=n_insights, failed=failed)
    manifest.save()
    print(f"DONE in {time.time() - start:.0f}s: {done} posts, {n_insights} insights, "
          f"{failed} failed, ~${cost:.2f} API-equivalent cost"
          + (", stopped early on rate limit" if rate_limited else ""), flush=True)
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?")
    ap.add_argument("--list-extractors", action="store_true",
                    help="show every supported agent harness and whether it is installed")
    ap.add_argument("--source", default="instagram", choices=list(DOWNLOADERS))
    ap.add_argument("--extractor", default=default_harness(), choices=EXTRACTORS + list(ALIASES))
    ap.add_argument("--model", default=None, help="model for the harness (format is harness-specific)")
    ap.add_argument("--cmd", default=None, help="for --extractor custom: command template")
    ap.add_argument("--timeout", type=int, default=1200, help="seconds per post before giving up")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", nargs="*", default=None, help="post ids to (re)extract")
    ap.add_argument("--render-only", action="store_true")
    a = ap.parse_args(argv)
    if a.list_extractors:
        print(describe_all())
        return
    if not a.target:
        ap.error("target is required")
    sys.exit(run(a.target, a.source, a.extractor, a.model, a.workers, a.limit, a.only,
                 a.render_only, a.cmd, a.timeout))


if __name__ == "__main__":
    main()
