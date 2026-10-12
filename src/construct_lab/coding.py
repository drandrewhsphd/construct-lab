"""Separate, versioned motive coding; never changes accepted passages."""
import json
from uuid import uuid4
from .learning import LearningStore
from .store import Conflict, required

class CodingStore(LearningStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.executescript('''CREATE TABLE IF NOT EXISTS coding_records(id TEXT PRIMARY KEY,project TEXT NOT NULL,passage TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,UNIQUE(project,passage));
  CREATE TABLE IF NOT EXISTS coding_history(id TEXT PRIMARY KEY,record TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
 def coding(self,project):
  w=self.workspace(project)
  records=[]
  for r in self.db.execute('SELECT * FROM coding_records WHERE project=? ORDER BY rowid',(project,)):
   x=dict(r);x['content']=json.loads(x['content']);x['history']=[dict(h,content=json.loads(h['content'])) for h in self.db.execute('SELECT * FROM coding_history WHERE record=? ORDER BY version DESC',(r['id'],))];records.append(x)
  return dict(project=w['project'],records=records,passages=[p for p in w['passages'] if p['status']=='verified'])
 def save_coding(self,project,b):
  actor=required(b.get('actor'));reason=required(b.get('reason'));c=b.get('content')
  if not isinstance(c,dict):raise ValueError('Coding content is required')
  allowed={'level','learning','reassurance','confidence','rationale','learning_evidence','reassurance_evidence','status'}
  if set(c)!=allowed or any(not isinstance(v,str) or len(v)>10000 for v in c.values()):raise ValueError('Invalid coding fields')
  if c['level'] not in ('episode','measure','study result','theory','not applicable'):raise ValueError('Choose a coding level')
  if any(c[k] not in ('supported','explicitly absent','not established') for k in ('learning','reassurance')):raise ValueError('Invalid motive evidence status')
  if c['confidence'] not in ('low','moderate','high') or c['status'] not in ('draft','reviewed'):raise ValueError('Invalid review status')
  required(c['rationale'])
  for k in ('learning','reassurance'):
   if c[k]!='not established':required(c[k+'_evidence'])
  with self.db:
   self.db.execute('BEGIN IMMEDIATE')
   p=self.db.execute('SELECT * FROM projects WHERE id=?',(project,)).fetchone()
   if p is None:raise KeyError('Unknown project')
   if b.get('definition_version')!=p['version']:raise Conflict('Definition changed. Reload before saving.')
   passage=self.db.execute('SELECT * FROM passages WHERE id=? AND project=? AND status=?',(b.get('passage'),project,'verified')).fetchone()
   if passage is None:raise ValueError('Choose accepted evidence from this project')
   if b.get('passage_version')!=passage['version']:raise Conflict('Source passage changed. Reload and review it again.')
   old=self.db.execute('SELECT * FROM coding_records WHERE project=? AND passage=?',(project,passage['id'])).fetchone()
   version=old['version'] if old else 0
   if b.get('expected_version')!=version:raise Conflict('This code changed elsewhere. Copy your edits and reload.')
   c=dict(c,guide_version='0.1',definition_version=p['version'],passage_version=passage['version'])
   c['code']='Not applicable' if c['level']=='not applicable' else ('Mixed motives' if c['learning']==c['reassurance']=='supported' else 'Learning supported' if c['learning']=='supported' else 'Reassurance supported' if c['reassurance']=='supported' else 'Unclear / other')
   rid=old['id'] if old else str(uuid4());payload=json.dumps(c)
   self.db.execute('INSERT OR REPLACE INTO coding_records VALUES(?,?,?,?,?)',(rid,project,passage['id'],version+1,payload))
   self.db.execute('INSERT INTO coding_history(id,record,version,content,actor,reason) VALUES(?,?,?,?,?,?)',(str(uuid4()),rid,version+1,payload,actor,reason))
  return self.coding(project)
 def export(self,project):
  result=super().export(project);result['coding_workspace']=self.coding(project)['records'];return result
