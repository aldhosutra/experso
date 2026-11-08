---
name: experso-dev-add-harness
description: "Adds a new agent harness, LLM backend or transcription engine to experso's code. Use when working in the experso repository and the user wants experso's LLM steps to run through another CLI, API or local model, or to transcribe with another engine."
---

# Add a harness, backend or transcriber

Needs: the tool, where it runs (OS, hardware, accounts), and a post with images to test on. Read [references/interfaces.md](references/interfaces.md) for what to implement.

## Workflow

```
- [ ] 1. Read the tool's real interface
- [ ] 2. Implement and register it
- [ ] 3. Test end to end
- [ ] 4. Document
```

**1. Read** its `--help` and current docs, and record the docs URL. Never guess flags.

**2. Implement** following the interfaces reference, with `tested=False`. Use the most restrictive tool, sandbox and permission flags it offers.

**3. Test** in a scratch workspace, from the repo root:

```bash
export EXPERSO_WORKSPACE=<scratch dir with a downloaded post>
X=plugins/experso/skills/experso-build/scripts
python3 $X/extract.py <handle> --extractor <name> [--model ...] --only <post-with-images>
```

Pass when the log shows `N/N images read` and `0 failed`. Then set `tested=True`. For a transcriber, run `ingest.py --transcriber <name> --max-items 2` and compare with an existing transcript. If a login or service is unavailable, leave `tested=False` and tell the user what to run later.

**4. Document** it in `README.md`. It should appear in `--list-extractors` or `--list-transcribers`. For model tiers, use **experso-dev-model-eval** and add its model names to experso-build's `references/harnesses-and-models.md`.

## Gotchas

- Never pass flags that let an LLM harness write files or run shell commands.
- A CLI that silently retries provider errors looks like a hang: test with a working model and a short `--timeout`.

## Report

The change, the test commands and results, and what wasn't tested.
