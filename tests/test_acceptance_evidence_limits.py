import unittest
from sitdown_acceptance_report import acceptance_record


class EvidenceTests(unittest.TestCase):
    def test_size_limit(self):
        with self.assertRaises(ValueError):
            acceptance_record(evidence="x" * 4097)

    def test_type(self):
        with self.assertRaises(ValueError):
            acceptance_record(evidence=None)
