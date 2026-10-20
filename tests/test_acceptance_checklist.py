from pathlib import Path
import unittest


class AcceptanceDocumentTests(unittest.TestCase):
    def test_checklist_explicitly_requires_real_delivery(self):
        doc = (Path(__file__).resolve().parents[1] / "docs" / "CENTRALNJ_ACCEPTANCE.md").read_text()
        self.assertIn("independent radio", doc)
        self.assertIn("Not run", doc)
        self.assertIn("never automatically publish", doc)
