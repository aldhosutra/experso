---
name: experso-audit
description: "Deterministically verifies a creator's experso skills: the whole chain from source post to insight to skill, every link, and conformity to the approved plan. Use after building, refreshing or merging experso skills, or when asked whether they are complete, correct or stale. Checks experso-generated skills only."
compatibility: "Requires Python 3.10+."
---

# Audit a creator's skills

Run every script from the workspace. `<X>` means the absolute path of the `experso-build` skill's `scripts/` folder: `<this skill's folder>/../experso-build/scripts`. Use the full path in each command, because shell variables may not persist between commands. If that folder is missing, only part of experso is installed: reinstall all the experso skills.

## Workflow

Get the **handle** (`python3 <X>/status.py` lists them). Audit each creator separately.

1. Run the audit:

   ```bash
   python3 <X>/audit.py <handle>
   ```

2. If any line says `FAIL`, run the command after its `fix:`.
3. Run the audit again. Repeat until the last line shows every check passed.

## Gotchas

- Never fix a failure by editing generated files. The next build overwrites the edit, and the audit reports it as drift. Fix the cause with the printed command.
- If the fix needs a re-digest or a rewrite, it uses the LLM and takes longer: tell the user first.

## What it checks

| Group | Must hold |
|---|---|
| workspace | AGENTS.md (and a separate CLAUDE.md) has the current experso section; `.claude/skills` reaches every skill; the README lists them; `.experso/` is git-ignored |
| plan | every planned skill is built; each SKILL.md's frontmatter, inputs, step headings, output, quality checks and hand-offs match the plan exactly; names and descriptions meet the Agent Skills spec |
| links | every link in the skills and insight indexes resolves, including `#anchors`; every insight links to its source post |
| chain | every insight is on file and in a digest item; every digest item is in a skill's references |
| stale | the skills' folders hold exactly the files the last build produced |
| templates | at least 85% of the creator's template lines survive verbatim |

## Report to the user

The final audit table, the fixes applied, and anything that remains failing.
