"""Researcher-directed next-evidence planning; no automated saturation inference."""
import json
from uuid import uuid4
from .definitions import DefinitionStore
from .store import Conflict, required

class LearningStore(DefinitionStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.executescript('''CREATE TABLE IF NOT EXISTS learning_questions(
  id TEXT PRIMARY KEY, project TEXT REFERENCES projects(id), version INTEGER NOT NULL,
  definition_version INTEGER NOT NULL, question TEXT NOT NULL, rationale TEXT NOT NULL,
  evidence_plan TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL,
  conclusion TEXT NOT NULL, evidence TEXT NOT NULL);''')
 def learning(self,project):
  w=self.workspace(project)
  return {'project':w['project'],'approved':w['history'][0] if w['history'] else None,
  'questions':[dict(r, evidence=json.loads(r['evidence'])) for r in self.db.execute('SELECT * FROM learning_questions WHERE project=? ORDER BY CASE priority WHEN \'high\' THEN 0 WHEN \'medium\' THEN 1 ELSE 2 END,rowid',(project,))], 'passages':w['passages'],'papers':self.papers(project)}
 def save_question(self,project,b):
  actor=required(b.get('actor'));reason=required(b.get('reason'))
  fields={k:required(b.get(k)) for k in ('question','rationale','evidence_plan','priority','status')}
  if any(len(v)>10000 for v in fields.values()):raise ValueError('Question fields are too long')
  if fields['priority'] not in ('high','medium','low') or fields['status'] not in ('open','investigating','resolved','deferred'):raise ValueError('Invalid priority or status')
  conclusion=b.get('conclusion','');evidence=b.get('evidence',[])
  if not isinstance(conclusion,str) or len(conclusion)>10000 or not isinstance(evidence,list) or any(not isinstance(x,str) for x in evidence):raise ValueError('Invalid conclusion or evidence')
  evidence=list(dict.fromkeys(evidence))
  if fields['status']=='resolved' and (not conclusion.strip() or not evidence):raise ValueError('Resolving requires a conclusion and accepted evidence')
  with self.db:
   self.db.execute('BEGIN IMMEDIATE')
   p=self.db.execute('SELECT version FROM projects WHERE id=?',(project,)).fetchone()
   if p is None:raise KeyError('Unknown project')
   if p['version']==0:raise ValueError('Approve a definition before planning its next evidence')
   if b.get('definition_version')!=p['version']:raise Conflict('The approved definition changed. Reload and reconsider this question.')
   qid=b.get('id') or str(uuid4());old=self.db.execute('SELECT * FROM learning_questions WHERE id=? AND project=?',(qid,project)).fetchone()
   if b.get('id') and old is None:raise KeyError('Unknown question')
   version=old['version'] if old else 0
   if b.get('expected_version')!=version:raise Conflict('This question changed. Copy your edits before reloading.')
   for cid in evidence:
    c=self.db.execute('SELECT c.status,s.project FROM claims c JOIN sources s ON s.id=c.source WHERE c.id=?',(cid,)).fetchone()
    if c is None or c['status']!='verified' or c['project']!=project:raise ValueError('Link accepted evidence from this project')
   self.db.execute('INSERT OR REPLACE INTO learning_questions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(qid,project,version+1,p['version'],fields['question'],fields['rationale'],fields['evidence_plan'],fields['priority'],fields['status'],conclusion,json.dumps(evidence)))
   self.event(project,'learning_question_saved',dict(fields,id=qid,version=version+1,definition_version=p['version'],conclusion=conclusion,evidence=evidence,actor=actor,reason=reason))
  return self.learning(project)
 def export(self,project):
  result=super().export(project);result['learning_questions']=self.learning(project)['questions'];return result
