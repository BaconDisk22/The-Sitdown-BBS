import unittest
from unittest.mock import patch
from io import StringIO
from tools.centralnj_acceptance import main


class AcceptanceCLITests(unittest.TestCase):
    def test_default_not_run(self):
        with patch("sys.stdout", new_callable=StringIO) as output:
            self.assertEqual(main([]), 0)
            self.assertIn('"not_run"', output.getvalue())

    def test_two_way_claim_requires_evidence(self):
        with self.assertRaises(SystemExit):
            main(["--result", "two_way_verified"])
