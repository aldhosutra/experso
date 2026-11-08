"""Render a skill plan JSON (from scripts/plan.py) into one HTML page.

Deterministic: the same JSON always gives byte-identical HTML (no timestamps,
no randomness, JSON order preserved). Pure presentation, no LLM, so the UI can
be changed freely without touching the plan.

The output is an Artifact-ready page fragment (no <html>/<head>/<body> tags;
browsers render it fine when opened locally too).

Usage:
    experso render HANDLE [-o OUT.html]       (or a path to a skill_plan.json)
Default output: skill_plan.html next to the JSON.
"""
import argparse
import json
from html import escape
from pathlib import Path

from ..paths import Profile

CSS = """
/* Layout: one reading column; each skill is an input -> process -> output strip. */
:root {
  --bg: #f4f6f5; --surface: #ffffff; --ink: #18211f; --muted: #5a6763; --line: #dbe1de;
  --accent: #2753c9; --accent-soft: #e7ecfb;
  --in: #0d7466; --in-soft: #e2f2ef; --out: #a24d14; --out-soft: #f8ebe0;
  --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", sans-serif;
  --body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #111615; --surface: #18201e; --ink: #e6ecea; --muted: #9aa8a3; --line: #2b3633;
  --accent: #8aa8ff; --accent-soft: #1e2a4a; --in: #5fd0bd; --in-soft: #12302b;
  --out: #f0a36b; --out-soft: #3a2616; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #111615; --surface: #18201e; --ink: #e6ecea; --muted: #9aa8a3; --line: #2b3633;
  --accent: #8aa8ff; --accent-soft: #1e2a4a; --in: #5fd0bd; --in-soft: #12302b;
  --out: #f0a36b; --out-soft: #3a2616; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font: 15px/1.6 var(--body); }
.wrap { max-width: 1120px; margin: 0 auto; padding-block: 40px 80px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 56px; }
h1, h2, h3 { font-family: var(--display); text-wrap: balance; margin: 0; line-height: 1.15; }
h1 { font-size: clamp(30px, 5vw, 46px); font-weight: 700; letter-spacing: -0.02em; }
h2 { font-size: 24px; font-weight: 650; }
h3 { font-size: 21px; font-weight: 650; }
p { margin: 0; max-width: 68ch; }
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }
.eyebrow { font: 600 12px/1 var(--mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.mono { font-family: var(--mono); font-size: 13px; }
.muted { color: var(--muted); }
header { display: grid; gap: 14px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px 22px; font: 14px var(--mono); color: var(--muted);
  font-variant-numeric: tabular-nums; }
.stats b { color: var(--ink); font-weight: 600; }
section { display: grid; gap: 18px; }
.section-head { display: grid; gap: 6px; }
.journeys { display: grid; gap: 14px; }
.journey { display: grid; gap: 8px; padding: 16px 18px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px; }
.flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.flow .arrow { color: var(--muted); }
.chip { display: inline-block; padding: 2px 9px; border-radius: 999px; font: 13px/1.6 var(--mono);
  background: var(--accent-soft); color: var(--accent); text-decoration: none; white-space: nowrap; }
.chip.plain { background: transparent; border: 1px solid var(--line); color: var(--muted); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.index { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.index a { display: grid; gap: 4px; padding: 14px 16px; background: var(--surface); color: var(--ink);
  border: 1px solid var(--line); border-radius: 10px; text-decoration: none; }
.index a:hover { border-color: var(--accent); }
.index .n { font: 12px var(--mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.index .t { font-weight: 600; }
.index .s { font-size: 13.5px; color: var(--muted); line-height: 1.45; }
.skill { display: grid; gap: 18px; padding-top: 28px; border-top: 1px solid var(--line); scroll-margin-top: 16px; }
.skill-head { display: grid; gap: 6px; }
.skill-head .meta { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: baseline; }
.trigger { padding: 12px 16px; border-left: 3px solid var(--accent); background: var(--surface);
  border-radius: 0 8px 8px 0; font-size: 14px; }
.ipo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr) minmax(0, 1fr); gap: 12px; align-items: start; }
@media (max-width: 860px) { .ipo { grid-template-columns: minmax(0, 1fr); } }
.col { display: grid; gap: 10px; padding: 14px 16px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px; min-width: 0; }
.col > .eyebrow { display: flex; align-items: center; gap: 8px; }
.col > .eyebrow::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: currentColor; }
.col.input > .eyebrow { color: var(--in); }
.col.process > .eyebrow { color: var(--accent); }
.col.output > .eyebrow { color: var(--out); }
.col ul, .col ol { margin: 0; padding-left: 18px; display: grid; gap: 10px; }
.field { display: grid; gap: 2px; }
.field .name { font: 600 13px var(--mono); }
.req { font: 600 11px var(--mono); letter-spacing: 0.04em; text-transform: uppercase; padding: 1px 6px;
  border-radius: 4px; background: var(--in-soft); color: var(--in); margin-left: 6px; }
.req.opt { background: transparent; color: var(--muted); border: 1px solid var(--line); }
.example { font-size: 13px; color: var(--muted); }
.steps { list-style: none; padding: 0 !important; counter-reset: step; }
.steps li { display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 4px 10px; counter-increment: step; }
.steps li::before { content: counter(step); font: 600 12px/22px var(--mono); text-align: center;
  width: 22px; height: 22px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); }
.steps .body { display: grid; gap: 4px; min-width: 0; }
.steps .title { font-weight: 600; }
.steps .produces { font-size: 13px; color: var(--muted); }
.steps .produces b { color: var(--ink); font-weight: 600; }
.steps .chips .chip { font-size: 12px; white-space: normal; }
.deliverable { font-weight: 600; }
.format { padding: 8px 10px; background: var(--out-soft); border-radius: 6px; font-size: 14px; }
.checks li::marker { color: var(--out); }
.details { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px 28px; }
.details > div { display: grid; gap: 8px; align-content: start; min-width: 0; }
.details ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
.quote { font-style: italic; }
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
table { border-collapse: collapse; font-size: 13px; width: 100%; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
thead th { font: 600 11px var(--mono); color: var(--muted); }
th.rot { writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; padding: 10px 6px; }
td.dot { text-align: center; color: var(--accent); font-size: 16px; line-height: 1; }
td.num { font-variant-numeric: tabular-nums; text-align: right; font-family: var(--mono); }
tbody tr:last-child td { border-bottom: 0; }
.note { color: var(--muted); min-width: 240px; }
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:'
         'opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:'
         'ital,wght@0,400;0,600;1,400&display=swap">')


def e(s) -> str:
    return escape(str(s), quote=True)


def chips(items, cls="chip", link=False) -> str:
    if not items:
        return ""
    if link:
        return '<div class="chips">' + "".join(
            f'<a class="{cls}" href="#{e(x)}">{e(x)}</a>' for x in items) + "</div>"
    return '<div class="chips">' + "".join(f'<span class="{cls}">{e(x)}</span>' for x in items) + "</div>"


def differ(s: dict) -> str:
    """Merge plans: where the creators disagree, and when to use which."""
    if not s.get("disagreements"):
        return ""
    items = "".join(
        f'<div class="journey"><h3>{e(d["topic"])}</h3><ul>'
        + "".join(f'<li><b>{"Your skill" if p["creator"] == "you" else "@" + e(p["creator"])}</b>: '
                  f'{e(p["position"])}</li>' for p in d["positions"])
        + f'</ul><p><b>When to use which:</b> {e(d["guidance"])}</p></div>'
        for d in s["disagreements"])
    return f'\n  <div class="journeys"><div class="eyebrow">Where the creators differ</div>{items}</div>'


def render(plan: dict) -> str:
    cats = {c["slug"]: c for c in plan["categories"]}
    skills = plan["skills"]
    names = {s["slug"]: s["name"] for s in skills}

    def skill_insights(s):
        return sum(cats[c]["insights"] for c in s["source_categories"] if c in cats)

    out = [f'<title>@{e(plan["creator"])} Skill Plan</title>',
           '<meta name="claude:viewport-fit-sides" content="cover">', FONTS,
           f"<style>{CSS}</style>", '<div class="wrap">']

    # Header
    out.append(f"""<header>
  <div class="eyebrow">Skill plan · @{e(plan['creator'])}</div>
  <h1>{len(skills)} agent skills from @{e(plan['creator'])}</h1>
  <div class="stats"><span><b>{len(skills)}</b> skills</span><span><b>{plan['total_insights']:,}</b> insights</span>
  <span><b>{len(cats)}</b> categories</span><span>planned by <b>{e(plan['model'])}</b></span></div>
  <p>{e(plan['overview'])}</p>
</header>""")

    # Journeys
    if plan.get("journeys"):
        out.append('<section><div class="section-head"><h2>Workflows</h2>'
                   '<p class="muted">How the skills chain together end to end.</p></div><div class="journeys">')
        for j in plan["journeys"]:
            flow = '<span class="arrow" aria-hidden="true">→</span>'.join(
                f'<a class="chip" href="#{e(x)}">{e(names.get(x, x))}</a>' for x in j["skills"])
            out.append(f'<div class="journey"><h3>{e(j["name"])}</h3><p class="muted">{e(j["description"])}</p>'
                       f'<div class="flow">{flow}</div></div>')
        out.append("</div></section>")

    # Index
    out.append('<section><div class="section-head"><h2>Skills</h2></div><nav class="index">')
    for n, s in enumerate(skills, 1):
        out.append(f'<a href="#{e(s["slug"])}"><span class="n">{n:02d} · {skill_insights(s):,} insights</span>'
                   f'<span class="t">{e(s["name"])}</span><span class="s">{e(s["summary"])}</span></a>')
    out.append("</nav></section>")

    # Skill details
    for n, s in enumerate(skills, 1):
        inputs = "".join(
            f'<li class="field"><span><span class="name">{e(i["name"])}</span>'
            f'<span class="req{"" if i["required"] else " opt"}">{"required" if i["required"] else "optional"}</span></span>'
            f'<span>{e(i["description"])}</span><span class="example">e.g. {e(i["example"])}</span></li>'
            for i in s["input"])
        steps = "".join(
            f'<li><span class="body"><span class="title">{e(st["title"])}</span><span>{e(st["action"])}</span>'
            + (f'<span class="muted mono">from {e(", ".join("@" + c for c in st["creators"]))}</span>'
               if st.get("creators") else "")
            + f'{chips(st["frameworks"])}<span class="produces"><b>Produces:</b> {e(st["produces"])}</span></span></li>'
            for st in s["steps"])
        o = s["output"]
        checks = "".join(f"<li>{e(c)}</li>" for c in o["quality_criteria"])
        related = "".join(f'<li><a href="#{e(r["slug"])}">{e(names.get(r["slug"], r["slug"]))}</a>'
                          f' <span class="muted">{e(r["relation"])}</span></li>' for r in s["related_skills"])
        examples = "".join(f'<li class="quote">“{e(x)}”</li>' for x in s["example_requests"])
        sources = "".join(f'<li>{e(cats[c]["name"] if c in cats else c)} '
                          f'<span class="muted mono">({cats[c]["insights"] if c in cats else "?"})</span></li>'
                          for c in s["source_categories"])
        out.append(f"""<article class="skill" id="{e(s['slug'])}">
  <div class="skill-head">
    <div class="meta"><span class="eyebrow">Skill {n:02d}</span><span class="mono muted">{e(s['slug'])}</span>
      <span class="mono muted">{skill_insights(s):,} source insights</span></div>
    <h2>{e(s['name'])}</h2>
    <p>{e(s['summary'])}</p>
  </div>
  <div class="trigger"><span class="eyebrow">Trigger description</span><br>{e(s['description'])}</div>
  <div class="ipo">
    <div class="col input"><div class="eyebrow">Input</div><ul>{inputs}</ul></div>
    <div class="col process"><div class="eyebrow">Process</div><ol class="steps">{steps}</ol></div>
    <div class="col output"><div class="eyebrow">Output</div>
      <div class="deliverable">{e(o['deliverable'])}</div>
      <div class="format">{e(o['format'])}</div>
      <div class="eyebrow">Quality checks</div><ul class="checks">{checks}</ul></div>
  </div>
  <div class="details">
    <div><div class="eyebrow">Example requests</div><ul>{examples}</ul></div>
    <div><div class="eyebrow">Key frameworks</div>{chips(s['key_frameworks'], 'chip plain')}</div>
    <div><div class="eyebrow">Built from</div><ul>{sources}</ul></div>
    <div><div class="eyebrow">Related skills</div><ul>{related or '<li class="muted">None</li>'}</ul></div>
    <div><div class="eyebrow">Why this shape</div><p>{e(s['merge_rationale'])}</p></div>
  </div>{differ(s)}
</article>""")

    # Coverage matrix
    cov = {c["category"]: c for c in plan["coverage"]}
    head = "".join(f'<th class="rot" scope="col"><a href="#{e(s["slug"])}">{e(s["name"])}</a></th>' for s in skills)
    rows = []
    for c in plan["categories"]:
        used = set(cov.get(c["slug"], {}).get("skills", []))
        cells = "".join(f'<td class="dot">{"●" if s["slug"] in used else ""}</td>' for s in skills)
        rows.append(f'<tr><th scope="row">{e(c["name"])}</th><td class="num">{c["insights"]}</td>{cells}'
                    f'<td class="note">{e(cov.get(c["slug"], {}).get("note", "NOT COVERED"))}</td></tr>')
    out.append(f"""<section><div class="section-head"><h2>Coverage</h2>
  <p class="muted">Every category of insights and the skills that use it. Each row needs at least one dot.</p></div>
  <div class="table-wrap"><table><thead><tr><th scope="col">Category</th><th scope="col">Insights</th>{head}
  <th scope="col">How it is used</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>""")

    out.append("</div>")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a handle, or a path to a skill_plan.json")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args(argv)
    src = Path(a.target) if a.target.endswith(".json") else Profile(a.target).plan_file
    if not src.exists():
        raise SystemExit(f"No plan at {src}: run `experso plan {a.target}` first.")
    dst = Path(a.out) if a.out else src.with_suffix(".html")
    dst.write_text(render(json.loads(src.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"[render] wrote {dst}")


if __name__ == "__main__":
    main()
