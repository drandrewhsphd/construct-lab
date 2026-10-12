import unittest,tempfile
from pathlib import Path
from construct_lab.learning import LearningStore
from construct_lab.definitions import FIELDS
from construct_lab.store import Conflict
class LearningTests(unittest.TestCase):
 def test_planning_resolution_and_stale_writes(self):
  with tempfile.TemporaryDirectory() as t:
   s=LearningStore(Path(t)/'db');p=s.create_project('Test');src=s.add_source(p,'Test','1','Synthetic');cid=s.propose_claim(src,'Synthetic','Test');s.review_claim(cid,'Test','Test',True)
   b=dict(expected_version=0,definition_version=0,question='Question',rationale='Why',evidence_plan='Search',priority='high',status='open',actor='Test',reason='Test')
   with self.assertRaises(ValueError):s.save_question(p,b)
   s.save_definition(p,dict(expected_version=0,expected_approved_version=0,content={k:'Test' for k in FIELDS},evidence=[cid],actor='Test',rationale='Test',confirmed=True),True)
   b['definition_version']=1;w=s.save_question(p,b);q=w['questions'][0];b.update(id=q['id'],expected_version=1,status='resolved')
   with self.assertRaises(ValueError):s.save_question(p,b)
   b.update(conclusion='Answer',evidence=[cid]);s.save_question(p,b)
   with self.assertRaises(Conflict):s.save_question(p,b)
   self.assertEqual(s.workspace(p)['project']['version'],1);self.assertEqual(s.export(p)['learning_questions'][0]['status'],'resolved');s.close()
