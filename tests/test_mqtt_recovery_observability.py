import configparser
import unittest
from sitdown_online import ActivityCounter


class RecoveryTelemetryTests(unittest.TestCase):
    def test_disabled_monitor_is_stopped_on_request(self):
        counter = ActivityCounter(configparser.ConfigParser())
        self.assertEqual(counter.snapshot()['recovery_attempts'], 0)
        counter.stop()
        self.assertTrue(counter.snapshot()['recovery_stopped'])

    def test_failure_increments_and_connect_resets(self):
        counter = ActivityCounter(configparser.ConfigParser())
        counter.recovery.enabled = True
        counter._connect_fail(None, None)
        self.assertEqual(counter.snapshot()['recovery_attempts'], 1)
        counter.recovery.connected()
        self.assertEqual(counter.snapshot()['recovery_attempts'], 0)
