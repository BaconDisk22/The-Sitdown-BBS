import unittest
from sitdown_release_readiness import REQUIRED, evaluate_release


class ReleaseReadinessTests(unittest.TestCase):
    def test_unknown_blocks(self):
        self.assertFalse(evaluate_release({})["ready"])

    def test_all_explicit(self):
        self.assertTrue(evaluate_release({key: True for key in REQUIRED})["ready"])

    def test_truthy_strings_fail(self):
        self.assertFalse(evaluate_release({"unit_tests_passed": "true"})["ready"])
