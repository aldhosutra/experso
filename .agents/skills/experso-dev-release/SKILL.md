---
name: experso-dev-release
description: "Releases a new version of experso: validates every skill, bumps the version, and updates the shared aldhosutra marketplace. Use when working in the experso repository and asked to release, publish or bump the version of experso, or to check that its skills meet the spec on every harness."
compatibility: "Requires git, PyYAML, and at least one agent CLI for the trigger check."
---

# Release experso

Needs the new version (semver). A change to the generated output's format is at least a minor bump. Run everything from the repo root.

## Workflow

```
- [ ] 1. Validate the skills
- [ ] 2. Check real harnesses pick the right skill
- [ ] 3. Test the scripts and install
- [ ] 4. Bump the version and rebuild
- [ ] 5. The user approves, then publish
```

**1. Validate** the spec and harness neutrality. Fix every failure and repeat until all pass:

```bash
python3 .agents/skills/experso-dev-release/scripts/lint_skills.py
```

**2. Check triggers** on every harness you have logged in. Reword a description for any miss and repeat:

```bash
python3 .agents/skills/experso-dev-release/scripts/check_triggers.py claude
python3 .agents/skills/experso-dev-release/scripts/check_triggers.py opencode --model <provider/model>
python3 .agents/skills/experso-dev-release/scripts/check_triggers.py codex
```

Cases are in [references/trigger-evals.json](references/trigger-evals.json). Add one whenever a skill is added.

**3. Test the scripts and install.**

```bash
X=plugins/experso/skills/experso-build/scripts
python3 $X/audit.py <a built creator>
HOME=$(mktemp -d) ./install.sh
git status --short    # nothing under workspace/ may be listed
```

**4. Bump** `__version__` in `$X/experso/__init__.py` and `version` in `plugins/experso/.claude-plugin/plugin.json`. Then run `python3 $X/write.py <handle> --assemble-only` for each built creator, and audit again.

**5. Publish**, only after the user confirms each push: commit, tag `v<version>`, and push `aldhosutra/experso`. The `aldhosutra` marketplace is duplicated in `.claude-plugin/marketplace.json` of `aldhosutra/supervise`, `aldhosutra/loopa` and `aldhosutra/experso`; each lists its own plugin as `"source": "./plugins/<name>"` and the others as `git-subdir`. Keep the three in step when a plugin is added or its description changes.

## Gotchas

- The two version strings must match.
- Every push is outward-facing: get a yes for each repository.

## Report

The version, each check's result per harness, and every repository pushed.
