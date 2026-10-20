import unittest
from sitdown_send_preflight import send_preflight


class SendLimitTests(unittest.TestCase):
    def test_multibyte_size(self):
        allowed, reason = send_preflight(enabled=True, confirmed=True,
                                         radio_ready=True, message="🤌" * 51)
        self.assertFalse(allowed)
        self.assertIn("200", reason)

    def test_wrong_type(self):
        self.assertFalse(send_preflight(message=None)[0])

    def test_short_text_only_eligible(self):
        ok, reason = send_preflight(enabled=True, confirmed=True,
                                    radio_ready=True, message="hello")
        self.assertTrue(ok)
        self.assertIn("no message sent", reason)
