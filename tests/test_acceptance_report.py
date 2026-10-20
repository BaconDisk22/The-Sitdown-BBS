import unittest
from sitdown_acceptance_report import acceptance_record


class AcceptanceReportTests(unittest.TestCase):
    def test_default_not_run(self):
        self.assertEqual(acceptance_record()["result"], "not_run")

    def test_two_way_requires_evidence(self):
        with self.assertRaises(ValueError):
            acceptance_record("two_way_verified")

    def test_rejects_invalid(self):
        with self.assertRaises(ValueError):
            acceptance_record("success")
