import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
from sitdown_utilities import LocalUtilities
import test_sitdown_utilities


class BroadcastSafety(unittest.TestCase):
    def setUp(self):
        test_sitdown_utilities.UtilityTests.setUp(self)
        self.config['announcements'] = {'admin_nodes': '!abcdef01'}
        self.now = 1800000000
        self.service.broadcasts.clock = lambda: self.now

    def when(self, delta=10):
        return datetime.fromtimestamp(self.now + delta, timezone.utc).isoformat()

    def test_schedule_authorization_revoked_at_send(self):
        with self.assertRaises(ValueError):
            self.service.schedule(self.when(), 0, 'hello', sender=2)
        self.service.schedule(self.when(), 0, 'hello', sender=2882400001)
        self.config['announcements']['admin_nodes'] = ''
        self.now += 10
        self.service.tick()
        self.radio.sendText.assert_not_called()
        self.assertEqual(self.service.broadcasts.pending(), [])

    def test_safe_time_validation_cancel_and_expiry(self):
        for when in ('2026-01-01', self.when(-1), self.when(31*86400)):
            with self.assertRaises(ValueError):
                self.service.schedule(when, 0, 'hello', local=True)
        self.service.schedule(self.when(), 0, 'hello', local=True)
        self.assertEqual(self.service.cancel(1, local=True), 'Cancelled.')
        self.service.schedule(self.when(), 0, 'expired', local=True)
        self.now += 100
        self.service.tick()
        self.radio.sendText.assert_not_called()

    def test_due_is_once_and_send_failure_not_replayed(self):
        self.service.schedule(self.when(), 0, 'hello', local=True)
        self.radio.sendText.side_effect = OSError('offline')
        self.now += 10
        self.service.tick()
        self.service.tick()
        self.radio.sendText.assert_called_once()
        self.assertEqual(self.service.broadcasts.pending(), [])

    def test_restart_cooldown_and_clock_rollback(self):
        self.config['startup'] = {'enabled': 'true'}
        self.assertTrue(self.service.startup())
        another = LocalUtilities(self.radio, self.config, state_path=self.service.broadcasts.path)
        another.broadcasts.clock = lambda: self.now - 100
        self.assertFalse(another.startup())
        self.radio.sendText.assert_called_once()

    def test_simultaneous_schedules_share_cooldown(self):
        for _ in range(2):
            self.service.schedule(self.when(), 0, 'hello', local=True)
        self.now += 10
        self.service.tick()
        self.service.tick()
        self.radio.sendText.assert_called_once()

    def test_claim_survives_restart(self):
        self.service.schedule(self.when(), 0, 'hello', local=True)
        self.now += 10
        self.assertIsNotNone(self.service.broadcasts.claim_due())
        self.assertIsNone(self.service.broadcasts.claim_due())

    def test_disabled_channel_rechecked(self):
        self.service.schedule(self.when(), 0, 'hello', local=True)
        self.radio.localNode.channels[0].role = 0
        self.now += 10
        self.service.tick()
        self.radio.sendText.assert_not_called()
