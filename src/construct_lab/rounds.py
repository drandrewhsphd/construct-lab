"""Immutable, prospective evidence-round snapshots and inspectable deltas."""
import hashlib
import json
from uuid import uuid4
from .dashboard import DashboardStore
from .store import Conflict, required

class RoundStore(DashboardStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.execute('''CREATE TABLE IF NOT EXISTS evidence_rounds(id TEXT PRIMARY KEY, project TEXT NOT NULL, sequence INTEGER NOT NULL, title TEXT NOT NULL, actor TEXT NOT NULL, note TEXT NOT NULL, snapshot TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(project,sequence))''')
 def snapshot(self,project):
  w=self.workspace(project);coding=self.coding(project)
  return dict(definition_version=w['project']['version'],definition=w['history'][0]['content'] if w['history'] else None,
   papers={p['id']:p for p in self.papers(project)},
   passages={p['id']:{k:p.get(k) for k in ('id','document','page','version','status','interpretation','quote','reviewed_quote')} for p in w['passages'] if p['status']=='verified'},
   coding={r['id']:dict(passage=r['passage'],version=r['version'],content=r['content']) for r in coding['records']},
   questions={q['id']:q for q in self.learning(project)['questions']})
 @staticmethod
 def digest(snapshot):return hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
 @staticmethod
 def delta(old,new):
  result={}
  for kind in ('papers','passages','coding','questions'):
   a=old.get(kind,{}) if old else {};b=new[kind]
   result[kind]=dict(added=[dict(id=k,after=b[k]) for k in sorted(b.keys()-a.keys())],removed=[dict(id=k,before=a[k]) for k in sorted(a.keys()-b.keys())],changed=[dict(id=k,before=a[k],after=b[k]) for k in sorted(a.keys()&b.keys()) if a[k]!=b[k]])
  result['definition_changed']=old is not None and (old['definition_version']!=new['definition_version'] or old['definition']!=new['definition'])
  return result
 def rounds(self,project):
  current=self.snapshot(project);history=[];previous=None
  for row in self.db.execute('SELECT * FROM evidence_rounds WHERE project=? ORDER BY sequence',(project,)):
   r=dict(row);snap=json.loads(r.pop('snapshot'));r['baseline']=previous is None;r['counts']={k:len(snap[k]) for k in ('papers','passages','coding','questions')};r['definition_version']=snap['definition_version'];r['delta']=None if previous is None else self.delta(previous,snap);history.append(r);previous=snap
  return dict(project=self.workspace(project)['project'],rounds=history,current_digest=self.digest(current),expected_sequence=len(history),preview=None if previous is None else self.delta(previous,current),current_counts={k:len(current[k]) for k in ('papers','passages','coding','questions')})
 def save_round(self,project,b):
  title=required(b.get('title'));actor=required(b.get('actor'));note=required(b.get('note'))
  if len(title)>160 or len(actor)>200 or len(note)>10000:raise ValueError('Round title, reviewer or note is too long')
  with self.db:
   self.db.execute('BEGIN IMMEDIATE')
   snapshot=self.snapshot(project)
   count=self.db.execute('SELECT COUNT(*) FROM evidence_rounds WHERE project=?',(project,)).fetchone()[0]
   if b.get('expected_sequence')!=count or b.get('current_digest')!=self.digest(snapshot):raise Conflict('Evidence or round history changed. Refresh and inspect the comparison before saving.')
   if count:
    old=json.loads(self.db.execute('SELECT snapshot FROM evidence_rounds WHERE project=? ORDER BY sequence DESC LIMIT 1',(project,)).fetchone()[0])
    if old==snapshot:raise ValueError('No evidence changes since the last round. Add or revise evidence before recording another round.')
   self.db.execute('INSERT INTO evidence_rounds(id,project,sequence,title,actor,note,snapshot) VALUES(?,?,?,?,?,?,?)',(str(uuid4()),project,count+1,title,actor,note,json.dumps(snapshot)))
  return self.rounds(project)
 def dashboard(self,project):
  d=super().dashboard(project);r=self.rounds(project)
  d['evidence_rounds']=dict(count=len(r['rounds']),latest=r['rounds'][-1] if r['rounds'] else None,pending=r['preview'])
  for dimension in d['saturation']['dimensions']:
   if dimension['name']=='New-evidence yield':
    dimension['status']='Baseline only' if len(r['rounds'])==1 else 'Round comparisons available' if r['rounds'] else 'No baseline recorded'
    dimension['detail']='Saved rounds track additions, revisions and removals. These are record changes, not measured theoretical novelty; stopping thresholds remain unset.'
  return d
 def export(self,project):
  result=super().export(project);result['evidence_rounds']=[dict(r,snapshot=json.loads(r['snapshot'])) for r in self.db.execute('SELECT * FROM evidence_rounds WHERE project=? ORDER BY sequence',(project,))];return result
