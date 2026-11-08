# Harness, backend and transcriber interfaces

All paths are under `plugins/experso/skills/experso-build/scripts/experso/`.

## Agent CLI: a `Harness` entry in `extractor/agent_cli.py`

| Field | Meaning |
|---|---|
| `binary`, `summary`, `docs` | The command, one line for the listing, and its docs URL |
| `tested` | `False` until the end-to-end test passes |
| `build` | `Call -> (argv, stdin)`. `Call` has `workdir`, `prompt`, `model`, `images`, `schema_file`, `out_file`, `schema`, `system` |
| `parse` | `(stdout, Call) -> reply text`, or a validated dict for native schema output |
| `images` | `path` (the agent opens `images/...`), `at` (`@images/...` references), `attach` (the command attaches them) |
| `native_schema` | The harness enforces a JSON Schema itself; otherwise it goes in the prompt and the reply is validated, with one retry |
| `system_flag` | The harness takes the system prompt separately; otherwise it is prepended |
| `notes` | Shown in `--list-extractors` |

Each call runs in a temp folder holding only the post's images. A harness that takes the prompt as an argument gets an empty stdin from the wrapper.

## Other LLM backend: an `Extractor` subclass

Implement `run_json(prompt, schema, system, images, image_label)` and `extract(post, creator)`, following `extractor/ollama_api.py`. Add it to `get_extractor()` in `extractor/__init__.py`.

## Transcription engine: a `Transcriber` subclass in `transcriber/`

Load models in `__init__`; `transcribe(media)` returns a `Transcript`. Add a `TranscriberInfo` to `transcriber/__init__.py` with OS, CPU, hardware, packages, programs and install command. The first entry whose requirements are met is the default.
