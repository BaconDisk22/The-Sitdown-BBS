import unittest
from sitdown_send_preflight import send_preflight


class SendPreflightTests(unittest.TestCase):
    def test_default_denied(self):
        self.assertFalse(send_preflight()[0])

    def test_demo_denied(self):
        self.assertFalse(send_preflight(enabled=True, confirmed=True, radio_ready=True,
                                        demo_mode=True, message="hi")[0])

    def test_eligible_is_not_sent(self):
        allowed, reason = send_preflight(enabled=True, confirmed=True,
                                         radio_ready=True, message="hi")
        self.assertTrue(allowed)
        self.assertIn("no message sent", reason)
