"""Offline send safety boundary tests: no SDK or MQTT calls."""
import unittest
from sitdown_send_preflight import send_preflight


class SendPreflightBoundaryTests(unittest.TestCase):
    def test_all_permission_gates_must_pass(self):
        base = dict(enabled=True, confirmed=True, radio_ready=True,
                    demo_mode=False, message="Hello CentralNJ")
        for key in ("enabled", "confirmed", "radio_ready"):
            with self.subTest(gate=key):
                attempt = dict(base)
                attempt[key] = False
                self.assertFalse(send_preflight(**attempt)[0])

    def test_whitespace_only_denied(self):
        self.assertFalse(send_preflight(enabled=True, confirmed=True,
                                        radio_ready=True, message="  \n  ")[0])

    def test_non_text_denied(self):
        self.assertEqual(send_preflight(message=None)[0], False)

    def test_utf8_limit_counts_bytes(self):
        kwargs = dict(enabled=True, confirmed=True, radio_ready=True)
        self.assertTrue(send_preflight(message="é" * 100, **kwargs)[0])
        allowed, reason = send_preflight(message="é" * 101, **kwargs)
        self.assertFalse(allowed)
        self.assertIn("200 UTF-8 bytes", reason)


if __name__ == "__main__":
    unittest.main()
