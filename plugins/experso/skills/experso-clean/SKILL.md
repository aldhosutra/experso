---
name: experso-clean
description: "Frees disk space by deleting experso data that has been consumed: downloaded videos, images, captions and transcripts already turned into insights. Use when the user asks to clean up experso data, delete downloaded videos, or remove experso working files. Never touches skills or insights."
compatibility: "Requires Python 3.10+."
---

# Clean experso data

Run every script from the workspace. `<X>` means the absolute path of the `experso-build` skill's `scripts/` folder: `<this skill's folder>/../experso-build/scripts`. Use the full path in each command, because shell variables may not persist between commands. If that folder is missing, only part of experso is installed: reinstall all the experso skills.

## Workflow

Get the **handle** (`python3 <X>/status.py` shows disk use per creator) and the level:

| Level | Deletes | Afterwards |
|---|---|---|
| default | cached files of every post whose insights exist | Refresh still works; it skips these posts |
| `--all` | the creator's whole `.experso/profiles/<handle>/` | A later refresh starts from zero: everything is downloaded, extracted and digested again |

1. Preview:

   ```bash
   python3 <X>/clean.py <handle> [--all] --dry-run
   ```

2. Tell the user the file count and size. **Stop until the user confirms.**
3. For `--all`, make sure **experso-audit** passes first.
4. Run the same command without `--dry-run`.

## Report to the user

Files deleted, space freed, and what remains.
