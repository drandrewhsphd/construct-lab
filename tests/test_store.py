import unittest
from construct_lab.store import Store, Conflict


class ResearchRecordTests(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")
        self.p = self.s.create_project("Curiosity")
        self.source = self.s.add_source(self.p, "Synthetic test fixture", "paragraph 1",
                                       "A desire to understand. Behavior alone is insufficient.")
        self.claim = self.s.propose_claim(self.source, "A desire to understand.", "Test interpretation")

    def tearDown(self):
        self.s.close()

    def approve(self, **kwargs):
        args = dict(project=self.p, expected_version=0, definition="Synthetic definition",
                    evidence=[self.claim], reviewer="Test reviewer", rationale="Test reason")
        args.update(kwargs)
        return self.s.approve_definition(**args)

    def test_invented_quote_is_rejected(self):
        with self.assertRaises(ValueError):
            self.s.propose_claim(self.source, "Invented quotation", "Interpretation")

    def test_unreviewed_claim_cannot_support_approval(self):
        before = self.s.export(self.p)
        with self.assertRaises(ValueError):
            self.approve()
        self.assertEqual(before, self.s.export(self.p))

    def test_approval_and_audit_export(self):
        self.s.review_claim(self.claim, "Reviewer", "Verified against source", True)
        self.assertEqual(self.approve(), 1)
        result = self.s.export(self.p)
        self.assertEqual(result["revisions"][0]["version"], 1)
        self.assertEqual(result["events"][-1]["kind"], "definition_approved")
        self.assertIn("not assessed", result["research_status"])

    def test_stale_approval_does_not_overwrite(self):
        self.s.review_claim(self.claim, "Reviewer", "Reason", True)
        self.approve()
        before = self.s.export(self.p)
        with self.assertRaises(Conflict):
            self.approve(definition="Stale change")
        self.assertEqual(before, self.s.export(self.p))

    def test_other_project_evidence_is_rejected(self):
        self.s.review_claim(self.claim, "Reviewer", "Reason", True)
        other = self.s.create_project("Another construct")
        with self.assertRaises(ValueError):
            self.approve(project=other)

    def test_rejected_claim_cannot_support_definition(self):
        self.s.review_claim(self.claim, "Reviewer", "Unsupported interpretation", False)
        with self.assertRaises(ValueError):
            self.approve()

    def test_review_cannot_be_silently_overwritten(self):
        self.s.review_claim(self.claim, "Reviewer", "Reason", True)
        with self.assertRaises(Conflict):
            self.s.review_claim(self.claim, "Other", "Changed mind", False)


if __name__ == "__main__":
    unittest.main()
