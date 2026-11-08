# Harnesses and models

The LLM steps run through an agent CLI. By default they use the harness that launched the script, else the first one installed. Override with `--extractor <name>` or by setting `$EXPERSO_HARNESS`. List them with `extract.py --list-extractors`.

## Which model for which step

Tests on real data showed some steps lose substance on a weaker model and others don't. On Claude Code the defaults below are automatic. On any other harness the harness's configured model is used unless you pass `--model`, so **pass your strongest available model to the "strong" steps**.

| Step | Tier | Claude Code default | Why |
|---|---|---|---|
| `extract.py` | strong | opus | A faster model keeps every idea but splits them less finely, so `--model sonnet` is an acceptable saving |
| `group.py` taxonomy (`--taxonomy-model`) | strong | opus | A weaker model produced categories mixing unrelated jobs |
| `group.py` assignment (`--model`) | fast | sonnet | 94% agreement with the strong model |
| `plan.py` | strong | opus | One call that everything downstream builds on |
| `digest.py` | strong | opus | A weaker model kept only 51–70% of templates verbatim, against 96% |
| `write.py` | fast | sonnet | Close to the strong model once the digest exists |
| `merge.py plan` | strong | opus | One call that the merged skill is built from |
| `merge.py write` | fast | sonnet | Same as `write.py` |

## Model names by harness

- Claude Code: `opus`, `sonnet`
- Codex: as in `codex` config, e.g. `--model gpt-5`
- OpenCode: `provider/model`, e.g. `--model google/gemini-2.5-flash`; list with `opencode models`
