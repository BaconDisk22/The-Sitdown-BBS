import unittest
from unittest.mock import patch
from sitdown_radio_preflight import check_radio


class RadioPreflightIsolationTests(unittest.TestCase):
    def test_demo_does_not_open_socket(self):
        with patch("socket.create_connection", side_effect=AssertionError("opened")):
            report = check_radio("tcp", "example.org", demo=True)
        self.assertIn("Skipped", report)
        self.assertIn("Unverified", report)

    def test_busy_does_not_open_socket(self):
        with patch("socket.create_connection", side_effect=AssertionError("opened")):
            report = check_radio("tcp", "example.org", busy=True)
        self.assertIn("Skipped", report)

    def test_invalid_host_does_not_open_socket(self):
        with patch("socket.create_connection", side_effect=AssertionError("opened")):
            report = check_radio("tcp", "http://example.org:4403")
        self.assertIn("Invalid TCP host", report)
