---
name: experso-setup
description: "Checks and installs what experso needs on this machine: Python, ffmpeg, Python packages, a transcription engine and a logged-in agent CLI. Use before the first experso build, when an experso script reports a missing package or tool, or when asked whether experso is ready."
---

# Set up experso

`<X>` means the absolute path of the `experso-build` skill's `scripts/` folder: `<this skill's folder>/../experso-build/scripts`. If that folder is missing, only part of experso is installed: reinstall all the experso skills.

## Workflow

1. Check:

   ```bash
   python3 --version                           # needs 3.10 or newer
   ffmpeg -version | head -1
   python3 -c "import instaloader, jsonschema"
   python3 <X>/ingest.py --list-transcribers
   python3 <X>/extract.py --list-extractors
   ```

2. If the imports fail or no transcriber is available, tell the user what's missing, get a go-ahead, and create experso's own environment (scripts use it automatically):

   ```bash
   python3 -m venv ~/.experso/venv
   ~/.experso/venv/bin/pip install instaloader jsonschema
   ~/.experso/venv/bin/pip install mlx-whisper      # Apple Silicon Mac
   ~/.experso/venv/bin/pip install faster-whisper   # anything else
   ```

   Install ffmpeg with the system package manager (`brew install ffmpeg`, `apt install ffmpeg`).

3. Confirm one listed harness answers. Examples:

   ```bash
   echo "Reply OK" | claude -p --model sonnet
   codex exec "Reply OK"
   opencode run -m <provider/model> "Reply OK"
   ```

   If none is logged in, ask the user to log in (for example `claude`, `codex login`, `opencode auth login`).

4. Re-run step 1 until everything is available.

## Gotchas

- A sandboxed agent may block network access, which downloads and LLM steps need: see [troubleshooting](../experso-build/references/troubleshooting.md).
- On non-Claude harnesses, read [harnesses and models](../experso-build/references/harnesses-and-models.md).
- Anonymous Instagram downloads work for public posts. Use a login only for stories or heavy throttling: `instaloader --login <spare account>`.

## Report to the user

What was checked, what was installed, and anything still missing with the command to fix it.
