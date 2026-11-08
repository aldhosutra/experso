"""Extractor registry. Extraction is semantic work done by an LLM; a backend is
only the wrapper that hands it a post and collects the structured result.

Backends:
- every coding-agent CLI in agent_cli.HARNESSES (claude-code, codex, opencode,
  gemini, qwen, cursor, copilot, droid, goose, crush, amp, auggie)
- custom: any other CLI, via --cmd "tool ... {prompt_file}"
- ollama: local models over Ollama's HTTP API

To add a harness, add a Harness entry in agent_cli.py (usually ~8 lines).
All backends share the prompt and insight format in schema.py.
"""
import os
import shutil
import subprocess
import urllib.request

from .agent_cli import HARNESSES, AgentCliExtractor
from .base import Extractor

NAMES = [*HARNESSES, "custom", "ollama"]
ALIASES = {"claude-cli": "claude-code", "claude": "claude-code", "cursor-agent": "cursor"}


def _running_under() -> str | None:
    """The agent harness this process was launched from, by walking parent processes."""
    binaries = {h.binary: name for name, h in HARNESSES.items()}
    pid = os.getppid()
    for _ in range(20):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,args=", "-p", str(pid)], capture_output=True, text=True).stdout
            ppid, _, args = out.strip().partition(" ")
        except OSError:  # no ps (e.g. Windows): fall through to what is installed
            return None
        for token in args.split()[:3]:  # e.g. "node /usr/lib/node_modules/.bin/codex exec"
            base = os.path.basename(token)
            if base in binaries:
                return binaries[base]
        if not ppid.strip().isdigit() or int(ppid) <= 1:
            return None
        pid = int(ppid)
    return None


def default_harness() -> str:
    """$EXPERSO_HARNESS, else the harness running this script, else the first one installed."""
    env = os.environ.get("EXPERSO_HARNESS")
    if env:
        return ALIASES.get(env, env)
    found = _running_under()
    if found:
        return found
    return next((n for n, h in HARNESSES.items() if shutil.which(h.binary)), "claude-code")


def default_model(harness: str, tier: str) -> str | None:
    """Model for a step. Tiers come from side-by-side tests: "strong" where substance is lost
    otherwise, "fast" where it isn't. Only Claude Code has known names; other harnesses use their
    configured model unless --model is given."""
    if ALIASES.get(harness, harness) == "claude-code":
        return {"strong": "opus", "fast": "sonnet"}[tier]
    return None


def _ollama_up() -> bool:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    host = host if host.startswith("http") else "http://" + host
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def get_extractor(name: str, model: str | None = None, **options) -> Extractor:
    name = ALIASES.get(name, name)
    if name == "ollama":
        from .ollama_api import OllamaExtractor
        if not _ollama_up():
            raise SystemExit("Ollama is not running (start it with `ollama serve`).")
        return OllamaExtractor(model=model, **options)
    if name == "custom":
        return AgentCliExtractor("custom", model=model, **options)
    if name not in HARNESSES:
        raise SystemExit(f"Unknown extractor {name!r}. Available: {', '.join(NAMES)}")
    if shutil.which(HARNESSES[name].binary) is None:
        raise SystemExit(f"Extractor {name!r} needs the `{HARNESSES[name].binary}` command, "
                         f"which is not installed. See {HARNESSES[name].docs}")
    return AgentCliExtractor(name, model=model, **options)


def describe_all() -> str:
    lines = []
    for name, h in HARNESSES.items():
        here = "installed" if shutil.which(h.binary) else "not installed"
        lines += [f"{name:12} [{here}; {'tested' if h.tested else 'untested'}] {h.summary}",
                  f"{'':12}  output: {'native JSON schema' if h.native_schema else 'schema in prompt + validation'}; "
                  f"images: {h.images}" + (f"; {h.notes}" if h.notes else ""),
                  f"{'':12}  docs: {h.docs}"]
    lines += [f"{'custom':12} [any CLI] --cmd 'tool ... {{prompt_file}}' (prompt via stdin if no {{prompt_file}}); "
              "reply must be the JSON on stdout",
              f"{'ollama':12} [{'running' if _ollama_up() else 'not running'}; untested] local vision model via "
              "Ollama HTTP API, native JSON schema; needs --model"]
    return "\n".join(lines)
