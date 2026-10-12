import tempfile
import unittest
from pathlib import Path
from construct_lab.rounds import RoundStore
from construct_lab.store import Conflict
from test_library import fixture

class RoundTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=RoundStore(Path(self.tmp.name)/'db');self.p=self.s.create_project('Test')
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def body(self):
  r=self.s.rounds(self.p);return dict(title='Test round',actor='Tester',note='Fixture checkpoint',current_digest=r['current_digest'],expected_sequence=r['expected_sequence'])
 def test_baseline_changes_immutable_export(self):
  self.s.save_round(self.p,self.body());original=self.s.export(self.p)['evidence_rounds'][0]
  with self.assertRaises(ValueError):self.s.save_round(self.p,self.body())
  self.s.import_pdf(self.p,fixture(),'test.pdf')
  r=self.s.save_round(self.p,self.body());self.assertEqual(len(r['rounds'][1]['delta']['papers']['added']),1)
  self.assertEqual(original,self.s.export(self.p)['evidence_rounds'][0]);self.assertEqual(len(self.s.dashboard(self.p)['evidence_rounds']['latest']['delta']['papers']['added']),1)
 def test_stale_preview_and_cross_project(self):
  b=self.body();self.s.import_pdf(self.p,fixture(),'test.pdf')
  with self.assertRaises(Conflict):self.s.save_round(self.p,b)
  b=self.body();self.s.save_round(self.p,b)
  with self.assertRaises(Conflict):self.s.save_round(self.p,b)
  other=self.s.create_project('Other');self.assertEqual(self.s.rounds(other)['rounds'],[])
 def test_delta_revisions_and_removals(self):
  a=dict(definition_version=0,definition=None,papers={},passages={'x':{'version':1}},coding={},questions={})
  b=dict(a,passages={'x':{'version':2}});d=self.s.delta(a,b);self.assertEqual(len(d['passages']['changed']),1)
  b['passages']={};self.assertEqual(len(self.s.delta(a,b)['passages']['removed']),1)
