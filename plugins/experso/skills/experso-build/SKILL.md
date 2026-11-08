---
name: experso-build
description: "Turns a creator's public profile (Instagram posts, reels and carousels) into reusable agent skills in .agents/skills, with evidence linked to the source posts. Use when the user wants skills built from a creator, influencer or expert's content, such as 'make skills from @handle' or 'learn @handle's expertise'. Not for a creator already built in this workspace: use experso-refresh."
compatibility: "Requires Python 3.10+, ffmpeg, network access and a logged-in agent CLI such as Claude Code, Codex or OpenCode. See experso-setup."
---

# Build skills from a creator's profile

Run every script from the workspace (the current directory; inside an experso repo clone, scripts use `<repo>/workspace/` on their own). `<X>` means the absolute path of this skill's `scripts/` folder. Use the full path in each command, because shell variables may not persist between commands.

## Before starting

1. Get the **handle**. Optional inputs: spoken language (`--language id`, default auto-detect), `--login <user>` for an Instagram account, a trial cap (`--max-items 20`).
2. If `.experso/profiles/<handle>/` exists, stop and use **experso-refresh**.
3. If experso has not run on this machine, use **experso-setup** first.
4. Tell the user the cost from [references/estimates.md](references/estimates.md) and get a go-ahead. For large profiles, offer a trial with `--max-items 20`.
5. On a harness other than Claude Code, read [references/harnesses-and-models.md](references/harnesses-and-models.md) and pass your strongest model to steps 2, 3, 4 and 5.

## Workflow

Copy this checklist and track it:

```
- [ ] 1. Ingest
- [ ] 2. Extract
- [ ] 3. Group
- [ ] 4. Plan, and the user approves it
- [ ] 5. Digest
- [ ] 6. Write
- [ ] 7. Audit passes
```

Every step skips finished work. If one stops on a usage limit or fails, see [references/troubleshooting.md](references/troubleshooting.md).

**1. Ingest.** Download and transcribe.

```bash
python3 <X>/ingest.py <handle> [--language xx] [--max-items N] [--login USER]
```

Pass when the last line reports `0 failed`. Read two transcripts to confirm the language and quality.

**2. Extract** insights from each post's caption, transcripts and images.

```bash
python3 <X>/extract.py <handle> --workers 3
```

Pass when the last line reports `0 failed` and each log line shows all images read (for example `10/10 images read`).

**3. Group** insights into categories.

```bash
python3 <X>/group.py <handle>
```

Pass when it prints `0 insights still unassigned`. Review the category sizes. A category inflated by one repeated pattern is fine, because the digest merges it. If a category is incoherent or far above 300 insights, edit `.experso/profiles/<handle>/state/_grouping/taxonomy.json` or re-run with `--redo-taxonomy`.

**4. Plan** the skills, merged by the output they produce.

```bash
python3 <X>/plan.py <handle>
python3 <X>/render.py <handle>
```

Show the user `.experso/profiles/<handle>/state/plan/skill_plan.html` (publish or preview it if your harness can, otherwise give the path). **Stop until the user approves.** Apply requested changes by editing `skill_plan.json`, then run `plan.py <handle> --check` until it prints `plan is valid`, re-render, and show it again.

Then run `python3 <X>/merge.py detect <handle>`. For each collision it reports, follow **experso-merge** through its plan step now (merging is the default). Its write step comes after step 6.

**5. Digest** each category once, deduplicating it.

```bash
python3 <X>/digest.py <handle> --workers 2
```

Pass when it reports `0 failed`. This is the heaviest step.

**6. Write** the skills.

```bash
python3 <X>/write.py <handle> --workers 3
```

Pass when it reports the skills assembled with no `FAILED` lines. `--assemble-only` regenerates all generated files without an LLM. If merges were planned in step 4, finish them now with **experso-merge**.

**7. Audit.** Use **experso-audit** for this handle, and fix every failure before reporting.

## Gotchas

- Never edit generated files under `.agents/`: the next build overwrites them and the audit reports the drift. Change the plan or re-run a step instead.
- Never delete `.experso/` state to retry a step. Re-run the same command.
- On a harness other than Claude Code, the digest needs your strongest model. A weaker one silently loses the creator's templates.

## Report to the user

- The skills created (the table in AGENTS.md's Experso section) and the workflows that chain them
- Posts, insights, categories, digest items, skills, and the audit result
- Anything unusual: failed posts, plan edits, collisions
- That **experso-clean** can now free the downloaded media

For the folder layout and ownership rules, read [references/workspace.md](references/workspace.md).
