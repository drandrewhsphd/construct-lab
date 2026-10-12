import tempfile,unittest
from pathlib import Path
from construct_lab.etymology import EtymologyStore,SCHEMA
from construct_lab.store import Conflict
class EtymologyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=EtymologyStore(Path(self.tmp.name)/'db');self.p=self.s.create_project('Pilot');self.q=self.s.create_project('Existing')
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def body(self,kind,links=()):
  c={f:'Example' for f in SCHEMA[kind]}
  if kind=='source':c['url']='https://example.org'
  if kind=='case':c['purpose']='development'
  if kind=='assessment':c['classification']='uncertain'
  return dict(kind=kind,content=c,links=list(links),actor='Tester',reason='Test',expected_version=0)
 def add(self,kind,links=()):return self.s.save_etymology(self.p,self.body(kind,links))['records'][-1]
 def link(self,r):return dict(id=r['id'],version=r['version'])
 def test_version_history_and_isolation(self):
  before=self.s.export(self.q);a=self.add('source');i=self.add('interpretation',[self.link(a)])
  b=self.body('source');b.update(id=a['id'],expected_version=1);b['content']['summary']='Revised';self.s.save_etymology(self.p,b)
  records=self.s.etymology(self.p)['records'];self.assertTrue(records[1]['stale']);self.assertEqual(len(records[0]['history']),2);self.assertEqual(records[1]['links'][0]['version'],1)
  with self.assertRaises(Conflict):self.s.save_etymology(self.p,b)
  self.assertEqual(before,self.s.export(self.q));self.assertEqual(len(self.s.export(self.p)['etymology_workspace']),2)
 def test_invalid_support_and_url(self):
  with self.assertRaises(ValueError):self.add('definition')
  a=self.add('source')
  with self.assertRaises(ValueError):self.add('definition',[self.link(a)])
  with self.assertRaises(ValueError):self.s.save_etymology(self.q,self.body('interpretation',[self.link(a)]))
  b=self.body('source');b['content']['url']='javascript:alert(1)'
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
 def test_assessment_requires_one_definition_and_case(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);c=self.add('case')
  with self.assertRaises(ValueError):self.add('assessment',[self.link(d)])
  result=self.add('assessment',[self.link(d),self.link(c)]);self.assertEqual(result['content']['classification'],'uncertain')
 def test_historical_comparison_preserves_versions(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)])
  hb=self.body('historical');hb['content']['url']='https://example.org/history';h=self.s.save_etymology(self.p,hb)['records'][-1]
  with self.assertRaises(ValueError):self.add('comparison',[self.link(d),self.link(h)])
  c=self.add('comparison',[self.link(d),self.link(h),self.link(a)])
  hb.update(id=h['id'],expected_version=1);hb['content']['definition']='Changed definition';self.s.save_etymology(self.p,hb)
  saved=next(x for x in self.s.export(self.p)['etymology_workspace'] if x['id']==c['id']);self.assertTrue(saved['stale']);self.assertIn(self.link(h),saved['links'])
  with self.assertRaises(Conflict):self.add('comparison',[self.link(d),self.link(h),self.link(a)])
  hb['content']['url']='javascript:alert(1)'
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,hb)
 def test_boundary_matrix_handles_missing_conflicting_and_stale(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);c=self.add('case')
  def cell():return self.s.etymology(self.p)['boundary']['rows'][0]['cells'][0]
  self.assertEqual(cell()['verdict'],'not assessed')
  body=self.body('assessment',[self.link(d),self.link(c)]);body['content']['classification']='included';self.s.save_etymology(self.p,body)
  self.assertEqual(cell()['verdict'],'included')
  body['content']['classification']='excluded';self.s.save_etymology(self.p,body)
  self.assertEqual(cell()['verdict'],'mixed judgments');self.assertEqual(len(cell()['assessments']),2)
  change=self.body('case');change.update(id=c['id'],expected_version=1);self.s.save_etymology(self.p,change)
  self.assertEqual(cell()['verdict'],'not assessed');self.assertEqual(cell()['stale'],2)
  self.assertEqual(self.s.etymology(self.p)['boundary']['rows'][0]['status'],'Unresolved or incomplete')
 def test_legacy_assessment_remains_readable(self):
  import json
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);c=self.add('case');r=self.add('assessment',[self.link(d),self.link(c)])
  old=dict(r['content']);del old['evidence_needed']
  with self.s.db:self.s.db.execute('UPDATE etymology_records SET content=? WHERE id=?',(json.dumps(old),r['id']))
  self.assertIn('Not recorded',self.s.etymology(self.p)['records'][-1]['content']['evidence_needed'])
 def task_fixture(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);c=self.add('case');r=self.add('assessment',[self.link(d),self.link(c)])
  b=self.body('task',[self.link(r),self.link(d),self.link(c)]);b['content'].update(status='open',priority='normal',decision='pending');return b,c,r
 def test_task_resolution_requires_finding_and_decision(self):
  b,c,r=self.task_fixture();t=self.s.save_etymology(self.p,b)['records'][-1];b.update(id=t['id'],expected_version=1);b['content']['status']='resolved'
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
  b['content']['decision']='inconclusive'
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
  f=self.body('finding');f['content'].update(url='https://example.org/paper',evidence_type='empirical study');finding=self.s.save_etymology(self.p,f)['records'][-1]
  b['links'].append(self.link(finding));self.s.save_etymology(self.p,b)
  saved=next(x for x in self.s.export(self.p)['etymology_workspace'] if x['id']==t['id']);self.assertEqual(saved['version'],2);self.assertEqual(saved['content']['decision'],'inconclusive')
  b['expected_version']=2;b['content'].update(status='investigating',decision='pending');self.s.save_etymology(self.p,b)
  with self.assertRaises(Conflict):self.s.save_etymology(self.p,b)
 def test_task_rejects_unrelated_and_outdated_case(self):
  b,c,r=self.task_fixture();other=self.add('case');bad=dict(b,links=[self.link(other) if x['id']==c['id'] else x for x in b['links']])
  with self.assertRaises(Conflict):self.s.save_etymology(self.p,bad)
  with self.assertRaises(ValueError):self.s.save_etymology(self.q,b)
  change=self.body('case');change.update(id=c['id'],expected_version=1);self.s.save_etymology(self.p,change)
  b['links']=[dict(x,version=2) if x['id']==c['id'] else x for x in b['links']]
  with self.assertRaises(Conflict):self.s.save_etymology(self.p,b)
 def test_candidate_can_link_findings_without_replacing_interpretation(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)])
  f=self.body('finding');f['content'].update(url='https://example.org/study',evidence_type='empirical study');r=self.s.save_etymology(self.p,f)['records'][-1]
  with self.assertRaises(ValueError):self.add('definition',[self.link(r)])
  d=self.add('definition',[self.link(i),self.link(r)]);self.assertIn(self.link(r),d['links'])
 def test_revision_snapshots_and_reassessment(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);d2=self.add('definition',[self.link(i)]);c=self.add('case');old=self.add('assessment',[self.link(d),self.link(c)])
  f=self.body('finding');f['content'].update(url='https://example.org/study',evidence_type='empirical study');f=self.s.save_etymology(self.p,f)['records'][-1]
  b=self.body('revision',[self.link(d),self.link(d2),self.link(f)]);b['content'].update(before_id=d['id'],after_id=d2['id']);revision=self.s.save_etymology(self.p,b)['records'][-1]
  v=self.s.etymology(self.p)['revisions'][0];self.assertEqual(v['impact'][0]['status'],'Needs reassessment for target')
  new=self.add('assessment',[self.link(d2),self.link(c)]);v=self.s.etymology(self.p)['revisions'][0];self.assertEqual(v['impact'][0]['followups'],[new['id']])
  change=self.body('definition',[self.link(i)]);change.update(id=d2['id'],expected_version=1);change['content']['definition']='Updated';self.s.save_etymology(self.p,change)
  v=self.s.etymology(self.p)['revisions'][0];self.assertEqual(v['after']['version'],1);self.assertEqual(v['impact'][0]['status'],'Review revision first');self.assertEqual(v['impact'][0]['followups'],[])
  b['content']['after_id']=d['id'];b['links']=[dict(x,version=2) if x['id']==d2['id'] else x for x in b['links']]
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
 def test_protocol_requires_candidate_and_preserves_snapshot_links(self):
  with self.assertRaises(ValueError):self.add('protocol')
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);p=self.add('protocol',[self.link(d)])
  change=self.body('definition',[self.link(i)]);change.update(id=d['id'],expected_version=1);self.s.save_etymology(self.p,change)
  saved=next(r for r in self.s.export(self.p)['etymology_workspace'] if r['id']==p['id']);self.assertTrue(saved['stale']);self.assertEqual(saved['links'],[self.link(d)])
 def run_fixture(self):
  a=self.add('source');i=self.add('interpretation',[self.link(a)]);d=self.add('definition',[self.link(i)]);p=self.add('protocol',[self.link(d)]);b=self.body('run',[self.link(p)]);b['content'].update(run_mode='demonstration',run_phase='active');r=self.s.save_etymology(self.p,b)['records'][-1];return p,b,r
 def test_run_freezes_protocol_and_requires_results(self):
  p,b,r=self.run_fixture();change=self.body('protocol',p['links']);change.update(id=p['id'],expected_version=1);self.s.save_etymology(self.p,change)
  b.update(id=r['id'],expected_version=1);self.s.save_etymology(self.p,b)
  b['expected_version']=2;b['content']['run_mode']='empirical'
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
  b['content'].update(run_mode='demonstration',run_phase='completed')
  with self.assertRaises(ValueError):self.s.save_etymology(self.p,b)
  r2=self.s.etymology(self.p)['records'][-1];self.assertEqual(r2['links'],r['links'])
 def test_observation_rejects_cross_run_reviewer_and_complete_lifecycle(self):
  p,b,r=self.run_fixture();p2,b2,r2=self.run_fixture();reviewer=self.add('reviewer',[self.link(r)])
  with self.assertRaises(ValueError):self.add('observation',[self.link(r2),self.link(reviewer)])
  obs=self.add('observation',[self.link(r),self.link(reviewer)]);result=self.add('result',[self.link(r),self.link(obs)])
  b.update(id=r['id'],expected_version=1);b['content']['run_phase']='completed';self.s.save_etymology(self.p,b)
  with self.assertRaises(ValueError):self.add('observation',[self.link(r),self.link(reviewer)])
  b['expected_version']=2;b['content']['run_phase']='active';self.s.save_etymology(self.p,b)
  self.add('observation',[self.link(r),self.link(reviewer)])
 def test_run_report_frozen_protocol_escape_and_isolation(self):
  from construct_lab.run_report import render_run_report
  p,b,r=self.run_fixture();before=self.s.export(self.p)
  report=render_run_report(self.s,self.p,r['id']);self.assertIn('SYNTHETIC DEMONSTRATION',report);self.assertIn('No observations recorded',report);self.assertEqual(before,self.s.export(self.p))
  change=self.body('protocol',p['links']);change.update(id=p['id'],expected_version=1);change['content']['objective']='NEW PROTOCOL TEXT';self.s.save_etymology(self.p,change)
  b.update(id=r['id'],expected_version=1);b['content']['scope']='<script>bad()</script>';self.s.save_etymology(self.p,b)
  report=render_run_report(self.s,self.p,r['id']);self.assertNotIn('NEW PROTOCOL TEXT',report);self.assertIn('&lt;script&gt;bad()',report);self.assertNotIn('<script>bad()',report)
  with self.assertRaises(KeyError):render_run_report(self.s,self.q,r['id'])
