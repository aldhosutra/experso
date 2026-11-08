"""Audit a creator's skills in the workspace: deterministic, no LLM.

Checks the full chain  post <- insight <- digest item <- skill  and that every
generated file matches the approved plan, so nothing can silently go stale:

  workspace   AGENTS.md (and CLAUDE.md) carry the current experso section; .claude/skills
              resolves to every skill; .agents/skills/README.md lists them; .experso/ is ignored
  plan        every planned skill is built; SKILL.md frontmatter (name, description, metadata),
              inputs table, "### N. <step>" headings in order, output, quality checks and
              hand-offs match the plan exactly
  links       every relative link in the skills and the insight indexes resolves, including
              #anchors; every insight links to its source post
  chain       every insight is on file and in some digest item; every digest item is in some
              skill's references; no insight file without an assignment
  stale       every file in this creator's skill folders was produced by the last build
              (state/outputs.json), and every file listed there exists
  templates   verbatim survival of the insights' template lines in the skills' references

Usage:  python3 scripts/audit.py HANDLE [--min-template-survival 0.85]
Exit code 1 if any check fails; each failure says how to fix it.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from .. import __version__
from ..merges import all_merges, merge_dir
from ..paths import Profile

LINK = re.compile(r"\]\(([^)\s]+)\)")
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
FIX_ASSEMBLE = "re-run write.py HANDLE --assemble-only"


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def section(md: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1) if m else ""


def skill_drift(md: str, s: dict, h: str, kinds: list[str]) -> list[str]:
    """Differences between a SKILL.md and the plan entry it was generated from."""
    drift = []
    fm = md.split("---", 2)[1] if md.startswith("---") else ""
    want = {"name": s["slug"], "description": json.dumps(s["description"], ensure_ascii=False)}
    if f"\nname: {want['name']}\n" not in f"\n{fm}" or f"\ndescription: {want['description']}\n" not in fm:
        drift.append(f"{s['slug']}: frontmatter name/description")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s["slug"]) or len(s["slug"]) > 64 or len(s["description"]) > 1024:
        drift.append(f"{s['slug']}: name or description breaks the Agent Skills spec (name a-z0-9-, max 64; description max 1024)")
    kind = re.search(r'^  experso-kind: "([^"]*)"', fm, re.M)
    if f'  experso-version: "{__version__}"' not in fm or not kind or kind.group(1) not in kinds or not re.search(
            rf'^  experso-creators: "[^"]*\b{re.escape(h)}\b', fm, re.M):
        drift.append(f"{s['slug']}: experso metadata")
    rows = re.findall(r"^\| `([^`]+)` \|", section(md, "Inputs"), re.M)
    if rows != [i["name"] for i in s["input"]]:
        drift.append(f"{s['slug']}: inputs table")
    heads = re.findall(r"^### (\d+)\. (.+)$", section(md, "Workflow"), re.M)
    if heads != [(str(n), st["title"]) for n, st in enumerate(s["steps"], 1)]:
        drift.append(f"{s['slug']}: workflow step headings")
    out = section(md, "Output")
    if f"**Deliverable:** {s['output']['deliverable']}" not in out or \
            f"**Format:** {s['output']['format']}" not in out:
        drift.append(f"{s['slug']}: output")
    if re.findall(r"^- \[ \] (.+)$", section(md, "Quality checks"), re.M) != s["output"]["quality_criteria"]:
        drift.append(f"{s['slug']}: quality checks")
    if len(re.findall(r"^- ", section(md, "Hand-offs"), re.M)) != max(1, len(s["related_skills"])):
        drift.append(f"{s['slug']}: hand-offs")
    return drift


def check_links(files: list[Path], root: Path) -> list[str]:
    bad, anchors = [], {}
    for f in files:
        for target in LINK.findall(f.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            path, _, frag = target.partition("#")
            dest = (f.parent / path).resolve()
            if not dest.exists():
                bad.append(f"{f.relative_to(root)} -> {target}")
                continue
            if frag:
                if dest not in anchors:
                    anchors[dest] = set(ANCHOR.findall(dest.read_text(encoding="utf-8")))
                if frag not in anchors[dest]:
                    bad.append(f"{f.relative_to(root)} -> {target} (no such anchor)")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--min-template-survival", type=float, default=0.85)
    a = ap.parse_args(argv)
    prof = Profile(a.target)
    ws, h = prof.ws, prof.handle
    results = []

    def check(name, ok, detail="", fix=""):
        results.append((name, bool(ok), detail if ok else f"{detail} -> fix: {fix}".strip(" ->")))

    if not (prof.plan_file.exists() and prof.outputs.exists()):
        raise SystemExit(f"@{h} has no plan or no build yet in {ws.root}.")
    plan = json.loads(prof.plan_file.read_text())
    outs = json.loads(prof.outputs.read_text())
    built = set(outs["skills"])
    # merged skills this creator is part of: slug -> (merge.json, merge plan)
    merges = {g["slug"]: (g, json.loads((merge_dir(ws, g["slug"]) / "merge_plan.json").read_text()))
              for g in all_merges(ws) if any(m["handle"] == h for m in g["members"])
              and (merge_dir(ws, g["slug"]) / "merge_plan.json").exists()}
    absorbed = {m["plan_slug"]: g["slug"] for g, _ in merges.values() for m in g["members"] if m["handle"] == h}
    all_skills = built | {slug for slug in merges if (ws.skills / slug / "SKILL.md").exists()}

    # ------------------------------------------------------------ workspace
    marker = f"<!-- experso:begin v{__version__} -->"
    agents_md = ws.agents_md.read_text() if ws.agents_md.exists() else ""
    check("workspace: AGENTS.md has the current experso section", marker in agents_md,
          f"expected {marker}", FIX_ASSEMBLE)
    claude_ok = (ws.claude_md.is_symlink() and os.readlink(ws.claude_md) == "AGENTS.md") or \
        (ws.claude_md.is_file() and marker in ws.claude_md.read_text())
    check("workspace: CLAUDE.md is AGENTS.md or has the section", claude_ok, "", FIX_ASSEMBLE)
    missing_claude = [s for s in all_skills if not (ws.claude_skills / s / "SKILL.md").exists()]
    check("workspace: .claude/skills reaches every skill", not missing_claude, ", ".join(missing_claude),
          FIX_ASSEMBLE)
    readme = (ws.skills / "README.md").read_text() if (ws.skills / "README.md").exists() else ""
    unlisted = [s for s in all_skills if f"]({s}/SKILL.md)" not in readme]
    check("workspace: .agents/skills/README.md lists every skill", marker in readme and not unlisted,
          ", ".join(unlisted), FIX_ASSEMBLE)
    check("workspace: .experso/ is git-ignored", (ws.experso / ".gitignore").is_file(), "", FIX_ASSEMBLE)

    # ------------------------------------------------------------ plan conformity
    unbuilt = [s["slug"] for s in plan["skills"] if s["slug"] not in built
               and absorbed.get(s["slug"]) not in all_skills]
    check(f"plan: all {len(plan['skills'])} planned skills built" + (f" ({len(absorbed)} as merged skills)"
          if absorbed else ""), not unbuilt, ", ".join(unbuilt),
          "re-run write.py HANDLE")
    drift = []
    for s in plan["skills"]:
        if s["slug"] in built and (ws.skills / s["slug"] / "SKILL.md").exists():
            drift += skill_drift((ws.skills / s["slug"] / "SKILL.md").read_text(encoding="utf-8"), s, h,
                                 ["generated"])
    for slug, (g, mp) in merges.items():
        f = ws.skills / slug / "SKILL.md"
        if f.exists():
            md = f.read_text(encoding="utf-8")
            drift += skill_drift(md, mp["skill"], h, ["merged", "improved"])
            topics = re.findall(r"^### (.+)$", section(md, "Where the creators differ"), re.M)
            if topics != [d["topic"] for d in mp["disagreements"]]:
                drift.append(f"{slug}: 'Where the creators differ' section")
    check("plan: every SKILL.md matches its plan entry", not drift, "; ".join(drift[:8]),
          "re-run write.py HANDLE --assemble-only (or --only SLUG if the plan changed)")

    # ------------------------------------------------------------ links
    skill_files = [p for s in all_skills for p in (ws.skills / s).rglob("*.md")]
    index_files = list(prof.insights.glob("_categories.md")) + list(prof.insights.glob("*/_index.md"))
    bad = check_links(skill_files + index_files, ws.root)
    check(f"links: all links in {len(skill_files)} skill files and {len(index_files)} indexes resolve",
          not bad, "; ".join(bad[:6]), FIX_ASSEMBLE)
    insight_files = {f.stem: f for f in prof.insights.glob("*/*.md") if not f.name.startswith("_")}
    no_url = [i for i, f in insight_files.items() if not re.search(r'^  url: "https?://', f.read_text()[:3000], re.M)]
    check(f"links: every insight links to its source post ({len(insight_files) - len(no_url)}/{len(insight_files)})",
          not no_url, ", ".join(no_url[:6]), "re-run extract.py HANDLE --render-only, then group.py HANDLE")

    # ------------------------------------------------------------ chain
    asg = json.loads((prof.grouping / "assignments.json").read_text())
    missing_files = sorted(set(asg) - set(insight_files))
    check(f"chain: every insight is on file ({len(set(asg) & set(insight_files))}/{len(asg)})",
          not missing_files, ", ".join(missing_files[:6]), "re-run extract.py HANDLE --render-only, then group.py HANDLE")
    orphans = sorted(set(insight_files) - set(asg))
    check("chain: no insight file without an assignment", not orphans, ", ".join(orphans[:6]),
          "re-run group.py HANDLE (assigns or files them)")
    digests = {json.loads(p.read_text())["category"]: json.loads(p.read_text()) for p in prof.digest.glob("*.json")}
    cats = [c["slug"] for c in plan["categories"]]
    check("chain: every category has a digest", all(c in digests for c in cats),
          ", ".join(c for c in cats if c not in digests), "re-run digest.py HANDLE")
    in_digest = {s for d in digests.values() for it in d["items"] for s in it["sources"]}
    lost = sorted(set(asg) - in_digest)
    check(f"chain: every insight is in a digest item ({len(set(asg) & in_digest)}/{len(asg)})", not lost,
          ", ".join(lost[:6]), "re-run digest.py HANDLE --refresh")
    anchors = {i for s in built for f in (ws.skills / s / "references").glob("*.md")
               for i in ANCHOR.findall(f.read_text(encoding="utf-8"))}
    anchors |= {i.split("--", 1)[1] for s in merges for f in (ws.skills / s / "references").glob("*.md")
                for i in ANCHOR.findall(f.read_text(encoding="utf-8")) if i.startswith(h + "--")}
    item_ids = [it.get("id") for d in digests.values() for it in d["items"]]
    unused = [i for i in item_ids if i not in anchors]
    check(f"chain: every digest item is in a skill's references ({len(item_ids) - len(unused)}/{len(item_ids)})",
          not unused, ", ".join(map(str, unused[:6])), FIX_ASSEMBLE)

    # ------------------------------------------------------------ stale files
    listed = set(outs["files"])
    for slug in merges:
        mo = merge_dir(ws, slug) / "outputs.json"
        listed |= set(json.loads(mo.read_text())["files"]) if mo.exists() else set()
    actual = {p.relative_to(ws.root).as_posix() for s in all_skills for p in (ws.skills / s).rglob("*")
              if p.is_file()}
    check("stale: no file in these skills that the last build did not produce", not (actual - listed),
          ", ".join(sorted(actual - listed)[:6]), FIX_ASSEMBLE)
    check("stale: every file the last build produced exists", not (listed - actual),
          ", ".join(sorted(listed - actual)[:6]), FIX_ASSEMBLE)

    # ------------------------------------------------------------ template survival
    refs = norm(" ".join(f.read_text() for s in all_skills for f in (ws.skills / s / "references").glob("*.md")))
    probes = []
    for f in insight_files.values():
        m = re.search(r"## Templates\n\n(.*?)(\n## |\Z)", f.read_text(), re.S)
        if m:
            for line in m.group(1).splitlines():
                w = norm(re.sub(r"^(- |\d+\. )", "", line)).split()
                if len(w) >= 6:
                    probes.append(" ".join(w[:6]))
    hit = sum(1 for p in probes if p in refs)
    rate = hit / len(probes) if probes else 1.0
    check(f"templates: verbatim survival {hit}/{len(probes)} ({rate:.0%}, min {a.min_template_survival:.0%})",
          rate >= a.min_template_survival, "", "re-run digest.py HANDLE --only <category> for the weakest category")

    width = max(len(r[0]) for r in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {detail}".rstrip())
    failed = sum(1 for r in results if not r[1])
    print(f"\n{len(results) - failed}/{len(results)} checks passed for @{h} in {ws.root}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
