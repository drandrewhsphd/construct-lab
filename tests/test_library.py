import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from construct_lab.library import LibraryStore, FIELDS
from construct_lab.server import make_server
from construct_lab.store import Conflict


def fixture(encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 30 700 Td (Synthetic research evidence used only to test page extraction and traceable storage. This sentence is not a research finding.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({'/Title': 'Synthetic paper', '/Author': 'Test Author'})
    if encrypted:
        writer.encrypt('secret')
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'library.sqlite'
        self.s = LibraryStore(self.path)
        self.p = self.s.create_project('Curiosity test')
        self.data = fixture()

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def test_original_pages_and_flags_persist_after_restart(self):
        imported = self.s.import_pdf(self.p, self.data, '../paper.pdf')
        self.s.close()
        self.s = LibraryStore(self.path)
        paper = self.s.paper(self.p, imported['id'])
        self.assertEqual(self.s.original(self.p, imported['id']), self.data)
        self.assertEqual(paper['filename'], 'paper.pdf')
        self.assertEqual(paper['metadata']['title'], 'Synthetic paper')
        self.assertEqual(paper['pages'][0]['status'], 'text_available')
        self.assertIn('Synthetic research evidence', paper['pages'][0]['text'])
        self.assertEqual(paper['pages'][1]['status'], 'check_original')
        self.assertEqual(paper['pages'][1]['number'], 2)
        self.assertEqual(paper['citation_status'], 'needs_review')
        self.assertEqual(self.s.export(self.p)['claims'], [])

    def test_duplicate_import_is_idempotent_and_project_scoped(self):
        first = self.s.import_pdf(self.p, self.data, 'a.pdf')
        before = self.s.export(self.p)
        second = self.s.import_pdf(self.p, self.data, 'renamed.pdf')
        self.assertEqual(first['id'], second['id'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(before, self.s.export(self.p))
        other = self.s.create_project('Independent project')
        self.assertFalse(self.s.import_pdf(other, self.data, 'same.pdf')['duplicate'])
        with self.assertRaises(KeyError):
            self.s.original(other, first['id'])

    def test_corrupt_or_encrypted_pdf_leaves_no_partial_import(self):
        for data in (b'<html>not PDF</html>', b'%PDF-1.7 damaged', fixture(True)):
            with self.assertRaises(ValueError):
                self.s.import_pdf(self.p, data, 'broken.pdf')
        self.assertEqual(self.s.papers(self.p), [])
        self.assertEqual(len(self.s.export(self.p)['events']), 1)

    def test_citation_review_is_versioned_and_not_evidence_approval(self):
        did = self.s.import_pdf(self.p, self.data, 'test.pdf')['id']
        metadata = dict.fromkeys(FIELDS, '')
        metadata.update(title='Checked title', authors='Test', year='2020', journal='Test journal', publication_version='Test manuscript', doi='10.test/demo')
        result = self.s.update_citation(self.p, did, 1, metadata, 'Reviewer', True)
        self.assertEqual(result['citation_status'], 'confirmed')
        self.assertEqual(result['version'], 2)
        before = self.s.export(self.p)
        with self.assertRaises(Conflict):
            self.s.update_citation(self.p, did, 1, metadata, 'Other', False)
        self.assertEqual(before, self.s.export(self.p))
        self.assertEqual(before['revisions'], [])
        self.assertEqual(before['events'][-1]['kind'], 'citation_updated')

    def test_library_http_upload_original_and_invalid_origin(self):
        server = make_server(self.path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        headers = {'Origin': base, 'Content-Type': 'application/pdf', 'X-Construct-Lab': 'local', 'X-Filename': 'test.pdf'}
        try:
            request = Request(base+f'/api/projects/{self.p}/papers', data=self.data, headers=headers)
            with urlopen(request) as r:
                result = json.load(r)
            with urlopen(base+f'/api/projects/{self.p}/papers/'+result['id']+'/pdf') as r:
                self.assertEqual(r.read(), self.data)
            with urlopen(base+f'/api/projects/{self.p}/papers/'+result['id']+'/pages/1') as r:
                self.assertTrue(r.read().startswith(b'\x89PNG'))
            with self.assertRaises(HTTPError) as missing:
                urlopen(base+f'/api/projects/{self.p}/papers/'+result['id']+'/pages/99')
            self.assertEqual(missing.exception.code, 404)
            headers['Origin'] = 'https://example.com'
            with self.assertRaises(HTTPError) as raised:
                urlopen(Request(base+f'/api/projects/{self.p}/papers', data=self.data, headers=headers))
            self.assertEqual(raised.exception.code, 403)
            with urlopen(base+'/library') as r:
                self.assertIn(b'Literature Library', r.read())
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
