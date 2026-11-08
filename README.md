# experso

[![license](https://img.shields.io/github/license/aldhosutra/experso?color=2da44e)](LICENSE)
![agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Codex%20%7C%20OpenCode-1f6feb)
![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

**Expert from persona.** Point experso at a creator who shares what they know, and it turns their public posts into agent skills your coding agent can run: not summaries, but workflows with inputs, steps, outputs, and the creator's own frameworks and templates, each traceable to the post it came from.

```text
/experso-build kallawaymarketing
```

That one profile (274 posts) became 15 skills: a hook writer, a script writer, a retention doctor, a carousel builder, a content calendar planner and more.

## How it works

1. **Ingest.** Downloads the posts and transcribes the videos, in parallel.
2. **Extract.** An LLM reads every caption, transcript and carousel slide and pulls out each piece of expertise as its own insight.
3. **Group.** Insights are sorted into skill-sized categories.
4. **Plan.** Categories are turned into skills by the output they produce. You review a rendered plan showing each skill's input, process and output.
5. **Digest.** Each category is deduplicated once, keeping the creator's specifics and templates word for word.
6. **Write.** Code renders each `SKILL.md` from the approved plan; the LLM writes only the step bodies. Every reference links to its evidence.
7. **Audit.** A deterministic check of the whole chain, from source post to skill, so nothing goes stale.

Your agent's usage is the main cost: about 4–5 Claude usage windows for a 275-post profile. Every step resumes where it stopped, so usage limits don't lose work.

## Installation

With the Skills CLI:

```bash
npx skills add aldhosutra/experso --global
```

Leave off `--global` to install into the current project only.

Claude Code can install it as a plugin instead, which `/plugin update` then keeps current:

```text
/plugin marketplace add aldhosutra/experso
/plugin install experso@aldhosutra
```

This is the shared `aldhosutra` marketplace, which also carries [supervise](https://github.com/aldhosutra/supervise) and [loopa](https://github.com/aldhosutra/loopa). If you already added one of them, skip the first line.

Or in one line, which can also set up the Python packages:

```bash
curl -fsSL https://raw.githubusercontent.com/aldhosutra/experso/main/install.sh | bash -s -- --deps
```

Then ask your agent to set up experso, or invoke `experso-setup` directly. You need Python 3.10+, ffmpeg, and one logged-in agent CLI.

| Agent | Invoke a skill | Where it finds them |
|---|---|---|
| Claude Code | `/experso-build` | `~/.claude/skills`, `.claude/skills` |
| OpenCode | `/experso-build` or `@experso-build` | `~/.agents/skills`, `~/.claude/skills`, project equivalents |
| Codex | `$experso-build` | `~/.agents/skills`, `.agents/skills` |

Or just describe what you want ("make skills from @handle"): every agent picks the skill from its description. experso's LLM steps run through whichever agent started them. On agents other than Claude Code, give the heavy steps your strongest model with `--model`.

## Skills

| Skill | What it does |
|---|---|
| `/experso-setup` | Checks and installs what experso needs |
| `/experso-build` | Turns a creator's profile into skills |
| `/experso-refresh` | Updates a creator's skills with their new posts, redoing only what changed |
| `/experso-merge` | Combines overlapping skills from several creators, recording where they disagree and when to use which, or improves one of your own skills |
| `/experso-audit` | Deterministically verifies a creator's skills against the approved plan |
| `/experso-clean` | Deletes downloaded media and other data that has been consumed |

## What you get

Run experso in any folder, and it builds there:

```text
AGENTS.md                      an "Experso" section listing the skills (your text is untouched)
.agents/skills/<skill>/        SKILL.md + references (frameworks, templates, examples, rules)
.agents/insights/<creator>/    the evidence: one file per idea, each linking to its source post
.claude/skills                 linked to .agents/skills
.experso/                      working data, never committed (experso-clean frees it)
```

Several creators share one `.agents/`, and experso only ever changes the skills it generated.

## Sources and agents

Sources: Instagram today. Transcription: MLX Whisper on Apple Silicon, faster-whisper elsewhere. The LLM steps run through the agent that started them, and can use Claude Code, Codex, OpenCode, Gemini CLI, Qwen Code, Cursor, Copilot CLI, Factory Droid, Goose, Crush, Amp, Auggie, Ollama, or any CLI you give a command template for.

The methods in generated skills belong to their creators. Only build from content you're allowed to use, and credit its source.

## License

[MIT](LICENSE)
