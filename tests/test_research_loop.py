import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from construct_lab.research_loop import ResearchLoopStore,validate_output
from construct_lab.loop_demo import demo_output
from construct_lab.store import Conflict
class LoopTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=ResearchLoopStore(Path(self.tmp.name)/'db');self.p=self.s.create_project('New construct');self.q=self.s.create_project('Other');self.ids=[self.source()]
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def source(self):return self.s.add_loop_evidence(self.p,dict(title='Test source',citation='Synthetic fixture',url='https://example.org/source',locator='Entry 1',text='Synthetic source for testing.',limitations='Not research evidence',actor='Tester',kind='linguistic',confirmed=True))['id']
 def body(self,stage='generate',parent=None):return dict(stage=stage,parent=parent,mode='demonstration',source_ids=self.ids[:],focus='A new construct',actor='Tester',consent=True)
 def runstage(self,stage='generate',parent=None):
  b=self.body(stage,parent);b['input_digest']=self.s.preview_loop(self.p,b)['input_digest'];return self.s.execute_loop(self.p,b)
 def accept(self,r):return self.s.review_loop(self.p,r['id'],dict(actor='Tester',reason='Checked fixture references',decision='accepted',confirmed=True,expected_version=0))
 def test_four_stage_lineage_and_export(self):
  a=self.accept(self.runstage());b=self.accept(self.runstage('challenge',a['id']));c=self.accept(self.runstage('plan',b['id']))
  with self.assertRaises(ValueError):self.runstage('revise',c['id'])
  self.ids.append(self.source());d=self.accept(self.runstage('revise',c['id']));self.assertEqual(len(d['record']['inputs']['ancestry']),3)
  revision=d['record']['accepted_output']['items'][0];self.assertTrue(revision['content']['before_id'].startswith(a['id']));self.assertIn(self.ids[-1],revision['refs']);self.assertEqual(len(self.s.export(self.p)['research_loop']['runs']),4);self.assertEqual(self.s.research_loop(self.q)['runs'],[])
 def test_review_gate_and_isolation(self):
  r=self.runstage()
  with self.assertRaises(ValueError):self.runstage('challenge',r['id'])
  with self.assertRaises(KeyError):self.s.loop_run(self.q,r['id'])
  self.accept(r)
  with self.assertRaises(Conflict):self.accept(r)
 def test_consent_digest_cache(self):
  b=self.body();b['input_digest']='bad'
  with self.assertRaises(Conflict):self.s.execute_loop(self.p,b)
  b['input_digest']=self.s.preview_loop(self.p,b)['input_digest'];b['consent']=False
  with self.assertRaises(ValueError):self.s.execute_loop(self.p,b)
  b['consent']=True;a=self.s.execute_loop(self.p,b);again=self.s.execute_loop(self.p,b);self.assertEqual(a['id'],again['id']);self.assertTrue(again['cached'])
 def test_invalid_references_and_shapes(self):
  i=self.s.loop_inputs(self.p,self.body());o=demo_output('generate',i);o['items'][1]['refs']=['invented']
  with self.assertRaises(ValueError):validate_output('generate',o,i)
  o=demo_output('generate',i);o['items'][0]['content']['extra']='bad'
  with self.assertRaises(ValueError):validate_output('generate',o,i)
 def test_edited_review_preserves_original(self):
  r=self.runstage();edited=copy.deepcopy(r['record']['output']);edited['items'][1]['content']['definition']='Reviewer amended definition'
  a=self.s.review_loop(self.p,r['id'],dict(actor='Human',reason='Clarified definition',decision='accepted',confirmed=True,expected_version=0,output=edited));self.assertNotEqual(a['record']['output'],a['record']['accepted_output'])
 def test_provider_failure_is_recorded(self):
  b=self.body();b['mode']='live';b['connection_id']='test';b['input_digest']=self.s.preview_loop(self.p,b)['input_digest'];config=dict(provider='local',endpoint='http://127.0.0.1:1/v1',model='fixture',connection_id='test',key='')
  with patch('construct_lab.research_loop.model_complete',side_effect=ValueError('Provider unavailable')):
   with self.assertRaises(ValueError):self.s.execute_loop(self.p,b,config)
  self.assertEqual(self.s.research_loop(self.p)['runs'][0]['status'],'failed')
 def test_stale_source_blocks_continuation(self):
  r=self.accept(self.runstage())
  import json
  row=self.s.db.execute('SELECT record FROM loop_evidence WHERE id=?',(self.ids[0],)).fetchone();data=json.loads(row[0]);data['text']='Corrected source'
  with self.s.db:self.s.db.execute('UPDATE loop_evidence SET record=? WHERE id=?',(json.dumps(data),self.ids[0]))
  self.assertTrue(self.s.research_loop(self.p)['runs'][0]['stale'])
  with self.assertRaises(Conflict):self.runstage('challenge',r['id'])
 def test_provider_transport(self):
  import json,threading
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  from construct_lab.research_loop import model_complete
  inputs=self.s.loop_inputs(self.p,self.body());output=demo_output('generate',inputs);captured=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))));payload=json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(output)))],model='transport-fixture',usage=dict(total_tokens=100))).encode();self.send_response(200);self.end_headers();self.wfile.write(payload)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   result,metadata=model_complete(dict(provider='openai',endpoint='http://127.0.0.1:'+str(server.server_port),model='fixture',key=''),'generate',inputs);self.assertEqual(result,output);self.assertFalse(captured[0]['store']);self.assertTrue(captured[0]['response_format']['json_schema']['strict'])
  finally:server.shutdown();thread.join();server.server_close()
