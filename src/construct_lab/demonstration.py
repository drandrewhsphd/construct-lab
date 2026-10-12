"""Isolated synthetic demonstration, built with the public storage workflows."""
import json
from .saturation import SaturationStore,GATES

class DemonstrationStore(SaturationStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.execute('CREATE TABLE IF NOT EXISTS demonstrations(project TEXT PRIMARY KEY,manifest TEXT NOT NULL)')
 def demonstration(self,project):
  row=self.db.execute('SELECT manifest FROM demonstrations WHERE project=?',(project,)).fetchone()
  if not row:raise KeyError('This project is not a registered demonstration')
  return dict(project=self.workspace(project)['project'],manifest=json.loads(row[0]),dashboard=self.dashboard(project),rounds=self.rounds(project)['rounds'],novelty=self.novelty(project)['summary'],saturation=self.saturation(project))

def build_demo(store,pdfs):
 """Build once per database. Original projects remain untouched."""
 existing=store.db.execute('SELECT project FROM demonstrations LIMIT 1').fetchone()
 if existing:return existing[0]
 p=store.create_project('DEMONSTRATION - Synthetic learning workflow')
 actor='AI assistant - SYNTHETIC SYSTEM DEMONSTRATION';reason='Scripted workflow exercise; not real research or independent human validation.'
 interpretations=['SYNTHETIC: A desire to understand illustrates a learning motive.','SYNTHETIC: Learning and reassurance can coexist in the invented episode.','SYNTHETIC: Another learning-oriented example repeats the existing pattern.']
 manifest=dict(kind='synthetic demonstration',documents=[],passages=[],categories=['baseline','challenge','confirmation'],limitations='No scholarly evidence, paid AI extraction, or independent validation. PDF text is imported and exact passages are selected deterministically to exercise provenance and review.')
 question=None
 for i,pdf in enumerate(pdfs):
  d=store.import_pdf(p,pdf,f'SYNTHETIC-demo-{i+1}.pdf')['id'];page=store.paper(p,d)['pages'][0];quote=page['text'].strip();start=page['text'].index(quote)
  passage=store.propose_passage(p,d,1,page['text_revision'],page['text_hash'],start,start+len(quote),quote,'definition',interpretations[i],actor)
  store.review_passage(p,passage,1,'verified','definition',interpretations[i],actor,reason,True)
  manifest['documents'].append(d);manifest['passages'].append(passage)
  claim=next(x['claim_id'] for x in store.passages(p) if x['id']==passage)
  if i==0:
   content=dict(definition='SYNTHETIC DEMO: Learning-oriented inquiry is seeking information to improve understanding.',dimensions='Desire to understand; information seeking.',boundaries='Invented examples only. Information seeking does not by itself establish motive.',disagreements='Mixed motives require explicit consideration.',questions='Can learning and reassurance coexist in an example?')
   store.save_definition(p,dict(actor=actor,rationale=reason,content=content,evidence=[claim],expected_version=0,expected_approved_version=0,confirmed=True),True)
   store.save_question(p,dict(actor=actor,reason=reason,question='SYNTHETIC: Can both motives coexist?',rationale='Exercise boundary assessment.',evidence_plan='Inspect the next invented mixed-motive example.',priority='high',status='open',conclusion='',evidence=[],definition_version=1,expected_version=0))
   question=store.learning(p)['questions'][0]
  elif i==1:
   store.save_question(p,dict(actor=actor,reason=reason,id=question['id'],question=question['question'],rationale=question['rationale'],evidence_plan=question['evidence_plan'],priority='high',status='resolved',conclusion='In this invented scenario both motives coexist. This resolves only the scripted demonstration question.',evidence=[claim],definition_version=1,expected_version=1))
  store.save_coding(p,dict(actor=actor,reason='AI workflow demonstration. '+reason,passage=passage,passage_version=2,definition_version=1,expected_version=0,content=dict(level='episode',learning='supported',reassurance='supported' if i==1 else 'not established',learning_evidence='The invented example explicitly describes wanting understanding.',reassurance_evidence='The second invented example explicitly describes reassurance.' if i==1 else '',confidence='high',rationale='Workflow demonstration using synthetic evidence; no population inference.',status='reviewed')))
  r=store.rounds(p);store.save_round(p,dict(title=['Synthetic baseline','Mixed-motive challenge','Confirming example'][i],actor=actor,note=reason,expected_sequence=r['expected_sequence'],current_digest=r['current_digest']))
  if i:
   rid=store.rounds(p)['rounds'][-1]['id']
   store.save_novelty(p,dict(actor=actor,reason=reason,round_id=rid,passage=passage,expected_version=0,content=dict(category=['','challenge','confirmation'][i],comparison='Prior synthetic learning-oriented example.',rationale=interpretations[i],implication='Retain mixed-motive caution; these invented examples do not validate a theory.',confidence='high',status='reviewed',mode='demonstration')))
 s=store.saturation(p);store.save_saturation(p,dict(actor=actor,reason=reason+' Thresholds chosen only to illustrate the controls.',expected_version=0,context=s['context'],rules=dict(rounds=2,min_passages=1,max_novelty_percent=5),checks={k:dict(status='unmet',rationale='Synthetic demonstration cannot establish research coverage, validation or resolved theoretical boundaries.') for k in GATES}))
 with store.db:store.db.execute('INSERT INTO demonstrations VALUES(?,?)',(p,json.dumps(manifest)))
 return p
