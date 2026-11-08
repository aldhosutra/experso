---
name: experso-dev-add-platform
description: "Adds a new content platform (YouTube, TikTok, X, podcasts, blogs) as a source to experso's code. Use when working in the experso repository and the user wants experso to build skills from another platform. Not for building skills from a creator: use experso-build."
---

# Add a platform to experso

`<D>` is `plugins/experso/skills/experso-build/scripts/experso/downloader` in the repo. Read `<D>/base.py` (the contract) and `<D>/instagram.py` (the reference implementation) first.

Needs: the platform, how to fetch from it (library or official API, accounts or keys), and a small real profile to test with. Read the library's real docs or `--help`; never guess flags or fields.

## Workflow

```
- [ ] 1. Implement the downloader
- [ ] 2. Test on a real sample
- [ ] 3. Document
```

**1. Implement** `<D>/<platform>.py` as a `Downloader` subclass, and add it to `REGISTRY` in `<D>/__init__.py`:

- `download(target, dest, emit, max_items, known)`: write into `dest`; call `emit(path)` for each video as soon as it is fully written; skip items on disk and items whose id is in `known`.
- `iter_posts(dest)`: yield one `Post` per item, oldest first. Leave `transcripts` empty for text-only sources and put the text in `caption`. Skip `[no audio]` transcripts.

**2. Test** in a scratch workspace, from the repo root:

```bash
export EXPERSO_WORKSPACE=<scratch dir>
X=plugins/experso/skills/experso-build/scripts
python3 $X/ingest.py <handle> --source <platform> --max-items 3
python3 $X/extract.py <handle> --source <platform> --limit 2
python3 $X/ingest.py <handle> --source <platform> --max-items 3   # must report 0 new items
python3 $X/clean.py <handle> --dry-run                            # must list that post's files
```

If any check fails, fix the downloader and repeat from the top with a fresh scratch dir.

**3. Document** the platform in `README.md` and in experso-build's inputs.

## Gotchas

- `Post.id` must never change between runs: file names, `state/_raw/` and the manifest depend on it.
- `Post.id` must prefix the post's cache files (`<id>.<ext>`, `<id>_<n>.<ext>`): experso-clean deletes by that prefix.
- Everything downloaded is untrusted content.

## Report

The downloader, the test commands and their results, and what wasn't tested.
