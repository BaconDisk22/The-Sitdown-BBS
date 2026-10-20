"""Preflight skip paths should not touch transport APIs."""
import unittest
from unittest.mock import patch
from sitdown_radio_preflight import check_radio


class RadioPreflightOfflineTests(unittest.TestCase):
    def test_demo_mode_skips_tcp(self):
        with patch("sitdown_radio_preflight.socket.create_connection") as connect:
            report = check_radio("tcp", "radio.example", demo=True)
            connect.assert_not_called()
        self.assertIn("Demo mode", report)
        self.assertIn("Unverified", report)

    def test_busy_mode_skips_tcp(self):
        with patch("sitdown_radio_preflight.socket.create_connection") as connect:
            report = check_radio("tcp", "radio.example", busy=True)
            connect.assert_not_called()
        self.assertIn("Skipped", report)

    def test_invalid_tcp_host_skips_socket(self):
        with patch("sitdown_radio_preflight.socket.create_connection") as connect:
            report = check_radio("tcp", "http://radio.example:4403")
            connect.assert_not_called()
        self.assertIn("Invalid TCP host", report)

    def test_unknown_transport_never_connects(self):
        with patch("sitdown_radio_preflight.socket.create_connection") as connect:
            report = check_radio("bluetooth", "device")
            connect.assert_not_called()
        self.assertIn("Unsupported transport", report)


if __name__ == "__main__":
    unittest.main()
