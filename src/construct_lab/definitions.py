"""Editable construct drafts and immutable approval snapshots."""
import json
from uuid import uuid4
from .extraction import ExtractionStore
from .store import Conflict, required

FIELDS = ('definition','dimensions','boundaries','disagreements','questions')

class DefinitionStore(ExtractionStore):
    def __init__(self, path):
        super().__init__(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS definition_drafts(
          project TEXT PRIMARY KEY REFERENCES projects(id), version INTEGER NOT NULL,
          content TEXT NOT NULL, evidence TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS definition_snapshots(
          revision TEXT PRIMARY KEY REFERENCES revisions(id), content TEXT NOT NULL);
        ''')

    def workspace(self, project):
        p=self.db.execute('SELECT * FROM projects WHERE id=?',(project,)).fetchone()
        if p is None: raise KeyError('Unknown project')
        d=self.db.execute('SELECT * FROM definition_drafts WHERE project=?',(project,)).fetchone()
        history=[]
        for r in self.db.execute('SELECT r.*,s.content FROM revisions r LEFT JOIN definition_snapshots s ON s.revision=r.id WHERE r.project=? ORDER BY r.version DESC',(project,)):
            x=dict(r);x['evidence']=json.loads(x['evidence']);x['content']=json.loads(x['content']) if x['content'] else {'definition':x['definition']};history.append(x)
        return {'project':dict(p),'draft':{'version':d['version'],'content':json.loads(d['content']),'evidence':json.loads(d['evidence'])} if d else {'version':0,'content':dict.fromkeys(FIELDS,''),'evidence':[]},'history':history,'passages':self.passages(project)}

    def save_definition(self, project, body, approve=False):
        actor=required(body.get('actor'));reason=required(body.get('rationale'))
        content=body.get('content');evidence=body.get('evidence')
        if not isinstance(content,dict) or set(content)!=set(FIELDS):raise ValueError('All construct fields are required')
        if any(not isinstance(v,str) or len(v)>20000 for v in content.values()):raise ValueError('Each field must be text under 20,000 characters')
        required(content['definition'])
        if not isinstance(evidence,list) or not evidence or any(not isinstance(x,str) for x in evidence):raise ValueError('Select accepted supporting evidence')
        evidence=list(dict.fromkeys(evidence))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            p=self.db.execute('SELECT version FROM projects WHERE id=?',(project,)).fetchone()
            if p is None:raise KeyError('Unknown project')
            d=self.db.execute('SELECT version FROM definition_drafts WHERE project=?',(project,)).fetchone()
            version=d['version'] if d else 0
            if body.get('expected_version')!=version:raise Conflict('Draft changed. Reload before saving; copy your edits first.')
            for cid in evidence:
                r=self.db.execute('SELECT c.status,s.project FROM claims c JOIN sources s ON s.id=c.source WHERE c.id=?',(cid,)).fetchone()
                if r is None or r['project']!=project or r['status']!='verified':raise ValueError('Evidence must be accepted in this project')
            if approve and (body.get('confirmed') is not True or body.get('expected_approved_version')!=p['version']):raise Conflict('Confirm approval of the current definition version')
            self.db.execute('INSERT OR REPLACE INTO definition_drafts VALUES(?,?,?,?)',(project,version+1,json.dumps(content),json.dumps(evidence)))
            self.event(project,'definition_draft_saved',{'version':version+1,'content':content,'evidence':evidence,'actor':actor,'rationale':reason})
            if approve:
                rid=str(uuid4());av=p['version']+1
                self.db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?)',(rid,project,av,content['definition'],json.dumps(evidence),actor,reason))
                self.db.execute('INSERT INTO definition_snapshots VALUES(?,?)',(rid,json.dumps(content)))
                self.db.execute('UPDATE projects SET version=? WHERE id=?',(av,project))
                self.event(project,'definition_approved',{'revision':rid,'version':av,'reviewer':actor,'rationale':reason})
        return self.workspace(project)

    def export(self,project):
        result=super().export(project)
        w=self.workspace(project)
        result['definition_workspace']={'draft':w['draft'],'history':w['history']}
        return result
