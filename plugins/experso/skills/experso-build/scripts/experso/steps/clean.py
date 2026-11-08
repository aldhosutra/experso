"""experso clean: delete data that has been consumed, deterministically.

    experso clean HANDLE [--dry-run]     delete cached files of every post whose insights
                                         are extracted (media, captions, metadata, transcripts)
    experso clean HANDLE --all [--dry-run]
                                         delete the whole .experso/profiles/HANDLE working folder
                                         (cache and state). Only allowed once the skills are built;
                                         afterwards a refresh starts from zero.

What counts as consumed: a post's downloaded media and transcripts become
insights in the extract step. Once its insights exist (state/_raw/<post>.json),
its cache files are no longer used by any later step: render works from _raw,
and refresh skips the post using the manifest. Posts not yet extracted keep
their files. Profile-level files (profile picture, profile metadata) go when
no unextracted post is left.
"""
import argparse
import json
import shutil
from pathlib import Path

from ..manifest import Manifest
from ..paths import Profile


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return str(n)


def size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0


def consumed_files(prof: Profile) -> tuple[list[Path], int]:
    """Cache files belonging to extracted posts, plus profile files when every
    post in the cache is extracted. Returns (files, number of unextracted posts)."""
    raw = prof.raw
    extracted = {p.stem for p in raw.glob("*.json")}
    files, owned = [], set()
    for f in sorted(prof.cache.iterdir()) if prof.cache.is_dir() else []:
        if not f.is_file():
            continue
        # post files are <post id>.<ext> or <post id>_<n>.<ext> (carousel items)
        post = next((pid for pid in extracted if f.name == pid or f.name.startswith(pid + ".")
                     or f.name.startswith(pid + "_")), None)
        if post:
            files.append(f)
            owned.add(f)
    others = [f for f in prof.cache.iterdir() if f.is_file() and f not in owned] if prof.cache.is_dir() else []
    pending = {f.name.split(".")[0] for f in others if f.name.endswith("_UTC.json")}
    if not pending:
        files += others  # only profile-level files are left
    return files, len(pending)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--all", action="store_true", help="delete the whole working folder (cache + state)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    prof = Profile(a.target)
    if not prof.home.exists():
        raise SystemExit(f"Nothing to clean: {prof.home} does not exist.")

    if a.all:
        if not prof.outputs.exists():
            raise SystemExit(f"Refusing: the skills for @{prof.handle} have not been built yet. Build "
                             "and audit them before deleting all working data.")
        total = size(prof.home)
        print(f"{'would delete' if a.dry_run else 'deleting'} {prof.home} ({human(total)}). "
              "A later refresh will download and extract everything again.")
        if not a.dry_run:
            shutil.rmtree(prof.home)
        return

    files, pending = consumed_files(prof)
    total = sum(f.stat().st_size for f in files)
    print(f"{len(files)} cached files of extracted posts, {human(total)}"
          + (f"; {pending} posts not extracted yet keep their files" if pending else ""))
    if a.dry_run:
        for f in files[:10]:
            print(f"  would delete {f.name}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        return
    for f in files:
        f.unlink()
    m = Manifest(prof)
    m.log("clean", files=len(files), bytes=total)
    m.save()
    print(f"deleted {len(files)} files, freed {human(total)}. State, insights and skills are untouched.")


def status(argv=None):
    """experso status [HANDLE]: posts per stage and disk use."""
    ap = argparse.ArgumentParser(prog="experso status")
    ap.add_argument("target", nargs="?")
    a = ap.parse_args(argv)
    from ..paths import Workspace
    for h in ([a.target] if a.target else Workspace().handles()):
        prof = Profile(h)
        m = Manifest(prof)
        posts = m.data["posts"]
        raw = prof.raw
        cats = [d for d in prof.insights.iterdir() if d.is_dir() and not d.name.startswith("_")] \
            if prof.insights.is_dir() else []
        n_ins = sum(1 for d in cats for f in d.glob("*.md") if not f.name.startswith("_")) + \
            sum(1 for f in prof.insights.glob("*.md") if not f.name.startswith("_")) if prof.insights.is_dir() else 0
        digests = len(list(prof.digest.glob("*.json"))) if prof.digest.is_dir() else 0
        skills = len(list(prof.skills_raw.glob("*.json"))) if prof.skills_raw.is_dir() else 0
        print(f"@{h}")
        print(f"  posts: {len(posts)} downloaded, {len(list(raw.glob('*.json')))} extracted")
        print(f"  insights: {n_ins} in {len(cats)} categories; digests: {digests}; "
              f"plan: {'yes' if prof.plan_file.exists() else 'no'}; skills written: {skills}")
        outs = json.loads(prof.outputs.read_text()) if prof.outputs.exists() else {}
        print(f"  skills in .agents/skills: {len(outs.get('skills', []))}")
        print(f"  disk: cache {human(size(prof.cache))}, state {human(size(prof.state))}, "
              f"insights {human(size(prof.insights))}")
