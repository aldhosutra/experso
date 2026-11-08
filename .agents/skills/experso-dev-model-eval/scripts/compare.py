#!/usr/bin/env python3
"""Run one experso step for two harness:model candidates on identical input, and measure it.

Run from the repo root:
    python3 .agents/skills/experso-dev-model-eval/scripts/compare.py STEP HANDLE \
        --a claude-code:opus --b opencode:google/gemini-2.5-flash [sample option]

    STEP       sample option
    extract    --post POST_ID [--post ...]   needs that post's cache (not yet cleaned)
    taxonomy   (full input)
    assign     [--batch 150]                 both get the same taxonomy, first batch only
    plan       (full input)
    digest     --category SLUG               ideally one that fits a single chunk
    write      --skill SLUG

Each candidate works on its own scratch copy of the workspace (the real one is never
written). Prints a metric table, writes <out>/report.json, and prints where each candidate's
output is so the two can be read side by side. Metrics inform the decision; they don't make it.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path.cwd()
SCRIPTS = ROOT / "plugins/experso/skills/experso-build/scripts"
if not SCRIPTS.is_dir():
    sys.exit("Run from the experso repo root.")
sys.path.insert(0, str(SCRIPTS))
from experso.paths import Profile, Workspace  # noqa: E402


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def json_of(p):
    return json.loads(Path(p).read_text())


def run(script, args, ws):
    env = dict(os.environ, EXPERSO_WORKSPACE=str(ws))
    r = subprocess.run([sys.executable, str(SCRIPTS / f"{script}.py"), *args], env=env, capture_output=True,
                       text=True, cwd=ws)
    (ws / "compare.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        raise RuntimeError(f"{script}.py failed in {ws}: " + " | ".join(tail))


def template_probes(prof, category, section):
    out = []
    for f in (prof.insights / category).glob("*.md"):
        if f.name.startswith("_"):
            continue
        m = re.search(rf"## {section}\n\n(.*?)(\n## |\Z)", f.read_text(), re.S)
        for line in (m.group(1).splitlines() if m else []):
            w = norm(re.sub(r"^(- |\d+\. )", "", line)).split()
            if len(w) >= 6:
                out.append(" ".join(w[:6]))
    return out


def survival(probes, text):
    hit = sum(p in text for p in probes)
    return f"{hit}/{len(probes)} ({100 * hit // max(1, len(probes))}%)"


# ------------------------------------------------- one prepare + run + measure per step

def do_extract(prof, a, flags):
    for p in a.post:
        (prof.raw / f"{p}.json").unlink(missing_ok=True)
    run("extract", [prof.handle, "--only", *a.post, "--workers", "2", *flags], prof.ws.root)
    raws = [json_of(prof.raw / f"{p}.json") for p in a.post]
    ins = [i for r in raws for i in r["insights"]]
    return {"insights": len(ins), "images read": sum(len(r["image_text"]) for r in raws),
            "not extracted": sum(len(r["not_extracted"]) for r in raws),
            "total chars": sum(len(json.dumps(i)) for i in ins),
            "_titles": [i["title"] for i in ins], "_text": norm(json.dumps(ins))}


def do_taxonomy(prof, a, flags):
    tflags = [x.replace("--model", "--taxonomy-model") for x in flags]
    run("group", [prof.handle, "--phase", "taxonomy", "--redo-taxonomy", *tflags], prof.ws.root)
    cats = json_of(prof.grouping / "taxonomy.json")["categories"]
    return {"categories": len(cats), "slugs": ", ".join(c["slug"] for c in cats)}


def do_assign(prof, a, flags):
    (prof.grouping / "assignments.json").unlink(missing_ok=True)
    run("group", [prof.handle, "--phase", "assign", "--max-batches", "1", "--batch", str(a.batch), *flags],
        prof.ws.root)
    got = json_of(prof.grouping / "assignments.json")
    return {"assigned": len(got), "_assign": got}


def do_plan(prof, a, flags):
    run("plan", [prof.handle, *flags], prof.ws.root)
    sk = json_of(prof.plan_file)["skills"]
    avg = lambda f: round(sum(map(f, sk)) / len(sk), 1)  # noqa: E731
    return {"skills": len(sk), "steps/skill": avg(lambda s: len(s["steps"])),
            "frameworks/skill": avg(lambda s: len({x for st in s["steps"] for x in st["frameworks"]})),
            "inputs/skill": avg(lambda s: len(s["input"])),
            "checks/skill": avg(lambda s: len(s["output"]["quality_criteria"])),
            "categories per skill": avg(lambda s: len(s["source_categories"]))}


def do_digest(prof, a, flags):
    (prof.digest / f"{a.category}.json").unlink(missing_ok=True)
    run("digest", [prof.handle, "--only", a.category, *flags], prof.ws.root)
    items = json_of(prof.digest / f"{a.category}.json")["items"]
    text = norm(" ".join(i["name"] + " " + i["content"] for i in items))
    return {"items": len(items), "chars": len(text),
            "templates verbatim": survival(template_probes(prof, a.category, "Templates"), text),
            "examples verbatim": survival(template_probes(prof, a.category, "Examples"), text)}


def do_write(prof, a, flags):
    (prof.skills_raw / f"{a.skill}.json").unlink(missing_ok=True)
    run("write", [prof.handle, "--only", a.skill, *flags], prof.ws.root)
    raw = json_of(prof.skills_raw / f"{a.skill}.json")
    sk = next(s for s in json_of(prof.plan_file)["skills"] if s["slug"] == a.skill)
    named = total = 0
    for st, body in zip(sk["steps"], raw["steps"]):
        for fw in st["frameworks"]:
            total += 1
            named += " ".join(norm(fw).split()[:3]) in norm(body["body"])
    return {"step body chars": sum(len(s["body"]) for s in raw["steps"]),
            "items linked": len({i for s in raw["steps"] for i in s["items"]}),
            "frameworks named in their step": f"{named}/{total}"}


STEPS = {"extract": do_extract, "taxonomy": do_taxonomy, "assign": do_assign, "plan": do_plan, "digest": do_digest,
         "write": do_write}
REQUIRED = {"extract": "post", "digest": "category", "write": "skill"}
OUTPUT = {"extract": "state/_raw/", "taxonomy": "state/_grouping/taxonomy.json", "assign": "state/_grouping/assignments.json",
          "plan": "state/plan/skill_plan.json", "digest": "state/digest/", "write": "state/plan/skills_raw/"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=list(STEPS))
    ap.add_argument("handle")
    ap.add_argument("--a", required=True, help="harness:model")
    ap.add_argument("--b", required=True, help="harness:model")
    ap.add_argument("--post", action="append")
    ap.add_argument("--category")
    ap.add_argument("--skill")
    ap.add_argument("--batch", type=int, default=150)
    ap.add_argument("--out", default=None, help="scratch folder (default: a new temp folder)")
    a = ap.parse_args()
    if REQUIRED.get(a.step) and not getattr(a, REQUIRED[a.step]):
        ap.error(f"{a.step} needs --{REQUIRED[a.step]}")

    src = Workspace(ROOT / "workspace")
    if a.step == "extract":
        missing = [p for p in a.post if not list(Profile(a.handle, src).cache.glob(p + "*"))]
        if missing:
            sys.exit(f"No cached files for {missing}: extraction can only be compared on posts not yet cleaned.")
    out = Path(a.out or tempfile.mkdtemp(prefix="experso-compare-")).resolve()
    results, errors, ignore = {}, {}, None
    if a.step != "extract":  # media is only needed to extract
        ignore = lambda d, names: ["cache"] if d.endswith(a.handle) else []  # noqa: E731

    def one(label, cand):
        harness, _, model = cand.partition(":")
        flags = ["--extractor", harness] + (["--model", model] if model else [])
        ws = out / label
        try:
            shutil.copytree(src.root, ws, symlinks=True, ignore=ignore, dirs_exist_ok=True)
            results[label] = STEPS[a.step](Profile(a.handle, Workspace(ws)).ensure(), a, flags)
        except Exception as e:
            errors[label] = str(e)

    ts = [threading.Thread(target=one, args=x) for x in (("a", a.a), ("b", a.b))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    if errors:
        sys.exit("\n".join(f"candidate {k}: {v}" for k, v in errors.items()))

    A, B = results["a"], results["b"]
    extra = {}
    if "_assign" in A:
        ids = sorted(set(A["_assign"]) & set(B["_assign"]))
        same = [i for i in ids if A["_assign"][i]["category"] == B["_assign"][i]["category"]]
        soft = [i for i in ids if i not in same and (B["_assign"][i]["category"] in A["_assign"][i]["also"]
                                                     or A["_assign"][i]["category"] in B["_assign"][i]["also"])]
        hard = [i for i in ids if i not in same and i not in soft]
        extra = {"primary agreement": f"{len(same)}/{len(ids)} ({100 * len(same) // max(1, len(ids))}%)",
                 "soft agreement": len(soft), "hard disagreements": hard}
    if "_titles" in A:
        def kept(titles, text):
            hits = 0
            for t in titles:
                w = [x for x in norm(t).split() if len(x) > 3]
                hits += sum(x in text for x in w) >= 0.6 * max(1, len(w))
            return f"{hits}/{len(titles)}"
        extra = {"a's ideas found in b": kept(A["_titles"], B["_text"]), "b's ideas found in a": kept(B["_titles"], A["_text"])}

    keys = [k for k in A if not k.startswith("_")]
    w = max(len(k) for k in keys + ["metric"])
    print(f"{'metric':<{w}}  {a.a:<34}  {a.b}")
    for k in keys:
        print(f"{k:<{w}}  {str(A[k]):<34}  {B[k]}")
    for k, v in extra.items():
        print(f"{k}: {v}")
    report = {"step": a.step, "a": a.a, "b": a.b, "metrics": {k: [A[k], B[k]] for k in keys}, "shared": extra}
    (out / "report.json").write_text(json.dumps(report, indent=1))
    for label, cand in (("a", a.a), ("b", a.b)):
        print(f"\n{cand} output: {out / label}/.experso/profiles/{a.handle}/{OUTPUT[a.step]}")
    print(f"report: {out / 'report.json'}\nNow read a sample of both outputs before deciding.")


if __name__ == "__main__":
    main()
