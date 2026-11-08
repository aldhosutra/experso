# Skills

Skills for running and maintaining experso. `.claude/skills` is a symlink to this folder. Naming: `/experso-*` serve users and ship with the plugin (their source is in `plugins/experso/skills/`, linked here); `/experso-dev-*` are for maintaining experso and don't ship. When adding a skill, also add it here.

## For users

| Skill | When to use |
|-------|-------------|
| [`/experso-setup`](experso-setup/SKILL.md) | Before the first build on a machine, or when a package or tool is missing. |
| [`/experso-build`](experso-build/SKILL.md) | Turn a creator's public profile into skills in `.agents/`: download, transcribe, extract, group, plan (reviewed), digest, write, audit. |
| [`/experso-refresh`](experso-refresh/SKILL.md) | Update a built creator with their new posts, redoing only what changed. |
| [`/experso-merge`](experso-merge/SKILL.md) | Combine overlapping skills from several creators into one, or improve your own skill with a creator's expertise. |
| [`/experso-audit`](experso-audit/SKILL.md) | Deterministically verify a creator's skills: the whole chain from post to skill, against the approved plan. |
| [`/experso-clean`](experso-clean/SKILL.md) | Delete downloaded media and other data that has been consumed. |

## For maintainers

| Skill | When to use |
|-------|-------------|
| [`/experso-dev-add-platform`](experso-dev-add-platform/SKILL.md) | Add a content platform to build skills from (YouTube, TikTok, ...). |
| [`/experso-dev-add-harness`](experso-dev-add-harness/SKILL.md) | Add an agent harness, LLM backend or transcription engine. |
| [`/experso-dev-model-eval`](experso-dev-model-eval/SKILL.md) | Choose a model or harness for a pipeline step with a side-by-side test. |
| [`/experso-dev-release`](experso-dev-release/SKILL.md) | Publish a new version and update the marketplaces. |
