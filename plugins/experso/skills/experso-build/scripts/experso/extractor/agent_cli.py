"""Generic wrapper for coding-agent CLIs run headless (Claude Code, Codex,
OpenCode, Gemini CLI, ...). The agent does the extraction; this only hands it a
post and collects the JSON.

Each call runs in a fresh temp folder that holds only the post's images (as
images/slide_NN.jpg), so the agent can open them and nothing else from the
project is in reach. Harnesses with native structured output get the JSON
Schema natively; the rest get it in the prompt, and the reply is parsed and
validated, with one retry that quotes the validation error.
"""
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .base import Extractor
from .schema import INLINE_SCHEMA, RESULT_SCHEMA, SYSTEM_PROMPT, build_prompt, parse_json


@dataclass
class Call:
    """Everything a harness needs to build its command line."""
    workdir: Path
    prompt: str              # already includes the system prompt if the harness has no flag for it
    model: str | None
    images: list[str]        # paths relative to workdir
    schema_file: Path
    out_file: Path
    schema: dict = None      # JSON Schema the reply must match
    system: str = ""         # system prompt (only used by harnesses with system_flag)


@dataclass(frozen=True)
class Harness:
    binary: str
    summary: str
    docs: str
    tested: bool                                   # verified end-to-end in this project
    build: Callable[[Call], tuple[list[str], str | None]]  # -> (argv, stdin)
    parse: Callable[[str, Call], "str | dict"]     # stdout -> reply text, or result dict if native
    images: str = "path"     # "path": agent opens images/... itself; "at": @images/... (Gemini-style);
                             # "attach": the command attaches them (refs say "attached image N")
    native_schema: bool = False
    system_flag: bool = False  # harness takes SYSTEM_PROMPT separately (else it is prepended)
    notes: str = ""


def _m(flag: str, c: Call) -> list[str]:
    return [flag, c.model] if c.model else []


def _json_field(*path):
    def parse(stdout: str, c: Call):
        obj = json.loads(stdout)
        for k in path:
            obj = obj[k]
        return obj
    return parse


def _text(stdout: str, c: Call) -> str:
    return stdout


def _out_file(stdout: str, c: Call) -> str:
    return c.out_file.read_text(encoding="utf-8")


def _opencode_events(stdout: str, c: Call) -> str:
    # JSON lines; the reply is the text parts after the last step_start.
    texts: list[str] = []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "step_start":
            texts = []
        elif ev.get("type") == "text":
            texts.append(ev.get("part", {}).get("text", ""))
        elif ev.get("type") == "error":
            raise RuntimeError(f"opencode error: {json.dumps(ev)[:400]}")
    return "".join(texts)


def _claude(stdout: str, c: Call):
    out = json.loads(stdout)
    if out.get("is_error") or not isinstance(out.get("structured_output"), dict):
        raise RuntimeError(f"no structured output (api status {out.get('api_error_status')}): "
                           f"{str(out.get('result'))[:300]}")
    res = out["structured_output"]
    res["_cost_usd"] = out.get("total_cost_usd")
    return res


HARNESSES: dict[str, Harness] = {
    "claude-code": Harness(
        binary="claude", summary="Anthropic Claude Code (`claude -p`)",
        docs="https://docs.claude.com/en/docs/claude-code/headless", tested=True,
        native_schema=True, system_flag=True,
        build=lambda c: (["claude", "-p", "--output-format", "json", *_m("--model", c),
                          "--tools", "Read", "--allowedTools", "Read", "--strict-mcp-config",
                          "--no-session-persistence", "--system-prompt", c.system,
                          "--json-schema", json.dumps(c.schema)], c.prompt),
        parse=_claude,
        notes="Only the Read tool, no MCP servers. Default model here: opus."),
    "codex": Harness(
        binary="codex", summary="OpenAI Codex CLI (`codex exec`)",
        docs="https://developers.openai.com/codex/cli", tested=False,
        native_schema=True, images="attach",
        build=lambda c: (["codex", "exec", *[a for i in c.images for a in ("-i", i)],
                          "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral",
                          "-C", str(c.workdir), "--output-schema", str(c.schema_file),
                          "-o", str(c.out_file), *_m("-m", c), "-"], c.prompt),
        parse=lambda s, c: parse_json(_out_file(s, c), c.schema),
        notes="Read-only sandbox, images attached with -i, schema via --output-schema."),
    "opencode": Harness(
        binary="opencode", summary="OpenCode (`opencode run`), any provider it is set up for",
        docs="https://opencode.ai/docs/cli/", tested=True, images="attach",
        build=lambda c: (["opencode", "run", c.prompt, *[a for i in c.images for a in ("-f", i)],
                          "--format", "json", "--dir", str(c.workdir), *_m("-m", c)], None),
        parse=_opencode_events,
        notes="Pass --model provider/model. If the provider errors, OpenCode retries "
              "silently until the timeout."),
    "gemini": Harness(
        binary="gemini", summary="Google Gemini CLI (`gemini -p`)",
        docs="https://geminicli.com/docs/cli/headless", tested=False, images="at",
        build=lambda c: (["gemini", "-p", c.prompt, "--output-format", "json", *_m("-m", c)], None),
        parse=_json_field("response")),
    "qwen": Harness(
        binary="qwen", summary="Qwen Code (Gemini CLI fork, `qwen -p`)",
        docs="https://github.com/QwenLM/qwen-code", tested=False, images="at",
        build=lambda c: (["qwen", "-p", c.prompt, "--output-format", "json", *_m("-m", c)], None),
        parse=_json_field("response")),
    "cursor": Harness(
        binary="cursor-agent", summary="Cursor CLI (`cursor-agent -p`)",
        docs="https://cursor.com/docs/cli/reference/output-format", tested=False,
        build=lambda c: (["cursor-agent", "-p", "--output-format", "json",
                          *_m("--model", c), c.prompt], None),
        parse=_json_field("result"),
        notes="Without --force it only proposes file changes."),
    "copilot": Harness(
        binary="copilot", summary="GitHub Copilot CLI (`copilot -p`)",
        docs="https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically",
        tested=False,
        build=lambda c: (["copilot", "-p", c.prompt, "-s", *_m("--model", c)], None),
        parse=_text),
    "droid": Harness(
        binary="droid", summary="Factory Droid (`droid exec`)",
        docs="https://docs.factory.ai/cli/droid-exec/overview", tested=False,
        build=lambda c: (["droid", "exec", "--output-format", "json", *_m("-m", c), c.prompt], None),
        parse=_json_field("result"),
        notes="Default autonomy is read-only. Needs FACTORY_API_KEY."),
    "goose": Harness(
        binary="goose", summary="Block Goose (`goose run`)",
        docs="https://block.github.io/goose/docs/guides/running-tasks", tested=False,
        build=lambda c: (["goose", "run", "--no-session", "-t", c.prompt], None),
        parse=_text, notes="Model comes from goose's own config."),
    "crush": Harness(
        binary="crush", summary="Charm Crush (`crush run`)",
        docs="https://github.com/charmbracelet/crush", tested=False,
        build=lambda c: (["crush", "run", "--quiet", c.prompt], None),
        parse=_text, notes="Model comes from crush's own config."),
    "amp": Harness(
        binary="amp", summary="Sourcegraph Amp (`amp -x`)",
        docs="https://ampcode.com/manual", tested=False,
        build=lambda c: (["amp", "-x", c.prompt], None),
        parse=_text),
    "auggie": Harness(
        binary="auggie", summary="Augment Code CLI (`auggie --print`)",
        docs="https://docs.augmentcode.com/cli/overview", tested=False,
        build=lambda c: (["auggie", "--print", "--quiet", c.prompt], None),
        parse=_text),
}


def custom_harness(template: str) -> Harness:
    """Any other CLI, from a command template. Placeholders: {prompt_file}
    (else the prompt goes to stdin), {workdir}, {model}. The agent must print
    the JSON reply to stdout; images are in ./images/ for it to open."""
    import shlex

    def build(c: Call):
        pf = c.workdir / "prompt.txt"
        pf.write_text(c.prompt, encoding="utf-8")
        argv = [a.format(prompt_file=pf, workdir=c.workdir, model=c.model or "")
                for a in shlex.split(template)]
        return argv, (None if "{prompt_file}" in template else c.prompt)

    return Harness(binary=shlex.split(template)[0], summary=f"custom: {template}",
                   docs="", tested=False, build=build, parse=_text)


class AgentCliExtractor(Extractor):
    def __init__(self, harness: str, **kwargs):
        super().__init__(**kwargs)
        self.name = harness
        if harness == "custom":
            if not self.options.get("cmd"):
                raise SystemExit("--extractor custom needs --cmd 'tool ... {prompt_file}'")
            self.h = custom_harness(self.options["cmd"])
        else:
            self.h = HARNESSES[harness]

    @property
    def label(self) -> str:
        return f"{self.name}/{self.model or 'default'}"

    def _refs(self, images: list[str]) -> tuple[list[str], str]:
        if self.h.images == "attach":
            return ([f"attached image {i} ({p})" for i, p in enumerate(images, 1)],
                    "they are attached to this message")
        if self.h.images == "at":
            return [f"@{p}" for p in images], "they are included via the @ references"
        return images, "open each file, relative to the current folder, with your file-reading tool"

    def _run(self, call: Call) -> "str | dict":
        argv, stdin = self.h.build(call)
        # Harnesses that take the prompt as an argument still read stdin if it
        # is a pipe (OpenCode waits on it forever), so give them an empty one.
        stdin_kw = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        r = subprocess.run(argv, capture_output=True, text=True, cwd=call.workdir,
                           timeout=self.options.get("timeout", 1200), **stdin_kw)
        if r.returncode != 0:
            raise RuntimeError(f"{self.h.binary} exited {r.returncode}: {(r.stderr or r.stdout)[-500:]}")
        return self.h.parse(r.stdout, call)

    def run_json(self, prompt: str, schema: dict, system: str = "",
                 images: list[str] | None = None, image_label: str = "image") -> dict:
        """Run any prompt through the harness and return a dict that validates
        against `schema`. `images` are absolute paths; they are copied into the
        temp workdir and the prompt's {images} / {image_how} placeholders (if
        present) are filled with harness-appropriate references."""
        with tempfile.TemporaryDirectory(prefix="agent-") as tmp:
            wd = Path(tmp)
            (wd / "images").mkdir()
            rels = []
            for i, src in enumerate(images or [], 1):
                rel = f"images/{image_label}_{i:02d}{Path(src).suffix}"
                shutil.copy(src, wd / rel)
                rels.append(rel)
            refs, how = self._refs(rels)
            if "{images}" in prompt or "{image_how}" in prompt:
                prompt = prompt.replace("{images}", "\n".join(refs) or "(none)").replace("{image_how}", how)
            if not self.h.native_schema:
                prompt += INLINE_SCHEMA.format(schema=json.dumps(schema))
            if system and not self.h.system_flag:
                prompt = system + "\n\n" + prompt
            schema_file = wd / "schema.json"
            schema_file.write_text(json.dumps(schema))
            call = Call(wd, prompt, self.model, rels, schema_file, wd / "reply.json",
                        schema=schema, system=system)

            reply = self._run(call)
            if isinstance(reply, dict):
                return reply
            try:
                return parse_json(reply, schema)
            except ValueError as e:  # one retry, telling the agent what was wrong
                call.prompt = (prompt + f"\n\nYour previous reply was rejected ({e}). "
                               "Reply again with ONLY the corrected JSON object.")
                reply = self._run(call)
                return reply if isinstance(reply, dict) else parse_json(reply, schema)

    def extract(self, post, creator: str) -> dict:
        prompt = build_prompt(post, creator, image_refs=["{images}"], image_how="{image_how}")
        return self.run_json(prompt, RESULT_SCHEMA, SYSTEM_PROMPT, post.images, "slide")
