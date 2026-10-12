"""Read-only, self-contained evaluation run reports with versioned evidence trails."""
from datetime import datetime,timezone
from html import escape

def render_run_report(store,project,run_id):
 data=store.etymology(project);records={r['id']:r for r in data['records']}
 run=records.get(run_id)
 if not run or run['kind']!='run':raise KeyError('Run not found in this project')
 children=[r for r in records.values() if r['kind'] in ('reviewer','observation','result') and any(l['id']==run_id for l in r['links'])]
 e=lambda v:escape(str(v),quote=True)
 stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
 def fields(content):return '<dl>'+''.join('<dt>'+e(k.replace('_',' ').capitalize())+'</dt><dd>'+e(v)+'</dd>' for k,v in content.items())+'</dl>'
 def card(r):
  h=r['history'][0]
  return '<article><h3>'+e(r['content']['title'])+' · V'+str(r['version'])+'</h3><p class="meta">Recorded by '+e(h['actor'])+' · '+e(h['created_at'])+' UTC</p>'+fields(r['content'])+'<p><strong>Save rationale:</strong> '+e(h['reason'])+'</p><p>Saved references: '+', '.join('<a href="#ref-'+e(l['id'])+'-'+str(l['version'])+'">'+e(records[l['id']]['kind'])+' V'+str(l['version'])+'</a>' for l in r['links'])+'</p></article>'
 counts={kind:sum(r['kind']==kind for r in children) for kind in ('reviewer','observation','result')}
 mode=run['content']['run_mode'];warning='SYNTHETIC DEMONSTRATION — not participant data or empirical validation.' if mode=='demonstration' else 'EMPIRICAL RUN RECORD — entries are user-recorded; this report does not verify data collection or validity.'
 pending=[]
 if counts['reviewer']==0:pending.append('No reviewer assignments recorded.')
 if counts['observation']==0:pending.append('No observations recorded. No empirical outcome can be reported.')
 if counts['result']==0:pending.append('No results, analysis or conclusions recorded.')
 if run['content']['run_phase']!='completed':pending.append('Run is '+run['content']['run_phase']+'; it is not marked completed.')
 if mode=='demonstration':pending.append('Demonstration completion does not mean the evaluation protocol was executed.')
 trail=[];seen=set()
 def visit(rid,version):
  if (rid,version) in seen:return
  seen.add((rid,version));r=records[rid];h=next(x for x in r['history'] if x['version']==version)
  trail.append('<article id="ref-'+e(rid)+'-'+str(version)+'"><h3>'+e(r['kind'].capitalize())+': '+e(h['content']['title'])+' · V'+str(version)+'</h3><p class="meta">'+e(rid)+' · '+e(h['actor'])+' · '+e(h['created_at'])+' UTC'+(' · a newer version exists' if r['version']!=version else '')+'</p>'+fields(h['content'])+'<p><strong>Save rationale:</strong> '+e(h['reason'])+'</p></article>')
  for l in h['links']:visit(l['id'],l['version'])
 for r in [run,*children]:
  for l in r['links']:visit(l['id'],l['version'])
 sections=''.join('<section><h2>'+title+'</h2>'+(''.join(card(r) for r in children if r['kind']==kind) or '<p>None recorded.</p>')+'</section>' for kind,title in [('reviewer','Reviewer assignments and exposure'),('observation','Observations and provenance'),('result','Results, deviations and conclusions')])
 return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(run['content']['title'])+' — Run summary</title><style>body{font:16px/1.55 system-ui;color:#203748;background:#eef3f6;margin:0}main{max-width:1000px;margin:auto;padding:30px}section,article{background:white;padding:22px;margin:18px 0;border:1px solid #d5e1e6;border-radius:8px}h1,h2{color:#145e67}dt{font-weight:700;margin-top:16px}dd{margin:4px 0;white-space:pre-wrap;overflow-wrap:anywhere}.banner{background:#fff1cf;padding:16px}.meta{color:#526575;font-size:14px;overflow-wrap:anywhere}a{color:#086d76}button{padding:10px;font:inherit}@media print{body{background:white}main{padding:0}button{display:none}article{break-inside:auto}h2,h3,dt{break-after:avoid}}</style><main><h1>Evaluation run summary</h1><h2>'+e(run['content']['title'])+'</h2><p class="banner">'+e(warning)+'</p><p>Project: '+e(data['project']['name'])+' · Report generated '+e(stamp)+' (UTC)</p><p class="meta">Run ID: '+e(run_id)+' · Current run V'+str(run['version'])+'. This is a point-in-time rendering. Current reviewer, observation and result records appear below; the appendix preserves the exact versions referenced by them, including older versions.</p><button onclick="window.print()">Print / Save as PDF</button><p>Reviewers: '+str(counts['reviewer'])+' · Observations: '+str(counts['observation'])+' · Result records: '+str(counts['result'])+'. Counts are records, not unique participants or independent replications.</p><section><h2>Readiness and unresolved items</h2>'+(''.join('<p>'+e(x)+'</p>' for x in pending) or '<p>Recording steps are complete; scientific adequacy still requires review.</p>')+'<p>Blinding and reviewer identity are not enforced by this local workspace. No validity, fit or saturation score is inferred.</p></section><section><h2>Run scope and registration</h2>'+card(run)+'</section>'+sections+'<section><h2>Frozen protocol and referenced evidence appendix</h2><p>These are the exact saved versions used, not replacements with the latest text. Linked literature is context, not new run observations.</p>'+''.join(trail)+'</section></main></html>'
