import tempfile
import unittest
from pathlib import Path
from construct_lab.navigation import AppStore
class NavigationTests(unittest.TestCase):
 def test_project_specific_actions_and_isolation(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=AppStore(Path(tmp)/'db');p=s.create_project('Research');demo=s.create_project('Demo')
   with s.db:s.db.execute('INSERT INTO demonstrations VALUES(?,?)',(demo,'{}'))
   before=s.export(p);items={x['id']:x for x in s.navigation()['projects']}
   self.assertEqual(items[p]['next']['path'],'library');self.assertFalse(items[p]['demonstration'])
   self.assertEqual(items[demo]['next']['path'],'demonstration');self.assertTrue(items[demo]['demonstration'])
   self.assertEqual(s.export(p),before);s.close()
