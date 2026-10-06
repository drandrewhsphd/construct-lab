import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from construct_lab.extraction import Connection, ExtractionStore, complete
from test_library import fixture

class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=ExtractionStore(Path(self.tmp.name)/'test.sqlite')
        self.p=self.s.create_project('Synthetic curiosity');self.d=self.s.import_pdf(self.p,fixture(),'test.pdf')['id']
        self.page=self.s.paper(self.p,self.d)['pages'][0]
        self.body=dict(actor='Researcher',focus='Curiosity',page=1,revision=0,digest=self.page['text_hash'],consent=True,connection_id='test-connection')
        self.config=dict(provider='openai',endpoint='https://api.openai.com/v1',model='test-model',key='secret-test-key',connection_id='test-connection')
        self.item=dict(quote=self.page['text'][:40],category='definition',interpretation='Synthetic interpretation only')
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def extract(self, items=None):
        with patch('construct_lab.extraction.complete',return_value=({'passages':items if items is not None else [self.item]}, {'model':'test-model','usage':{}})) as call:
            result=self.s.extract(self.p,self.d,self.body,self.config)
        return result,call
    def test_unapproved_traceable_and_no_secrets(self):
        result,_=self.extract();p=self.s.passages(self.p)[0]
        self.assertEqual(p['status'],'proposed');self.assertEqual(p['ai']['run'],result['id'])
        self.assertEqual(self.s.export(self.p)['claims'],[])
        self.assertNotIn(self.config['key'],json.dumps(self.s.export(self.p)))
        self.assertEqual(result['record']['source_text'],self.page['text'])
    def test_repeat_cached_and_duplicates_skipped(self):
        first,_=self.extract([self.item,self.item]);second,call=self.extract()
        self.assertTrue(second['cached']);call.assert_not_called()
        self.assertEqual(len(self.s.passages(self.p)),1);self.assertEqual(len(first['record']['skipped']),1)
        self.body['focus']='Another focus';result,_=self.extract()
        self.assertEqual(result['record']['passages'],[])
    def test_invalid_proposals_skipped(self):
        result,_=self.extract([dict(self.item,quote='This quotation was invented'),dict(self.item,category='verified'),42])
        self.assertEqual(self.s.passages(self.p),[]);self.assertEqual(len(result['record']['skipped']),3)
    def test_failure_and_retry(self):
        with patch('construct_lab.extraction.complete',side_effect=ValueError('Provider unavailable')):
            with self.assertRaises(ValueError):self.s.extract(self.p,self.d,self.body,self.config)
        self.assertEqual(self.s.runs(self.p)[0]['status'],'failed');self.assertEqual(self.s.passages(self.p),[])
        self.extract();self.assertEqual(len(self.s.passages(self.p)),1)
    def test_stale_during_call_atomic(self):
        def change(*args):
            with patch('construct_lab.review.recognize',return_value={'text':'Changed OCR','engine':'synthetic'}):self.s.ocr_page(self.p,self.d,1,0,'Test')
            return {'passages':[self.item]},{}
        with patch('construct_lab.extraction.complete',side_effect=change):
            with self.assertRaises(ValueError):self.s.extract(self.p,self.d,self.body,self.config)
        self.assertEqual(self.s.passages(self.p),[]);self.assertEqual(self.s.runs(self.p)[0]['status'],'failed')
    def test_consent_staleness_isolation_before_network(self):
        with patch('construct_lab.extraction.complete') as call:
            for body in (dict(self.body,consent=False),dict(self.body,digest='stale'),dict(self.body,page=True),dict(self.body,connection_id='stale')):
                with self.assertRaises(ValueError):self.s.extract(self.p,self.d,body,self.config)
            other=self.s.create_project('Other')
            with self.assertRaises(KeyError):self.s.extract(other,self.d,self.body,self.config)
            call.assert_not_called()
    def test_empty_result(self):
        result,_=self.extract([]);self.assertEqual(result['status'],'completed');self.assertEqual(self.s.passages(self.p),[])
    def test_connection(self):
        c=Connection();public=c.configure(self.config)
        self.assertNotIn('key',public);self.assertEqual(c.snapshot()['key'],'secret-test-key')
        c.clear();self.assertFalse(c.public()['configured'])
        for bad in ('http://example.com/v1','https://user:pass@example.com/v1','https://example.com/v1?key=secret'):
            with self.assertRaises(ValueError):c.configure(dict(self.config,provider='compatible',endpoint=bad))
        with self.assertRaises(ValueError):c.configure(dict(self.config,provider='local',endpoint='http://example.com/v1'))
    def test_transport(self):
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'passages':[self.item]})}}],'model':'test-model'}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch('construct_lab.extraction.build_opener',return_value=opener):result,_=complete(self.config,'Focus',self.page['text'])
        request=opener.open.call_args.args[0];payload=json.loads(request.data)
        self.assertFalse(payload['store']);self.assertEqual(payload['response_format']['type'],'json_object')
        self.assertEqual(result['passages'][0],self.item)
        response.read.return_value=b'{"choices":[{"finish_reason":"length"}]}'
        with patch('construct_lab.extraction.build_opener',return_value=opener):
            with self.assertRaises(ValueError):complete(self.config,'Focus','Source')

if __name__=='__main__':unittest.main()
