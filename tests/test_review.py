import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from construct_lab.review import ReviewStore
from construct_lab.store import Conflict
from test_library import fixture


class PassageReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite'
        self.s = ReviewStore(self.path)
        self.p = self.s.create_project('Synthetic test project')
        self.d = self.s.import_pdf(self.p, fixture(), 'test.pdf')['id']

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def proposal(self, **extra):
        page = self.s.paper(self.p,self.d)['pages'][0]
        args = dict(project=self.p, document=self.d, page=1, revision=page['text_revision'], digest=page['text_hash'],
                    start=0, end=27, quote=page['text'][:27], category='definition', interpretation='Synthetic interpretation', actor='Test researcher')
        args.update(extra)
        return self.s.propose_passage(**args)

    def review(self, pid, **extra):
        args = dict(project=self.p, passage=pid, version=1, decision='verified', category='definition',
                    interpretation='Reviewed synthetic interpretation', reviewer='Test reviewer', rationale='Compared against original', original_checked=True)
        args.update(extra)
        return self.s.review_passage(**args)

    def test_ocr_preserves_native_text_original_and_previous_versions(self):
        original = self.s.original(self.p,self.d)
        native = self.s.paper(self.p,self.d)['pages'][0]['text']
        with patch('construct_lab.review.recognize', return_value={'text':'First synthetic OCR', 'engine':'test','blocks':[]}):
            self.s.ocr_page(self.p,self.d,1,0,'Tester')
        with patch('construct_lab.review.recognize', return_value={'text':'Second synthetic OCR', 'engine':'test','blocks':[]}):
            self.s.ocr_page(self.p,self.d,1,1,'Tester')
        self.assertEqual(self.s.original(self.p,self.d), original)
        self.assertEqual(self.s.db.execute('SELECT text FROM document_pages WHERE document=? AND number=1',(self.d,)).fetchone()[0],native)
        self.assertEqual(len(self.s.export(self.p)['ocr_history']),2)
        self.s.close();self.s=ReviewStore(self.path)
        self.assertEqual(self.s.paper(self.p,self.d)['pages'][0]['text'],'Second synthetic OCR')

    def test_failed_and_stale_ocr_leave_no_partial_write(self):
        before = self.s.export(self.p)
        with patch('construct_lab.review.recognize', side_effect=ValueError('Failed')):
            with self.assertRaises(ValueError): self.s.ocr_page(self.p,self.d,1,0,'Tester')
        self.assertEqual(before,self.s.export(self.p))
        with self.assertRaises(Conflict): self.s.ocr_page(self.p,self.d,1,99,'Tester')

    def test_quote_and_source_version_are_checked(self):
        for changes in ({'quote':'Invented quotation'},{'start':-1},{'digest':'stale'},{'revision':99}):
            with self.assertRaises(ValueError): self.proposal(**changes)
        self.assertEqual(self.s.passages(self.p),[])

    def test_new_ocr_does_not_change_existing_passage(self):
        pid=self.proposal()
        old=self.s.passages(self.p)[0]
        with patch('construct_lab.review.recognize', return_value={'text':'New OCR text','engine':'test','blocks':[]}):
            self.s.ocr_page(self.p,self.d,1,0,'Tester')
        new=self.s.passages(self.p)[0]
        self.assertEqual(new['quote'],old['quote'])
        self.assertEqual(new['source_text'],old['source_text'])
        self.assertTrue(new['newer_page_text'])

    def test_acceptance_requires_original_check_and_creates_verified_claim(self):
        pid=self.proposal()
        with self.assertRaises(ValueError): self.review(pid,original_checked=False)
        self.assertEqual(self.s.export(self.p)['claims'],[])
        self.review(pid,corrected_quote='Human-checked corrected quotation')
        record=self.s.passages(self.p)[0]
        self.assertNotEqual(record['quote'],record['reviewed_quote'])
        claim=self.s.export(self.p)['claims'][0]
        self.assertEqual(claim['status'],'verified')
        self.assertEqual(claim['quote'],'Human-checked corrected quotation')
        self.s.approve_definition(self.p,0,'Synthetic definition',[claim['id']],'Reviewer','Synthetic test')
        with self.assertRaises(Conflict): self.review(pid,version=2)

    def test_unresolved_can_be_revisited_but_stale_review_cannot_overwrite(self):
        pid=self.proposal()
        self.review(pid,decision='unresolved',original_checked=False)
        with self.assertRaises(Conflict): self.review(pid)
        self.review(pid,version=2,decision='rejected',original_checked=False)
        self.assertEqual(self.s.export(self.p)['claims'],[])
        self.assertEqual(self.s.passages(self.p)[0]['status'],'rejected')

    def test_other_project_cannot_review_or_select_passage(self):
        pid=self.proposal();other=self.s.create_project('Other')
        with self.assertRaises(KeyError): self.review(pid,project=other)
        with self.assertRaises(KeyError): self.proposal(project=other)
        self.assertEqual(self.s.passages(other),[])


if __name__=='__main__': unittest.main()
