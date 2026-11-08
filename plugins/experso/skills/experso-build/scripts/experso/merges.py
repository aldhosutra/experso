"""Merge registry and skill ownership.

A merged skill combines several creators' skills (and optionally one of the
user's own skills, the "base") into one folder in .agents/skills/. Its state
lives in .experso/merges/<slug>/:

    merge.json          {"slug", "members": [{"handle", "plan_slug"}], "base": bool}
    merge_plan.json     the reviewed plan for the merged skill (one skill entry)
    merge_plan.html     its rendering
    writer.json         the writer's output
    outputs.json        files generated for it (stale detection)
    preview/            a merged skill awaiting approval (when it replaces a user skill)

Ownership is read from SKILL.md frontmatter metadata (flat strings):
    experso-version, experso-kind (generated | merged | improved), experso-creators ("a,b")
A skill without them belongs to the user and is never changed without a backup
and explicit approval.
"""
import json
import re
from pathlib import Path

from .paths import Workspace


def skill_meta(skill_dir: Path) -> dict | None:
    """experso metadata of a skill folder, {} for a user's own skill, None if absent."""
    f = skill_dir / "SKILL.md"
    if not f.exists():
        return {} if skill_dir.exists() else None
    head = f.read_text(encoding="utf-8")[:3000]
    fm = head.split("---", 2)[1] if head.startswith("---") else ""
    meta = dict(re.findall(r'^  (experso-[a-z]+): "([^"]*)"$', fm, re.M))
    if not meta:
        return {}
    meta["creators"] = [c.strip() for c in meta.get("experso-creators", "").split(",") if c.strip()]
    return meta


def merge_dir(ws: Workspace, slug: str) -> Path:
    return ws.experso / "merges" / slug


def all_merges(ws: Workspace) -> list[dict]:
    d = ws.experso / "merges"
    out = []
    for f in sorted(d.glob("*/merge.json")) if d.is_dir() else []:
        out.append(json.loads(f.read_text()))
    return out


def merged_into(ws: Workspace) -> dict[tuple[str, str], str]:
    """(handle, plan_slug) -> slug of the merged skill that absorbed it."""
    return {(m["handle"], m["plan_slug"]): g["slug"] for g in all_merges(ws) for m in g["members"]}
