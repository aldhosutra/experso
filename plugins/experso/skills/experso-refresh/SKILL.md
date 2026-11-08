---
name: experso-refresh
description: "Updates a creator's existing experso skills with their newer posts, redoing only what changed. Use when the user asks to refresh or update a creator already built in this workspace, such as 'refresh @handle', 'pull in their new videos'. Not for a creator with no skills here yet: use experso-build."
compatibility: "Requires Python 3.10+, ffmpeg, network access and a logged-in agent CLI. See experso-setup."
---

# Refresh a creator's skills

Run every script from the workspace. `<X>` means the absolute path of the `experso-build` skill's `scripts/` folder: `<this skill's folder>/../experso-build/scripts`. Use the full path in each command, because shell variables may not persist between commands. If that folder is missing, only part of experso is installed: reinstall all the experso skills.

## Workflow

Get the **handle**. `python3 <X>/status.py` lists the creators in this workspace; if the handle isn't there, use **experso-build**. Copy this checklist and track it:

```
- [ ] 1. Ingest new posts
- [ ] 2. Extract and group them
- [ ] 3. Re-digest changed categories
- [ ] 4. Rewrite affected skills
- [ ] 5. Update merged skills
- [ ] 6. Audit passes
```

**1. Ingest.**

```bash
python3 <X>/ingest.py <handle>
```

Posts in the manifest are skipped, even after experso-clean. If it reports `0 new items`, stop and tell the user there's nothing new.

**2. Extract and group.**

```bash
python3 <X>/extract.py <handle> --workers 3
python3 <X>/group.py <handle>
```

New insights go into the existing categories. If many fit their category poorly, the creator may have started a new topic: tell the user and offer to re-plan (below).

**3. Re-digest** only the categories whose insight count changed.

```bash
python3 <X>/digest.py <handle> --refresh
```

**4. Rewrite** only the skills built from those categories.

```bash
python3 <X>/write.py <handle> --refresh
```

**5. Update merged skills** this creator is part of. List them with `ls .experso/merges/` and check each `merge.json`.

```bash
python3 <X>/merge.py write <skill> --refresh
```

**6. Audit.** Use **experso-audit** for this handle, and for every other creator in a skill updated in step 5.

## When the plan must change

Only for a new topic that no skill covers. Run `plan.py <handle>` (it keeps the previous plan with a timestamp) and `render.py <handle>`, have the user approve it as in experso-build, then run `write.py <handle>`.

## Gotchas

- On a harness other than Claude Code, pass your strongest model to `extract.py` and `digest.py`: see [harnesses and models](../experso-build/references/harnesses-and-models.md).
- If a step stops or hangs, see [troubleshooting](../experso-build/references/troubleshooting.md).

## Report to the user

New posts and insights, categories re-digested, skills rewritten, the audit result, and any sign that a re-plan is worthwhile.
