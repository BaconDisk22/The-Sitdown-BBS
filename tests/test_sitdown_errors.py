import unittest
from sitdown_errors import explain_transport_error


class TransportHintsTests(unittest.TestCase):
    def test_network_unreachable(self):
        self.assertIn("network unreachable", explain_transport_error("OSError: No route to host").lower())

    def test_refused(self):
        self.assertIn("TCP", explain_transport_error("Connection refused"))

    def test_timeout(self):
        self.assertIn("timed out", explain_transport_error("timed out"))

    def test_serial_permissions(self):
        self.assertIn("USB permissions", explain_transport_error("Permission denied"))

    def test_unknown_error_does_not_echo_secret(self):
        self.assertNotIn("my-secret", explain_transport_error("my-secret unknown failure"))
