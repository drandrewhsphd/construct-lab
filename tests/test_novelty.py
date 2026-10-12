import unittest
from test_coding import CodingTests as Fixtures
from construct_lab.novelty import NoveltyStore
from construct_lab.store import Conflict

class NoveltyTests(unittest.TestCase):
 def setUp(self):
  Fixtures.setUp(self);path=self.s.db.execute('PRAGMA database_list').fetchone()[2];self.s.close();self.s=NoveltyStore(path)
  self.checkpoint()
 def tearDown(self):Fixtures.tearDown(self)
 def checkpoint(self):
  r=self.s.rounds(self.p);self.s.save_round(self.p,dict(title='Fixture',actor='Tester',note='Test',expected_sequence=r['expected_sequence'],current_digest=r['current_digest']))
 def body(self):
  r=self.s.novelty(self.p)['rounds'][-1];return dict(round_id=r['id'],passage=self.pid,expected_version=0,actor='Tester',reason='Test judgment',content=dict(category='challenge',comparison='Prior interpretation',rationale='Conflicting evidence',implication='Needs further evidence',confidence='low',status='reviewed',mode='research'))
 def test_baseline_excluded_history_and_isolation(self):
  before=self.s.export(self.p);b=self.body();d=self.s.save_novelty(self.p,b)
  self.assertIsNone(d['summary'][0]['novel'])
  with self.assertRaises(Conflict):self.s.save_novelty(self.p,b)
  b['expected_version']=1;b['content']['category']='unresolved';d=self.s.save_novelty(self.p,b)
  self.assertEqual(len(d['records'][0]['history']),2)
  after=self.s.export(self.p);self.assertEqual({k:v for k,v in before.items() if k!='novelty_assessments'},{k:v for k,v in after.items() if k!='novelty_assessments'})
 def test_eligibility_demonstration_excluded(self):
  with self.s.db:self.s.db.execute('UPDATE passages SET version=version+1 WHERE id=?',(self.pid,))
  self.checkpoint();b=self.body();b['content']['mode']='demonstration';d=self.s.save_novelty(self.p,b)
  self.assertEqual(d['summary'][1]['novel'],0)
  b['expected_version']=1;b['content']['mode']='research';d=self.s.save_novelty(self.p,b);self.assertEqual(d['summary'][1]['novel'],1)
  other=self.s.create_project('Other')
  with self.assertRaises(ValueError):self.s.save_novelty(other,b)
  b['passage']='missing'
  with self.assertRaises(ValueError):self.s.save_novelty(self.p,b)
