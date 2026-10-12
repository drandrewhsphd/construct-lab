"""Versioned researcher judgments against immutable evidence-round context."""
import json
from uuid import uuid4
from .rounds import RoundStore
from .store import Conflict, required

CATEGORIES=('new concept','new relationship','boundary refinement','measurement refinement','challenge','confirmation','unresolved')
FIELDS=('category','comparison','rationale','implication','confidence','status','mode')
class NoveltyStore(RoundStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.executescript('''CREATE TABLE IF NOT EXISTS novelty_assessments(id TEXT PRIMARY KEY,project TEXT NOT NULL,round_id TEXT NOT NULL,passage TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,UNIQUE(project,round_id,passage));
  CREATE TABLE IF NOT EXISTS novelty_history(id TEXT PRIMARY KEY,assessment TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
 def novelty(self,project):
  w=self.workspace(project);rounds=[];previous=None
  for row in self.db.execute('SELECT * FROM evidence_rounds WHERE project=? ORDER BY sequence',(project,)):
   snap=json.loads(row['snapshot']);passages=snap['passages']
   eligible=list(passages) if previous is None else [k for k,v in passages.items() if previous['passages'].get(k)!=v]
   rounds.append(dict(id=row['id'],sequence=row['sequence'],title=row['title'],baseline=previous is None,definition=snap['definition'],prior_definition=previous['definition'] if previous else None,prior_passages=list(previous['passages'].values()) if previous else [],passages=[dict(passages[k],prior=previous['passages'].get(k) if previous else None) for k in eligible]))
   previous=snap
  records=[]
  for r in self.db.execute('SELECT * FROM novelty_assessments WHERE project=?',(project,)):
   x=dict(r);x['content']=json.loads(x['content']);x['history']=[dict(h,content=json.loads(h['content'])) for h in self.db.execute('SELECT * FROM novelty_history WHERE assessment=? ORDER BY version DESC',(r['id'],))];records.append(x)
  summary=[]
  for r in rounds:
   rr=[a for a in records if a['round_id']==r['id']];reviewed=[a for a in rr if a['content']['mode']=='research' and a['content']['status']=='reviewed'];decided=[a for a in reviewed if a['content']['category']!='unresolved'];novel=[a for a in decided if a['content']['category']!='confirmation']
   summary.append(dict(sequence=r['sequence'],baseline=r['baseline'],eligible=len(r['passages']),assessed=len(rr),research_reviewed=len(reviewed),unresolved=sum(a['content']['category']=='unresolved' for a in reviewed),demonstration=sum(a['content']['mode']=='demonstration' for a in rr),novel=len(novel) if not r['baseline'] else None,decided=len(decided) if not r['baseline'] else None))
  return dict(project=w['project'],rounds=rounds,records=records,summary=summary,categories=CATEGORIES)
 def save_novelty(self,project,b):
  actor=required(b.get('actor'));reason=required(b.get('reason'));c=b.get('content')
  if not isinstance(c,dict) or set(c)!=set(FIELDS) or any(not isinstance(v,str) or len(v)>10000 for v in c.values()):raise ValueError('Complete all assessment fields')
  if c['category'] not in CATEGORIES or c['confidence'] not in ('low','moderate','high') or c['status'] not in ('draft','reviewed') or c['mode'] not in ('demonstration','research'):raise ValueError('Invalid assessment choice')
  for k in ('comparison','rationale','implication'):required(c[k])
  if len(actor)>200 or len(reason)>2000:raise ValueError('Reviewer or reason is too long')
  with self.db:
   self.db.execute('BEGIN IMMEDIATE')
   data=self.novelty(project);r=next((r for r in data['rounds'] if r['id']==b.get('round_id')),None)
   if r is None or not any(p['id']==b.get('passage') for p in r['passages']):raise ValueError('Select eligible evidence from this project and round')
   old=self.db.execute('SELECT * FROM novelty_assessments WHERE project=? AND round_id=? AND passage=?',(project,r['id'],b['passage'])).fetchone();v=old['version'] if old else 0
   if b.get('expected_version')!=v:raise Conflict('Assessment changed. Copy your notes and refresh before saving.')
   aid=old['id'] if old else str(uuid4());payload=json.dumps(c)
   self.db.execute('INSERT OR REPLACE INTO novelty_assessments VALUES(?,?,?,?,?,?)',(aid,project,r['id'],b['passage'],v+1,payload))
   self.db.execute('INSERT INTO novelty_history(id,assessment,version,content,actor,reason) VALUES(?,?,?,?,?,?)',(str(uuid4()),aid,v+1,payload,actor,reason))
  return self.novelty(project)
 def dashboard(self,project):
  d=super().dashboard(project);d['novelty_summary']=self.novelty(project)['summary'];return d
 def export(self,project):
  d=super().export(project);d['novelty_assessments']=self.novelty(project)['records'];return d
