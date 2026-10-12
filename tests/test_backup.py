import tempfile
import unittest
from pathlib import Path
from construct_lab.navigation import AppStore
from construct_lab.backup import create_backup,restore_backup,verify,acquire_lock,list_backups
from test_library import fixture
class BackupTests(unittest.TestCase):
 def test_restore_preserves_pdfs_and_history_and_safety_copy(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'app.sqlite';s=AppStore(path);p=s.create_project('Original');d=s.import_pdf(p,fixture(),'fixture.pdf')['id'];before=s.export(p);original=s.original(p,d);s.close()
   b=create_backup(path);source=path.parent/'backups'/b['filename']
   s=AppStore(path);s.create_project('Later work');s.close()
   result=restore_backup(path,source);self.assertIsNotNone(result['safety_backup'])
   s=AppStore(path);self.assertEqual(s.export(p),before);self.assertEqual(s.original(p,d),original);self.assertEqual(len(s.state()['projects']),1);s.close()
   self.assertEqual(verify(path.parent/'backups'/result['safety_backup']['filename'])['projects'],2)
   self.assertEqual(len(list_backups(path)),2)
 def test_running_app_and_corrupt_backup_block_restore(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'app.sqlite';s=AppStore(path);s.create_project('Keep');s.close();b=create_backup(path);source=path.parent/'backups'/b['filename']
   lock=acquire_lock(path)
   try:
    with self.assertRaises(ValueError):restore_backup(path,source)
   finally:lock.close()
   with source.open('ab') as f:f.write(b'altered')
   with self.assertRaises(ValueError):restore_backup(path,source)
   self.assertEqual(verify(path)['projects'],1)
