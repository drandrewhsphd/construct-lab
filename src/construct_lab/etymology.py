"""Versioned linguistic evidence and explicitly conjectural theory development."""
import json
from uuid import uuid4
from urllib.parse import urlsplit
from .navigation import AppStore
from .store import Conflict,required
SCHEMA={
 'run':['title','run_mode','run_phase','coordinator','scope','preregistration'],
 'reviewer':['title','reviewer_role','independence','prior_exposure'],
 'observation':['title','participant_code','context','observed','measurements','provenance','limitations'],
 'result':['title','summary','analysis','deviations','conclusion','limitations'],
 'protocol':['title','objective','design','sampling','materials','measures','procedure','analysis','decision_rules','independence','limitations'],
 'revision':['title','before_id','after_id','change_reason','evidence_interpretation','limitations'],
 'finding':['title','citation','url','locator','evidence_type','observation','limitations'],
 'task':['title','question','search_plan','owner','priority','status','findings_summary','decision','resolution'],
 'historical':['title','term','date','citation','url','definition','unit','context','locator','limitations'],
 'comparison':['title','retained','changed','excluded','justification','test','limitations'],
 'source':['title','url','excerpt','summary','language','historical_period','locator','accessed','limitations'],
 'interpretation':['title','claim','inferential_bridge','assumptions','alternative'],
 'definition':['title','definition','unit','inclusion','exclusion','counterexample'],
 'relationship':['title','role','mechanism','prediction','alternative','test'],
 'case':['title','scenario','origin','purpose','notes'],
 'assessment':['title','classification','rationale','evidence_needed','assessor_independence','limitations']}
ALLOWED={'run':{'protocol'},'reviewer':{'run'},'observation':{'run','reviewer'},'result':{'run','observation'},'protocol':{'definition','finding','case'},'revision':{'definition','finding'},'finding':set(),'task':{'assessment','definition','case','finding'},'historical':set(),'comparison':{'source','historical','definition'},'source':set(),'interpretation':{'source'},'definition':{'interpretation','finding'},'relationship':{'definition','interpretation'},'case':{'definition'},'assessment':{'definition','case'}}
REQUIRED={'run':{'protocol'},'reviewer':{'run'},'observation':{'run','reviewer'},'result':{'run','observation'},'protocol':{'definition'},'revision':{'definition','finding'},'finding':set(),'task':{'assessment','definition','case'},'historical':set(),'comparison':{'source','historical','definition'},'source':set(),'interpretation':{'source'},'definition':{'interpretation'},'relationship':{'definition'},'case':set(),'assessment':{'definition','case'}}
class EtymologyStore(AppStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.executescript('''CREATE TABLE IF NOT EXISTS etymology_records(id TEXT PRIMARY KEY,project TEXT NOT NULL,kind TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,links TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS etymology_history(id TEXT PRIMARY KEY,record TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,links TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS etymology_pilots(name TEXT PRIMARY KEY,project TEXT NOT NULL);''')
 def etymology(self,project):
  w=self.workspace(project);rows=[]
  versions={r['id']:r['version'] for r in self.db.execute('SELECT id,version FROM etymology_records WHERE project=?',(project,))}
  for r in self.db.execute('SELECT * FROM etymology_records WHERE project=? ORDER BY rowid',(project,)):
   x=dict(r);x['content']=json.loads(x['content']);x['links']=json.loads(x['links']);x['stale']=any(versions.get(l['id'])!=l['version'] for l in x['links']);x['history']=[dict(h,content=json.loads(h['content']),links=json.loads(h['links'])) for h in self.db.execute('SELECT * FROM etymology_history WHERE record=? ORDER BY version DESC',(x['id'],))];rows.append(x)
  for x in rows:
   if x['kind']=='assessment':
    x['content'].setdefault('evidence_needed','Not recorded in this earlier version.')
    for h in x['history']:h['content'].setdefault('evidence_needed','Not recorded in this earlier version.')
  return dict(revisions=revision_views(rows),boundary=boundary_matrix(rows),project=w['project'],records=rows,schema=SCHEMA,allowed={k:sorted(v) for k,v in ALLOWED.items()})
 def save_etymology(self,project,b):
  kind=b.get('kind');content=b.get('content');actor=required(b.get('actor'));reason=required(b.get('reason'))
  if kind not in SCHEMA or not isinstance(content,dict) or set(content)!=set(SCHEMA[kind]):raise ValueError('Use all fields for the selected record type')
  if any(not isinstance(v,str) or len(v)>10000 for v in content.values()):raise ValueError('Fields must be text under 10,000 characters')
  for v in content.values():required(v)
  if len(actor)>200 or len(reason)>2000:raise ValueError('Name or save reason too long')
  if kind in ('source','historical','finding') and (urlsplit(content['url']).scheme not in ('http','https') or not urlsplit(content['url']).netloc):raise ValueError('Source URL must be an HTTP or HTTPS link')
  if kind=='relationship' and content['role'] not in ('antecedent','outcome','moderator','mechanism','competing explanation'):raise ValueError('Choose a relationship role')
  if kind=='case' and content['purpose'] not in ('development','evaluation candidate'):raise ValueError('Choose a case purpose')
  if kind=='assessment' and content['classification'] not in ('included','excluded','uncertain'):raise ValueError('Choose a classification')
  if kind=='task':
   if content['status'] not in ('open','investigating','resolved','deferred') or content['priority'] not in ('high','normal','low') or content['decision'] not in ('pending','retain definition','revise definition','inconclusive'):raise ValueError('Choose a valid task status, priority and decision')
   if content['status']=='resolved' and content['decision']=='pending':raise ValueError('Record a decision before resolving the task')
  if kind=='finding' and content['evidence_type'] not in ('empirical study','scholarly argument','linguistic source','other'):raise ValueError('Choose an evidence type')
  if kind=='run' and (content['run_mode'] not in ('demonstration','empirical') or content['run_phase'] not in ('planned','active','completed')):raise ValueError('Choose run mode and phase')
  links=b.get('links')
  if not isinstance(links,list) or any(not isinstance(l,dict) or set(l)!={'id','version'} or not isinstance(l['id'],str) or type(l['version']) is not int for l in links):raise ValueError('Select versioned supporting records')
  if len({l['id'] for l in links})!=len(links):raise ValueError('Duplicate links')
  with self.db:
   self.db.execute('BEGIN IMMEDIATE');self.workspace(project)
   rid=b.get('id') or str(uuid4());old=self.db.execute('SELECT * FROM etymology_records WHERE id=? AND project=?',(rid,project)).fetchone()
   if b.get('id') and old is None:raise ValueError('Unknown record in this project')
   version=old['version'] if old else 0
   if b.get('expected_version')!=version:raise Conflict('Record changed. Copy your edits and reload.')
   if old and old['kind']!=kind:raise ValueError('Record type cannot change')
   kinds=[]
   for l in links:
    target=self.db.execute('SELECT * FROM etymology_records WHERE id=? AND project=?',(l['id'],project)).fetchone()
    if not target or target['kind'] not in ALLOWED[kind]:raise ValueError('Link appropriate supporting records from this project')
    frozen=kind in ('run','reviewer','observation','result') and ((old and l in json.loads(old['links'])) or (target['kind']=='run' and l['version']==1))
    if frozen and not self.db.execute('SELECT 1 FROM etymology_history WHERE record=? AND version=?',(l['id'],l['version'])).fetchone():raise ValueError('Missing frozen version')
    if target['version']!=l['version'] and not frozen:raise Conflict('Supporting record changed. Reload and reassess your interpretation.')
    kinds.append(target['kind'])
   if not REQUIRED[kind].issubset(kinds):raise ValueError('Missing required supporting source, interpretation, definition or case')
   if kind=='assessment' and (kinds.count('definition')!=1 or kinds.count('case')!=1):raise ValueError('An assessment requires exactly one definition and one case')
   if kind=='comparison' and (kinds.count('definition')!=1 or kinds.count('historical')!=1):raise ValueError('A comparison requires exactly one candidate definition, one historical definition and at least one linguistic source')
   if kind=='task':
    if any(kinds.count(k)!=1 for k in ('assessment','definition','case')):raise ValueError('A task requires exactly one assessment, its definition and its case')
    targets={k:[l for l in links if self.db.execute('SELECT kind FROM etymology_records WHERE id=?',(l['id'],)).fetchone()[0]==k] for k in ('assessment','definition','case')}
    assessment=self.db.execute('SELECT links FROM etymology_records WHERE id=?',(targets['assessment'][0]['id'],)).fetchone()
    if any(l not in json.loads(assessment['links']) for k in ('definition','case') for l in targets[k]):raise Conflict('Reassess the judgment against the current case and definition before creating or updating its task')
    if content['status']=='resolved' and 'finding' not in kinds:raise ValueError('Link at least one documented finding before resolving the task')
   if kind=='revision':
    if kinds.count('definition')!=2 or content['before_id']==content['after_id']:raise ValueError('Choose two distinct candidate definitions')
    definitions={l['id'] for l in links if self.db.execute('SELECT kind FROM etymology_records WHERE id=?',(l['id'],)).fetchone()[0]=='definition'}
    if definitions!={content['before_id'],content['after_id']}:raise ValueError('Before and after must match the two linked definitions')
   if kind=='run':
    if len(links)!=1:raise ValueError('A run requires exactly one protocol')
    if old and (links!=json.loads(old['links']) or content['run_mode']!=json.loads(old['content'])['run_mode']):raise ValueError('Run protocol and mode are frozen; create a new run for a new protocol or mode')
    if content['run_phase']=='completed':
     results=[r for r in self.db.execute("SELECT links FROM etymology_records WHERE project=? AND kind='result'",(project,)) if any(l['id']==rid for l in json.loads(r['links']))]
     if not results:raise ValueError('Record observations and a result before completing the run')
   if kind in ('reviewer','observation','result'):
    runs=[l for l,k in zip(links,kinds) if k=='run']
    if len(runs)!=1 or runs[0]['version']!=1:raise ValueError('Link exactly one run at its frozen version 1')
    runid=runs[0]['id']
    if old and next(l['id'] for l in json.loads(old['links']) if self.db.execute('SELECT kind FROM etymology_records WHERE id=?',(l['id'],)).fetchone()[0]=='run')!=runid:raise ValueError('Records cannot move between runs')
    run=self.db.execute('SELECT content FROM etymology_records WHERE id=?',(runid,)).fetchone()
    if json.loads(run['content'])['run_phase']=='completed':raise ValueError('Reopen the run before editing its records')
    if kind=='observation' and kinds.count('reviewer')!=1:raise ValueError('Select exactly one assigned reviewer')
    for l,k in zip(links,kinds):
     if k in ('reviewer','observation'):
      linked=json.loads(self.db.execute('SELECT links FROM etymology_history WHERE record=? AND version=?',(l['id'],l['version'])).fetchone()[0])
      if not any(x['id']==runid for x in linked):raise ValueError('Reviewer and observations must belong to this run')
   payload=json.dumps(content);linked=json.dumps(links)
   self.db.execute('INSERT INTO etymology_records VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,content=excluded.content,links=excluded.links',(rid,project,kind,version+1,payload,linked))
   self.db.execute('INSERT INTO etymology_history(id,record,version,content,links,actor,reason) VALUES(?,?,?,?,?,?,?)',(str(uuid4()),rid,version+1,payload,linked,actor,reason))
  return self.etymology(project)
 def navigation(self):
  d=super().navigation();ids={r[0] for r in self.db.execute('SELECT DISTINCT project FROM etymology_records')}
  for p in d['projects']:
   if p['id'] in ids:p['next']=dict(path='etymology',label='Open etymology workspace',detail='Inspect sourced word history, then proposed interpretations, definitions and relationships. Pilot claims are conjectures; no manual approval is needed to explore the workspace.')
  return d
 def export(self,project):
  d=super().export(project);d['etymology_workspace']=self.etymology(project)['records'];return d


def boundary_matrix(records):
 """Describe judgments without treating agreement as correctness or saturation."""
 definitions=[r for r in records if r['kind']=='definition']
 cases=[r for r in records if r['kind']=='case']
 rows=[]
 for case in cases:
  cells=[];labels=set();complete=True
  for definition in definitions:
   assessments=[r for r in records if r['kind']=='assessment' and {case['id'],definition['id']}.issubset({l['id'] for l in r['links']})]
   current=[r for r in assessments if not r['stale']]
   values={r['content']['classification'] for r in current}
   # Conflicting or uncertain assessors are never silently collapsed into a verdict.
   verdict=next(iter(values)) if len(values)==1 else ('mixed judgments' if values else 'not assessed')
   if verdict not in ('included','excluded'):complete=False
   else:labels.add(verdict)
   cells.append(dict(definition=definition['id'],assessments=[r['id'] for r in assessments],verdict=verdict,stale=sum(r['stale'] for r in assessments)))
  status='Different classifications' if len(labels)>1 else ('Same classification' if complete and definitions else 'Unresolved or incomplete')
  rows.append(dict(case=case['id'],status=status,cells=cells))
 return dict(definitions=[r['id'] for r in definitions],rows=rows)


def revision_views(records):
 byid={r['id']:r for r in records};result=[]
 for r in records:
  if r['kind']!='revision':continue
  snapshots={}
  for role in ('before_id','after_id'):
   rid=r['content'][role];link=next(l for l in r['links'] if l['id']==rid)
   h=next(h for h in byid[rid]['history'] if h['version']==link['version'])
   snapshots[role]=dict(id=rid,version=h['version'],content=h['content'])
  before=snapshots['before_id'];after=snapshots['after_id'];impact=[]
  for a in records:
   if a['kind']!='assessment' or not any(l['id']==before['id'] for l in a['links']):continue
   case=next(byid[l['id']] for l in a['links'] if byid[l['id']]['kind']=='case')
   followups=[x for x in records if x['kind']=='assessment' and not x['stale'] and any(l['id']==after['id'] and l['version']==after['version'] for l in x['links']) and any(l['id']==case['id'] for l in x['links'])]
   impact.append(dict(assessment=a['id'],case=case['id'],followups=[x['id'] for x in followups],status='Review revision first' if r['stale'] else ('Judgment recorded for target' if followups else 'Needs reassessment for target')))
  result.append(dict(id=r['id'],before=before,after=after,impact=impact))
 return result
