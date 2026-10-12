import tempfile
import unittest
from pathlib import Path
from construct_lab.demonstration import DemonstrationStore,build_demo
from test_library import fixture

class DemonstrationTests(unittest.TestCase):
 def test_full_workflow_isolated_repeatable_and_not_saturated(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=DemonstrationStore(Path(tmp)/'db');original=s.create_project('Real project');before=s.export(original)
   p=build_demo(s,[fixture()+f'\n% scenario {i}'.encode() for i in range(3)])
   d=s.demonstration(p)
   self.assertEqual(d['dashboard']['counts']['papers'],3)
   self.assertEqual(d['dashboard']['counts']['accepted'],3)
   self.assertEqual(d['dashboard']['counts']['coded'],3)
   self.assertEqual(len(d['rounds']),3)
   self.assertEqual(d['rounds'][1]['delta']['passages']['added'][0]['after']['status'],'verified')
   self.assertEqual(sum(r['demonstration'] for r in d['novelty']),2)
   self.assertEqual(sum(r['research_reviewed'] for r in d['novelty']),0)
   self.assertEqual(d['saturation']['recommendation'],'Continue evidence development')
   self.assertEqual(s.export(original),before)
   self.assertEqual(build_demo(s,[]),p)
   self.assertEqual(len(s.rounds(p)['rounds']),3)
   with self.assertRaises(KeyError):s.demonstration(original)
   s.close()
