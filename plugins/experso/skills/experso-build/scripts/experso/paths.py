"""Where experso reads and writes.

The workspace is where packs are built:
  - inside an experso repo clone (has plugins/experso/): <repo>/workspace/
  - anywhere else: the current directory
  - $EXPERSO_WORKSPACE overrides both (used for tests and scratch runs)

Layout of a workspace (several creators merge into one .agents/):

    AGENTS.md                         contains one managed "Experso" section
    CLAUDE.md -> AGENTS.md            created only if there was no CLAUDE.md
    .agents/skills/<skill>/           SKILL.md + references/ (frontmatter metadata says experso owns it)
    .agents/insights/<handle>/        evidence: <category>/<insight-id>.md, _index.md, _categories.md
    .claude/skills                    -> ../.agents/skills (or per-skill links if it is a real folder)
    .experso/
      .gitignore                      "*": working data is never committed
      profiles/<handle>/
        manifest.json                 source, processed posts, history
        cache/                        downloaded media, captions, metadata, transcripts (experso-clean)
        state/
          _raw/                       full extractor output per post
          _grouping/                  taxonomy.json, assignments.json
          digest/                     <category>.json: deduplicated items with stable ids
          plan/                       skill_plan.json/.html, skills_raw/<slug>.json
          outputs.json                every file experso generated for this handle (stale detection)
"""
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def repo_root(start: Path) -> Path | None:
    for d in (start, *start.parents):
        if (d / "plugins" / "experso" / ".claude-plugin" / "plugin.json").is_file():
            return d
    return None


def workspace() -> Path:
    env = os.environ.get("EXPERSO_WORKSPACE")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    repo = repo_root(cwd)
    return repo / "workspace" if repo else cwd


class Workspace:
    def __init__(self, root: Path | None = None):
        self.root = Path(root).resolve() if root else workspace()
        self.agents = self.root / ".agents"
        self.skills = self.agents / "skills"
        self.insights_root = self.agents / "insights"
        self.claude_skills = self.root / ".claude" / "skills"
        self.agents_md = self.root / "AGENTS.md"
        self.claude_md = self.root / "CLAUDE.md"
        self.experso = self.root / ".experso"

    def ensure(self) -> "Workspace":
        self.experso.mkdir(parents=True, exist_ok=True)
        ignore = self.experso / ".gitignore"
        if not ignore.exists():
            ignore.write_text("# experso working data: never commit\n*\n")
        return self

    def handles(self) -> list[str]:
        d = self.experso / "profiles"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


class Profile:
    def __init__(self, handle: str, ws: Workspace | None = None):
        self.handle = handle.lstrip("@")
        self.ws = ws or Workspace()
        self.home = self.ws.experso / "profiles" / self.handle
        self.manifest = self.home / "manifest.json"
        self.cache = self.home / "cache"
        self.state = self.home / "state"
        self.raw = self.state / "_raw"
        self.grouping = self.state / "_grouping"
        self.digest = self.state / "digest"
        self.plan_dir = self.state / "plan"
        self.plan_file = self.plan_dir / "skill_plan.json"
        self.skills_raw = self.plan_dir / "skills_raw"
        self.outputs = self.state / "outputs.json"
        self.insights = self.ws.insights_root / self.handle

    def ensure(self) -> "Profile":
        self.ws.ensure()
        for d in (self.cache, self.raw, self.grouping, self.digest, self.plan_dir, self.insights):
            d.mkdir(parents=True, exist_ok=True)
        return self
