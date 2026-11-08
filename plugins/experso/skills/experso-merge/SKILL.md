---
name: experso-merge
description: "Merges overlapping agent skills into one that combines several experts' methods and records where they disagree, or improves one of the user's own skills with a creator's expertise. Use when asked to merge or combine skills, to improve a skill with a creator's methods, or when an experso build reports a name collision."
compatibility: "Requires Python 3.10+ and a logged-in agent CLI. See experso-setup."
---

# Merge skills

Run every script from the workspace. `<X>` means the absolute path of the `experso-build` skill's `scripts/` folder: `<this skill's folder>/../experso-build/scripts`. Use the full path in each command, because shell variables may not persist between commands. If that folder is missing, only part of experso is installed: reinstall all the experso skills.

## Workflow

Inputs: the **target skill** in `.agents/skills/` and each creator's skill to bring in, as `handle` or `handle:plan-skill` when the names differ. Each creator needs a plan here. Copy this checklist and track it:

```
- [ ] 1. Find overlaps
- [ ] 2. Plan the merge, and the user approves it
- [ ] 3. Write it
- [ ] 4. Audit passes for every creator in the merge
```

**1. Find overlaps.**

```bash
python3 <X>/merge.py detect <handle> [--suggest]
```

`--suggest` also finds skills that produce the same deliverable under different names; confirm those with the user. Merge by default. If the user wants to keep both, run `python3 <X>/merge.py separate <handle> <skill>`, which renames that creator's skill to `<skill>-<handle>`, then do what it prints.

**2. Plan the merge.**

```bash
python3 <X>/merge.py plan <target-skill> --member <handle>[:<plan-skill>] [--member ...]
```

The target's owner is included automatically. Show the user `.experso/merges/<target-skill>/merge_plan.html` (publish or preview it if your harness can, otherwise give the path). **Stop until the user approves.** It shows the merged steps and each disagreement, with guidance on when to use which side.

**3. Write it** (needs each creator's digest, so during a build do this after experso-build's write step).

```bash
python3 <X>/merge.py write <target-skill>
```

If the target is the user's own skill, this only creates a preview. Show the user `.experso/merges/<target-skill>/preview.diff`. **Stop until the user approves**, then add `--confirm`, which backs up the original to `.experso/backups/` and replaces it.

**4. Audit.** Use **experso-audit** for every creator in the merge.

## Gotchas

- Merging a user's own skill replaces it. Never pass `--confirm` before the user has seen the diff.
- On a harness other than Claude Code, pass your strongest model to `merge.py plan`: see [harnesses and models](../experso-build/references/harnesses-and-models.md).
- After a member creator refreshes, run `merge.py write <target-skill> --refresh`.

## Report to the user

The merged skill's path, its creators, the number of disagreements recorded, what was backed up, and the audit result.
