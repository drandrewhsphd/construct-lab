import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from construct_lab.saturation import SaturationStore,GATES
from construct_lab.store import Conflict

class SaturationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=SaturationStore(Path(self.tmp.name)/'db');self.p=self.s.create_project('Fixture')
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def body(self):
  d=self.s.saturation(self.p);return dict(expected_version=d['version'],context=d['context'],rules=dict(rounds=1,min_passages=1,max_novelty_percent=5),checks={k:dict(status='met',rationale='Synthetic validation') for k in GATES},actor='Tester',reason='Synthetic thresholds')
 def test_missing_evidence_no_stop_and_history(self):
  self.assertEqual(self.s.saturation(self.p)['recommendation'],'Continue evidence development')
  b=self.body();self.s.save_saturation(self.p,b)
  with self.assertRaises(Conflict):self.s.save_saturation(self.p,b)
  self.assertEqual(len(self.s.saturation(self.p)['history']),1)
  with self.s.db:self.s.db.execute('UPDATE projects SET version=1 WHERE id=?',(self.p,))
  d=self.s.saturation(self.p);self.assertFalse(d['checks_current'])
  self.assertTrue(any(c['name']=='Coding validation' and c['status']=='unknown' for c in d['conditions']))
 def test_invalid_thresholds_and_checks(self):
  b=self.body();b['rules']['rounds']=True
  with self.assertRaises(ValueError):self.s.save_saturation(self.p,b)
  b=self.body();b['checks'][GATES[0]]['rationale']=''
  with self.assertRaises(ValueError):self.s.save_saturation(self.p,b)
 def test_qualified_window_and_blockers(self):
  self.s.save_saturation(self.p,self.body())
  n=dict(project=dict(version=2),summary=[dict(sequence=2,baseline=False,eligible=1,research_reviewed=1,unresolved=0,novel=0,decided=1)])
  preview={k:{a:[] for a in ('added','changed','removed')} for k in ('papers','passages','coding','questions')};preview['definition_changed']=False
  rounds=dict(rounds=[dict(delta=dict(definition_changed=False))],preview=preview)
  digest=self.s.context(self.p)
  with patch.object(self.s,'novelty',return_value=n),patch.object(self.s,'rounds',return_value=rounds),patch.object(self.s,'learning',return_value={'questions':[]}),patch.object(self.s,'context',return_value=digest):
   self.assertEqual(self.s.saturation(self.p)['recommendation'],'Consider a documented stopping decision')
   n['summary'][0]['research_reviewed']=0
   self.assertEqual(self.s.saturation(self.p)['recommendation'],'Continue evidence development')
   n['summary'][0]['research_reviewed']=1;n['summary'][0]['novel']=1
   self.assertEqual(self.s.saturation(self.p)['recommendation'],'Continue evidence development')
