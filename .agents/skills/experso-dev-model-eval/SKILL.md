---
name: experso-dev-model-eval
description: "Compares models or harnesses on one experso pipeline step and sets the default from the evidence. Use when working in the experso repository and asking whether a cheaper model works for a step, comparing candidates such as claude-code:sonnet and codex:gpt-5, or choosing a default for a new LLM step."
---

# Evaluate a model for a pipeline step

Candidates are `harness:model` pairs on any harness, such as `claude-code:sonnet` or `opencode:google/gemini-2.5-flash`. Needs `workspace/` with the earlier steps done for the creator.

## Workflow

```
- [ ] 1. Run the comparison
- [ ] 2. Read real output side by side
- [ ] 3. Decide and record
```

**1. Compare**, from the repo root. The script copies the workspace once per candidate, runs the step on identical input, and prints the step's metrics.

```bash
python3 .agents/skills/experso-dev-model-eval/scripts/compare.py <step> <handle> --a <harness:model> --b <harness:model> [sample option]
```

| Step | Sample option |
|---|---|
| `extract` | `--post <post id>`, repeatable; the post must not be cleaned yet |
| `taxonomy`, `plan` | none: full input |
| `assign` | `--batch 150` |
| `digest` | `--category <slug>`, ideally one that fits a single chunk |
| `write` | `--skill <slug>` |

`merge` has no automated comparison: copy the workspace by hand and run `merge.py plan` with `EXPERSO_WORKSPACE` set to each copy.

**2. Read** a sample of both outputs (the script prints where they are). Numbers alone mislead: fewer items can mean better merging. [references/metrics.md](references/metrics.md) has what to look for per step and the results behind the current defaults.

**3. Decide.**

- Use the cheaper candidate when substance survives: only granularity or prose differs.
- Keep the stronger one when ideas, templates or steps are lost, or when the step is a single call that everything downstream builds on, where the saving is negligible.
- If a cheaper candidate is close, try one cheap fix (such as smaller chunks) and re-measure.

Record it: update the step's tier in `default_model`, the `--model` help text, the table in experso-build's `references/harnesses-and-models.md`, the pipeline table in `AGENTS.md`, and the results table in this skill's metrics reference.

## Gotchas

- Extraction can only be compared on posts whose cache hasn't been cleaned.
- Metrics compare the candidates; they can't tell you whether either output is good. Read them.

## Report

A table of metric by candidate, two or three side-by-side excerpts, the decision and why, and the changes made.
