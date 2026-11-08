#!/usr/bin/env python3
"""Check that real agents pick the right experso skill for sample requests.

Run from the repo root:
    python3 .agents/skills/experso-dev-release/scripts/check_triggers.py claude
    python3 .agents/skills/experso-dev-release/scripts/check_triggers.py opencode --model google/gemini-2.5-flash
Each case asks the harness which skill it would use (no work is done).
Exit code 1 if any case misses.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "references" / "trigger-evals.json"
ASK = ("Which available skill would you load for this request? Do not load it or do the work. Reply with only "
       "the skill name, or 'none' if no skill fits.\n\nRequest: {q}")


def ask(harness: str, model: str | None, q: str) -> str:
    prompt = ASK.format(q=q)
    if harness == "claude":
        cmd = ["claude", "-p", "--model", model or "sonnet"]
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300)
    elif harness == "opencode":
        cmd = ["opencode", "run", prompt] + (["-m", model] if model else [])
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    else:
        cmd = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-"] + (["-m", model] if model else [])
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300)
    lines = [ln.strip(" `*.") for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1].lower() if lines else f"(no output: {r.stderr[-200:]})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("harness", choices=["claude", "opencode", "codex"])
    ap.add_argument("--model")
    a = ap.parse_args()
    cases, misses = json.loads(EVALS.read_text()), 0
    for c in cases:
        got = ask(a.harness, a.model, c["query"])
        ok = got == c["expect"]
        misses += not ok
        print(f"{'PASS' if ok else 'MISS'}  {c['expect']:26} got {got[:40]:40} {c['query'][:50]}", flush=True)
    print(f"\n{len(cases) - misses}/{len(cases)} routed correctly on {a.harness}")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
