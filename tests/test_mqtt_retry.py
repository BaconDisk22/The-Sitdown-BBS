import unittest
from sitdown_mqtt_retry import retry_delay, should_retry


class RetryTests(unittest.TestCase):
    def test_bounded(self):
        self.assertEqual([retry_delay(i) for i in range(4)], [2, 4, 8, 16])
        self.assertEqual(retry_delay(100), 120)

    def test_disabled_never_retries(self):
        self.assertFalse(should_retry(enabled=False, user_stopped=False, attempt=0))

    def test_operator_stop_blocks_retries(self):
        self.assertFalse(should_retry(enabled=True, user_stopped=True, attempt=0))

    def test_max_attempts(self):
        self.assertFalse(should_retry(enabled=True, user_stopped=False, attempt=5))

    def test_invalid_attempt(self):
        with self.assertRaises(ValueError):
            retry_delay(-1)
