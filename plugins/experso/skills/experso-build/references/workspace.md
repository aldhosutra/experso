# Workspace layout

The workspace is where experso builds: the current directory, or `<repo>/workspace/` inside an experso repo clone, or `$EXPERSO_WORKSPACE` when set. Several creators share one workspace and one `.agents/`.

```
AGENTS.md                         one managed "Experso" section between <!-- experso:begin vX --> markers
CLAUDE.md -> AGENTS.md            created only if there was no CLAUDE.md
.agents/skills/<skill>/           SKILL.md + references/<kind>.md
.agents/skills/README.md          index, with a managed Experso section
.agents/insights/<handle>/        <category>/<insight-id>.md, <category>/_index.md, _categories.md
.claude/skills                    -> ../.agents/skills (or one link per skill if it is a real folder)
.experso/                         working data; has its own .gitignore, never committed
  profiles/<handle>/
    manifest.json                 source, processed posts, history
    cache/                        downloaded media, captions, metadata, transcripts
    state/_raw/                   full extraction output per post
    state/_grouping/              taxonomy.json, assignments.json
    state/digest/<category>.json  deduplicated items with stable ids
    state/plan/                   skill_plan.json, skill_plan.html, skills_raw/
    state/outputs.json            every file the last build generated
  merges/<skill>/                 merge.json, merge_plan.json/.html, writer.json, outputs.json
  backups/<skill>/<timestamp>/    a user's skill before it was improved
```

## Ownership

A skill is experso's when its frontmatter `metadata` has `experso-version`, `experso-kind` (`generated`, `merged` or `improved`) and `experso-creators`. experso regenerates those skills freely, so hand edits to them are lost and the audit reports them. It never changes any other skill without a backup and the user's approval, and in shared files it edits only between its markers.

## The chain

```
post (URL) <- insight <- digest item <- skill reference <- SKILL.md step
```

Each link is generated from ids when skills are assembled. The digest is a build step: it deduplicates each category once, and nothing reads it after the build.
