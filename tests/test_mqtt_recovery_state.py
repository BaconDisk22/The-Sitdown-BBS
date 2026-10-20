import unittest
from sitdown_mqtt_recovery_state import RecoveryState


class RecoveryStateTests(unittest.TestCase):
    def test_disabled(self):
        self.assertIsNone(RecoveryState().next_delay())

    def test_bounded_attempts(self):
        state = RecoveryState(enabled=True)
        self.assertEqual([state.next_delay() for _ in range(5)], [2, 4, 8, 16, 32])
        self.assertIsNone(state.next_delay())

    def test_operator_stop(self):
        state = RecoveryState(enabled=True)
        state.stop()
        self.assertIsNone(state.next_delay())

    def test_success_resets(self):
        state = RecoveryState(enabled=True)
        state.next_delay()
        state.connected()
        self.assertEqual(state.next_delay(), 2)
