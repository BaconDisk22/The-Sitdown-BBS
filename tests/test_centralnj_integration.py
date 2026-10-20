"""Offline integration tests: no MQTT broker, no Tk window, no radio hardware."""
import configparser
import unittest
from unittest.mock import Mock
from sitdown_online import ActivityCounter
from sitdown_mqtt_recovery_state import RecoveryState
from sitdown_send_preflight import send_preflight
from sitdown_status_view import format_operator_status


class CentralNJIntegrationTests(unittest.TestCase):
    def test_disabled_monitor_never_constructs_client(self):
        cfg = configparser.ConfigParser()
        cfg.add_section("mqtt_monitor")
        cfg.set("mqtt_monitor", "enabled", "false")
        factory = Mock(side_effect=AssertionError("must not connect"))
        counter = ActivityCounter(cfg)
        counter.start(factory=factory)
        factory.assert_not_called()

    def test_recovery_stop_is_terminal(self):
        state = RecoveryState(enabled=True)
        self.assertEqual(state.next_delay(), 2)
        state.stop()
        self.assertIsNone(state.next_delay())

    def test_send_preflight_never_assumes_confirmation(self):
        allowed, reason = send_preflight(enabled=True, confirmed=False,
                                         radio_ready=True, message="test")
        self.assertFalse(allowed)
        self.assertIn("confirmation", reason.lower())

    def test_status_does_not_claim_two_way(self):
        text = format_operator_status("connected", "connected")
        self.assertIn("Unverified", text)


if __name__ == "__main__":
    unittest.main()
