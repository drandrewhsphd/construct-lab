from test_coding import CodingTests
from construct_lab.dashboard import DashboardStore

class DashboardTests(CodingTests):
 def setUp(self):
  super().setUp();path=self.s.db.execute('PRAGMA database_list').fetchone()[2];self.s.close();self.s=DashboardStore(path)
 def test_counts_demo_and_stale(self):
  before=self.s.export(self.p)
  d=self.s.dashboard(self.p)
  self.assertEqual(d['counts']['uncoded'],1)
  self.assertEqual(d['saturation']['status'],'Not established')
  self.assertEqual(before,self.s.export(self.p))
  self.b['actor']='AI workflow demonstration';self.b['content']['status']='reviewed';self.s.save_coding(self.p,self.b)
  d=self.s.dashboard(self.p)
  self.assertEqual(d['counts']['demonstration'],1);self.assertEqual(d['counts']['uncoded'],0)
  self.assertEqual(d['saturation']['status'],'Not established')
  with self.s.db:self.s.db.execute('UPDATE projects SET version=1 WHERE id=?',(self.p,))
  self.assertEqual(self.s.dashboard(self.p)['counts']['stale'],1)
  other=self.s.create_project('Empty')
  self.assertEqual(self.s.dashboard(other)['counts']['coded'],0)
