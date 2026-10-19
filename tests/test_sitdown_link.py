import threading
import unittest
from unittest.mock import Mock
from sitdown_link import RadioLinkMonitor


class RadioLinkTests(unittest.TestCase):
    def setUp(self):
        self.interface = Mock(isConnected=threading.Event())
        self.clock = Mock(return_value=0)
        self.emit = Mock()
        self.monitor = RadioLinkMonitor(self.interface, clock=self.clock, emit=self.emit)

    def test_disconnect_expires_even_while_process_is_alive(self):
        self.interface.isConnected.set()
        self.assertFalse(self.monitor.check())
        self.interface.isConnected.clear()
        self.assertFalse(self.monitor.check())
        self.clock.return_value = 29
        self.assertFalse(self.monitor.check())
        self.clock.return_value = 30
        self.assertTrue(self.monitor.check())
        self.emit.assert_called_with({'state': 'disconnected'})

    def test_sdk_recovery_resets_grace_and_silent_connected_radio_is_not_failed(self):
        self.monitor.check()
        self.clock.return_value = 20
        self.interface.isConnected.set()
        self.assertFalse(self.monitor.check())
        self.clock.return_value = 1000
        self.assertFalse(self.monitor.check())
        self.interface.isConnected.clear()
        self.assertFalse(self.monitor.check())
        self.clock.return_value = 1030
        self.assertTrue(self.monitor.check())

    def test_state_only_emitted_on_transition(self):
        self.monitor.check()
        self.monitor.check()
        self.assertEqual(self.emit.call_count, 1)
        self.interface.isConnected.set()
        self.monitor.check()
        self.emit.assert_called_with({'state': 'sdk_connected'})
