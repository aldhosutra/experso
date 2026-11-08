#!/usr/bin/env bash
# Install the experso skills for Claude Code, Codex, OpenCode and any agent that
# reads ~/.agents/skills or ~/.claude/skills.
#
#   ./install.sh                         from a clone
#   curl -fsSL <raw-url> | bash          from anywhere (clones itself)
#   curl -fsSL <raw-url> | bash -s -- --deps
#
# Options:
#   --project      install into ./.agents/skills of the current directory instead of ~/.agents/skills
#   --deps         create ~/.experso/venv with the Python packages experso needs
#                  (instaloader, jsonschema, and the transcription engine for this machine)
#
# The skills are copied to ~/.agents/skills and linked from ~/.claude/skills.
# Claude Code users may prefer the plugin route instead, which handles updates:
#   /plugin marketplace add aldhosutra/experso
#   /plugin install experso@aldhosutra
set -euo pipefail

REPO_URL="https://github.com/aldhosutra/experso.git"
SKILLS_SUBPATH="plugins/experso/skills"
COMMANDS_SUBPATH="plugins/experso/opencode/command"
SCOPE="user"; DEPS=0
for a in "$@"; do
  case "$a" in
    --project) SCOPE="project" ;;
    --deps) DEPS=1 ;;
    -h|--help) sed -n '2,16p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

for tool in git python3 ffmpeg; do
  command -v "$tool" >/dev/null 2>&1 || echo "warning: $tool not found: experso needs it (macOS: brew install $tool)" >&2
done

# Work out where the skills are coming from. When piped through bash there is no script on disk, so fetch a copy.
ROOT=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  [ -d "$HERE/$SKILLS_SUBPATH" ] && ROOT="$HERE"
fi
if [ -z "$ROOT" ]; then
  CLONE="$(mktemp -d)"
  trap 'rm -rf "$CLONE"' EXIT
  echo "fetching $REPO_URL"
  git clone --depth 1 -q "$REPO_URL" "$CLONE/experso"
  ROOT="$CLONE/experso"
fi
[ -d "$ROOT/$SKILLS_SUBPATH" ] || { echo "cannot find the skills at $ROOT/$SKILLS_SUBPATH" >&2; exit 1; }

if [ "$SCOPE" = "project" ]; then BASE="$PWD"; else BASE="$HOME"; fi
AGENTS_DIR="$BASE/.agents/skills"
CLAUDE_DIR="$BASE/.claude/skills"
mkdir -p "$AGENTS_DIR" "$(dirname "$CLAUDE_DIR")"

count=0
for src in "$ROOT/$SKILLS_SUBPATH"/experso-*/; do
  name="$(basename "$src")"
  dest="$AGENTS_DIR/$name"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  find "$dest" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  # Link from .claude/skills, unless that whole folder is already a link to .agents/skills
  if [ ! -L "$CLAUDE_DIR" ]; then
    mkdir -p "$CLAUDE_DIR"
    rm -rf "${CLAUDE_DIR:?}/$name"
    if [ "$SCOPE" = "project" ]; then
      ln -s "../../.agents/skills/$name" "$CLAUDE_DIR/$name"
    else
      ln -s "$dest" "$CLAUDE_DIR/$name"
    fi
  fi
  count=$((count + 1))
done
echo "installed $count skills to $AGENTS_DIR (linked from $CLAUDE_DIR)"

# OpenCode reads the skills folders above; its slash commands live elsewhere.
if command -v opencode >/dev/null 2>&1; then
  if [ "$SCOPE" = "project" ]; then CMD_DIR="$PWD/.opencode/command"; else CMD_DIR="$HOME/.config/opencode/command"; fi
  mkdir -p "$CMD_DIR"
  cp "$ROOT/$COMMANDS_SUBPATH"/experso-*.md "$CMD_DIR/"
  echo "installed the opencode commands to $CMD_DIR"
fi

if [ "$DEPS" = 1 ]; then
  echo "creating ~/.experso/venv"
  [ -x "$HOME/.experso/venv/bin/python" ] || python3 -m venv "$HOME/.experso/venv"
  PIP="$HOME/.experso/venv/bin/pip"
  "$PIP" install -q --disable-pip-version-check --upgrade pip >/dev/null 2>&1 || true
  "$PIP" install -q --disable-pip-version-check instaloader jsonschema
  if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    "$PIP" install -q --disable-pip-version-check mlx-whisper
  else
    "$PIP" install -q --disable-pip-version-check faster-whisper
  fi
fi

echo
echo "Start a new agent session, then ask it to set up experso, or invoke:"
echo "  experso-setup            check this machine"
echo "  experso-build <handle>   turn a creator's profile into skills"
echo "(Claude Code and OpenCode: /experso-build. Codex: \$experso-build.)"
