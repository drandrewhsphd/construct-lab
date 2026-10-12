import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from construct_lab.etymology import EtymologyStore, SCHEMA
from construct_lab.walkthrough import render_walkthrough


class WalkthroughTests(unittest.TestCase):
    def test_live_evidence_is_escaped_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EtymologyStore(Path(tmp) / 'db')
            project = store.create_project('Pilot')
            content = {k: 'Example' for k in SCHEMA['source']}
            content.update(title='<script>alert(1)</script>', url='https://example.org', summary='Original recorded evidence')
            store.save_etymology(project, dict(kind='source', content=content, links=[], actor='Tester', reason='Fixture', expected_version=0))
            before = store.export(project)
            with patch('construct_lab.walkthrough.PILOT', project):
                page = render_walkthrough(store, project)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)
            self.assertNotIn('<script>alert(1)</script>', page)
            self.assertIn('Original recorded evidence', page)
            self.assertEqual(page.count('Organization Science fit'), 10)
            self.assertIn('Platform without linguistic expansion', page)
            self.assertEqual(store.export(project), before)
            other = store.create_project('Other project')
            page = render_walkthrough(store, other)
            self.assertNotIn('Original recorded evidence', page)
            with self.assertRaises(KeyError):
                render_walkthrough(store, 'missing-project')
            store.close()
