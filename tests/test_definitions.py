import tempfile,unittest
from pathlib import Path
from construct_lab.definitions import DefinitionStore,FIELDS
from construct_lab.store import Conflict
class DefinitionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=DefinitionStore(Path(self.tmp.name)/'db');self.p=self.s.create_project('Test')
  src=self.s.add_source(self.p,'Synthetic','1','Example');self.claim=self.s.propose_claim(src,'Example','Synthetic claim');self.s.review_claim(self.claim,'Tester','Synthetic',True)
  self.b=dict(expected_version=0,expected_approved_version=0,content={k:'Draft '+k for k in FIELDS},evidence=[self.claim],actor='Tester',rationale='Test',confirmed=True)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def test_draft_approval_history_conflict(self):
  self.s.save_definition(self.p,self.b)
  self.assertEqual(self.s.workspace(self.p)['project']['version'],0)
  with self.assertRaises(Conflict):self.s.save_definition(self.p,self.b)
  self.b['expected_version']=1;self.s.save_definition(self.p,self.b,True)
  self.b['expected_version']=2;self.b['content']['definition']='Changed';self.s.save_definition(self.p,self.b)
  w=self.s.workspace(self.p);self.assertEqual(w['history'][0]['definition'],'Draft definition');self.assertEqual(w['draft']['content']['definition'],'Changed')
  self.assertIn('definition_workspace',self.s.export(self.p))
 def test_unaccepted_foreign_and_missing_confirmation(self):
  src=self.s.add_source(self.p,'Synthetic','1','Other');claim=self.s.propose_claim(src,'Other','Pending')
  self.b['evidence']=[claim]
  with self.assertRaises(ValueError):self.s.save_definition(self.p,self.b)
  q=self.s.create_project('Other');src=self.s.add_source(q,'Synthetic','1','Foreign');cid=self.s.propose_claim(src,'Foreign','Other');self.s.review_claim(cid,'Tester','Test',True);self.b['evidence']=[cid]
  with self.assertRaises(ValueError):self.s.save_definition(self.p,self.b)
  self.b['evidence']=[self.claim];self.b['confirmed']=False
  with self.assertRaises(Conflict):self.s.save_definition(self.p,self.b,True)
  self.assertEqual(self.s.workspace(self.p)['draft']['version'],0)
