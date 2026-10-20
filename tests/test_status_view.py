import unittest
from sitdown_status_view import format_operator_status


class StatusViewTests(unittest.TestCase):
    def test_unverified_delivery(self):
        text = format_operator_status("connected", "connected")
        self.assertIn("Unverified", text)
        self.assertIn("MQTT monitor: connected", text)

    def test_defaults_safe(self):
        self.assertIn("MQTT monitor: disabled", format_operator_status())
