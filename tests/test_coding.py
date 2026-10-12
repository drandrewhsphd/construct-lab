import tempfile
import unittest
from pathlib import Path
from construct_lab.coding import CodingStore
from construct_lab.store import Conflict
from test_library import fixture

class CodingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=CodingStore(Path(self.tmp.name)/'db')
  self.p=self.s.create_project('Synthetic project')
  d=self.s.import_pdf(self.p,fixture(),'test.pdf')['id'];page=self.s.paper(self.p,d)['pages'][0]
  self.pid=self.s.propose_passage(project=self.p,document=d,page=1,revision=page['text_revision'],digest=page['text_hash'],start=0,end=27,quote=page['text'][:27],category='definition',interpretation='Synthetic interpretation',actor='Tester')
  self.s.review_passage(project=self.p,passage=self.pid,version=1,decision='verified',category='definition',interpretation='Synthetic interpretation',reviewer='Tester',rationale='Checked original',original_checked=True)
  self.b=dict(passage=self.pid,passage_version=self.s.passages(self.p)[0]['version'],expected_version=0,definition_version=0,actor='Tester',reason='Initial coding',content=dict(level='measure',learning='supported',reassurance='not established',learning_evidence='Synthetic item wording',reassurance_evidence='',confidence='moderate',rationale='Measure content does not establish an episode motive',status='draft'))
 def tearDown(self):
  self.s.close();self.tmp.cleanup()
 def test_history_and_source_isolation(self):
  before=self.s.export(self.p);r=self.s.save_coding(self.p,self.b)['records'][0]
  self.assertEqual(r['content']['code'],'Learning supported')
  self.b['expected_version']=1;self.b['content']['learning']='not established';self.b['reason']='Reconsidered evidence'
  r=self.s.save_coding(self.p,self.b)['records'][0]
  self.assertEqual(r['version'],2);self.assertEqual(len(r['history']),2)
  self.assertEqual(r['history'][1]['content']['code'],'Learning supported')
  after=self.s.export(self.p)
  self.assertEqual({k:v for k,v in before.items() if k!='coding_workspace'},{k:v for k,v in after.items() if k!='coding_workspace'})
 def test_stale_updates_and_foreign_sources_rejected(self):
  self.s.save_coding(self.p,self.b)
  with self.assertRaises(Conflict):self.s.save_coding(self.p,self.b)
  for field in ('passage_version','definition_version'):
   b=dict(self.b,expected_version=1);b[field]=99
   with self.assertRaises(Conflict):self.s.save_coding(self.p,b)
  other=self.s.create_project('Other')
  with self.assertRaises(ValueError):self.s.save_coding(other,self.b)
  self.assertEqual(len(self.s.coding(self.p)['records'][0]['history']),1)
 def test_motive_evidence_required(self):
  self.b['content']['learning_evidence']=''
  with self.assertRaises(ValueError):self.s.save_coding(self.p,self.b)
  self.assertEqual(self.s.coding(self.p)['records'],[])
