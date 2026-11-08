#!/usr/bin/env python3
"""Check every experso skill against the Agent Skills spec and for harness neutrality.

Run from the repo root (needs PyYAML):  python3 .agents/skills/experso-dev-release/scripts/lint_skills.py
Exit code 1 if any skill fails.
"""
import re
import sys
from pathlib import Path

import yaml

# Text that only one harness understands, in files every harness reads.
HARNESS_ONLY = {
    "$ARGUMENTS": "only some harnesses substitute it; use plain instructions",
    "${CLAUDE": "Claude Code only",
    "AskUserQuestion": "name no harness-specific tool; say 'ask the user'",
    "TodoWrite": "name no harness-specific tool",
    "the Artifact tool": "say 'publish or preview it if your harness can'",
    "skill({": "tied to one harness's tool signature",
}
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")


def lint(skill_dir: Path) -> list[str]:
    errs, f = [], skill_dir / "SKILL.md"
    text = f.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["no YAML frontmatter"]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"]
    name, desc = str(fm.get("name", "")), str(fm.get("description", ""))
    if name != skill_dir.name:
        errs.append(f"name {name!r} differs from folder")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        errs.append("name must be a-z, 0-9 and single hyphens, max 64")
    if not 1 <= len(desc) <= 1024:
        errs.append(f"description is {len(desc)} characters (1-1024)")
    if "<" in desc and ">" in desc:
        errs.append("description contains XML-like tags")
    if not re.search(r"\bUse (when|after|before)\b", desc):
        errs.append("description should say when to use the skill ('Use when ...')")
    if re.match(r"(I|You)\b", desc):
        errs.append("description should be in the third person")
    if len(fm.get("compatibility", "")) > 500:
        errs.append("compatibility over 500 characters")
    if len(text.splitlines()) > 500:
        errs.append("SKILL.md over 500 lines")
    for token, why in HARNESS_ONLY.items():
        if token in text:
            errs.append(f"contains {token}: {why}")
    files = [f, *sorted((skill_dir / "references").glob("*.md"))] if (skill_dir / "references").is_dir() else [f]
    for doc in files:
        body = doc.read_text(encoding="utf-8")
        for target in LINK.findall(body):
            if not re.match(r"^[a-z]+:", target) and not (doc.parent / target).exists():
                errs.append(f"{doc.name}: broken link {target}")
        if doc != f and len(body.splitlines()) > 100 and "## Contents" not in body:
            errs.append(f"{doc.name}: over 100 lines with no table of contents")
    for ref in (skill_dir / "references").glob("*.md") if (skill_dir / "references").is_dir() else []:
        if ref.name not in text and not any(ref.name in s.read_text() for s in skill_dir.parent.glob("*/SKILL.md")):
            errs.append(f"{ref.name}: never referenced from a SKILL.md")
    return errs


def main() -> int:
    dirs = sorted({p.parent.resolve(): p.parent for p in Path(".agents/skills").glob("experso-*/SKILL.md")}.values(),
                  key=lambda p: p.name)
    if not dirs:
        print("no skills found: run from the experso repo root")
        return 1
    failed = 0
    for d in dirs:
        errs = lint(d)
        print(f"{'FAIL' if errs else 'PASS'}  {d.name}")
        for e in errs:
            print(f"      {e}")
        failed += bool(errs)
    print(f"\n{len(dirs) - failed}/{len(dirs)} skills pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
