"""Read-only co-author tour; live pilot evidence is distinct from proposed benefits."""
import json
from html import escape
from pathlib import Path
from urllib.parse import quote

PILOT = '1ac68a9e-2b21-4f11-a5a6-9076a6295df0'

def render_walkthrough(store, project):
    data = store.etymology(project)  # Validate ownership/context before rendering.
    if project != PILOT:
        return ('<!doctype html><html lang="en"><title>Co-author walkthrough</title>'
                '<main><h1>This walkthrough uses the immersiveness pilot</h1>'
                '<p>Your selected project has not been changed.</p>'
                f'<a href="/walkthrough?project={PILOT}">Open the immersiveness walkthrough</a>'
                '</main></html>')
    content = json.loads(Path(__file__).with_name('walkthrough_content.json').read_text())
    e = lambda value: escape(str(value), quote=True)
    base = '/etymology?project=' + quote(project)
    records = data['records']
    chapters = []
    for i, step in enumerate(content['steps'], 1):
        evidence = []
        for r in records:
            if r['kind'] not in step['kinds']:
                continue
            fields = ''.join(f'<dt>{e(k.replace("_", " "))}</dt><dd>{e(v)}</dd>' for k,v in r['content'].items() if k != 'title')
            history = r['history'][0] if r['history'] else {}
            source = r['content'].get('url', '')
            source_link = f'<p><a href="{e(source)}" target="_blank" rel="noopener">Open documented source</a></p>' if source.startswith(('https://','http://')) else ''
            report = f'<p><a href="/api/projects/{quote(project)}/runs/{quote(r["id"])}/report">Open this run-summary report</a></p>' if r['kind'] == 'run' else ''
            evidence.append(f'<details class="record"><summary>{e(r["content"]["title"])} · V{r["version"]}</summary>'
                            f'<p class="meta">{e(r["kind"])} · {e(history.get("actor",""))} · {e(history.get("created_at",""))} UTC'
                            f'{" · References an earlier supporting version" if r["stale"] else ""}</p><dl>{fields}</dl>{source_link}{report}'
                            f'<a href="{base}&amp;record={quote(r["id"])}#heading">Inspect record and version history</a></details>')
        evidence_html = ''.join(evidence) or '<p>This is a proposed extension. There are no joint saturation results for this pilot.</p>'
        chapters.append(f'<section id="step-{i}" class="step"><div class="eyebrow">STEP {i:02d} / 10</div><h2>{e(step["title"])}</h2>'
                        f'<p class="lead">{e(step["action"])}</p><p>{e(step["example"])}</p>'
                        f'<div class="fit"><strong>Organization Science fit</strong><br><span>{e(step["fit"])}</span><p>{e(step["why"])}</p>'
                        '<a href="https://orgsci.org/" target="_blank" rel="noopener">Call: contribution types and review criteria</a></div>'
                        f'<h3>The prompting objection</h3><p>{e(step["prompt"])}</p><p class="limit"><strong>What we cannot claim:</strong> {e(step["limit"])}</p>'
                        f'<details><summary>Inspect live pilot evidence · {len(evidence)} records</summary>{evidence_html}</details>'
                        f'<div class="actions"><a href="{base}#{step["anchor"]}">Open workspace at this step</a>'
                        f'<a href="#step-{i+1}" class="next">Next step →</a></div></section>' if i < 10 else
                        f'<section id="step-{i}" class="step"><div class="eyebrow">STEP 10 / 10</div><h2>{e(step["title"])}</h2><p class="lead">{e(step["action"])}</p><p>{e(step["example"])}</p><div class="fit"><strong>Organization Science fit</strong><br>{e(step["fit"])}<p>{e(step["why"])}</p><a href="https://orgsci.org/" target="_blank" rel="noopener">Call: contribution types and review criteria</a></div><h3>The prompting objection</h3><p>{e(step["prompt"])}</p><p class="limit"><strong>What we cannot claim:</strong> {e(step["limit"])}</p><details><summary>Inspect live pilot evidence · {len(evidence)} records</summary>{evidence_html}</details><div class="actions"><a href="{base}#runs">Open evaluation runs</a><a href="#comparison" class="next">Compare with prompting →</a></div></section>')
    nav = ''.join(f'<a href="#step-{i}"><span>{i:02d}</span> {e(s["title"])}</a>' for i,s in enumerate(content['steps'],1))
    rows = ''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in row)+'</tr>' for row in content['comparison'])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Construct Lab · Co-author walkthrough</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#edf2f1;color:#203b38;font:16px/1.6 system-ui}}main{{max-width:1200px;margin:auto;padding:32px 24px}}h1{{font-size:38px;line-height:1.18;max-width:820px}}h2{{font-size:28px;line-height:1.25}}h3{{margin-bottom:6px}}a{{color:#086d76}}.hero,.step,.panel{{background:white;padding:32px;border:1px solid #d4e0dc;border-radius:12px;margin-bottom:22px}}.hero{{border-top:7px solid #086d76}}.eyebrow,.meta{{font-size:13px;letter-spacing:.03em;color:#4d6861}}.lead{{font-size:18px}}.status,.limit{{padding:16px;background:#fff2d9;border-left:4px solid #ba8b30}}.layout{{display:grid;grid-template-columns:255px 1fr;gap:24px}}.chapters{{position:sticky;top:16px;align-self:start}}.chapters a{{display:block;text-decoration:none;margin:0 0 10px;font-size:14px;padding:7px;border-radius:5px}}.chapters a:hover,.chapters a:focus{{background:#d8e7e1}}.chapters span{{color:#657e75;margin-right:6px}}.fit{{background:#e8f4f0;padding:18px;border-left:4px solid #086d76}}.fit p{{margin:8px 0}}.fit a{{font-size:13px}}details{{padding:12px 0}}summary{{cursor:pointer;font-weight:600}}.record{{margin:8px 0;padding:12px;border:1px solid #d8e1dd;border-radius:6px}}dt{{font-weight:600;text-transform:capitalize}}dd{{margin:0 0 14px;white-space:pre-wrap;overflow-wrap:anywhere}}.actions{{display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;margin-top:20px}}.button,.next{{background:#086d76;color:white;padding:10px 14px;border-radius:6px;text-decoration:none;display:inline-block}}.downloads{{display:flex;gap:12px;flex-wrap:wrap}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #d7e2dd;vertical-align:top}}th{{background:#e8f4f0}}.table-wrap{{overflow:auto}}.step{{scroll-margin-top:15px}}button{{font:inherit;padding:8px;cursor:pointer}}@media(max-width:800px){{.layout{{display:block}}.chapters{{position:static}}h1{{font-size:30px}}.hero,.step,.panel{{padding:22px}}}}@media print{{#app-shell,.chapters,button,.actions{{display:none}}.layout{{display:block}}body{{background:white}}.step,.panel{{break-inside:avoid;border:0}}h1{{font-size:26px}}}}
</style></head><body><main><div class="hero"><div class="eyebrow">CO-AUTHOR WALKTHROUGH · IMMERSIVENESS PILOT · OCTOBER 10, 2026</div>
<h1>{e(content['title'])}</h1><p class="lead">{e(content['thesis'])}</p>
<p class="status"><strong>Start here:</strong> Follow the ten steps below. At each step, inspect the evidence and ask what a strong prompting workflow could reproduce. No coding or approval is needed to explore this page.</p>
<div class="downloads"><a class="button" href="/research-loop?project={quote(project)}">Open executable AI research loop</a><a href="#step-1">Begin walkthrough →</a></div><p>Software release v0.2.0: the AI research loop executes generation, challenges, planning and revision. This historical walkthrough describes the pilot research rationale. Submission drafts are distributed separately and are not required to use the software.</p>
<details><summary>Call requirements and package status</summary><p>{e(content['call'])} <a href="https://orgsci.org/" target="_blank" rel="noopener">Read the call</a>.</p><p>Proposal: 1,816 body words, five pages plus references. Supplement: prototype limits, four-condition comparison, proposed stopping design and submission decisions. Both are editable and require co-author review. Nothing has been submitted or published.</p></details></div>
<div class="layout"><nav class="chapters" aria-label="Walkthrough steps">{nav}<a href="#comparison">Prompting comparison</a><a href="#next">Your next actions</a></nav><div>{''.join(chapters)}</div></div>
<section class="panel" id="comparison"><h2>Make the skeptical comparison a research study</h2><p>Proposed study, not completed evidence. Match model, source access, expertise and resource budgets. Use independent held-out tasks and judges. Primary outcome: theoretical discrimination; assess audit accuracy, correction sensitivity, unsupported closure, time and cost separately.</p><div class="table-wrap"><table><thead><tr><th>Condition</th><th>What researchers receive</th><th>What the comparison can establish</th></tr></thead><tbody>{rows}</tbody></table></div><p class="limit">{e(content['verdict'])}</p><p>Thresholds, sample size, rating rubric and analysis must be fixed after a development pilot and before confirmation. The application does not yet automate this experiment.</p></section>
<section class="panel" id="next"><h2>What you and your co-authors do next</h2><p>{e(content['next'])}</p><ol><li>Review the proposal's scientific claim and the four-condition comparison.</li><li>Assign an evaluation lead and an artifact/reproducibility lead; confirm authorship and resources.</li><li>Prepare a rights-cleared data snapshot and clean release, verify reviewer access, and check portal instructions before submitting.</li></ol><p><strong>Deadline on the call:</strong> November 1, 2026. Current local files are ready for discussion; repository release and journal submission are still separate actions.</p><button onclick="window.print()">Print walkthrough</button></section></main><script src="/shell.js"></script></body></html>'''
