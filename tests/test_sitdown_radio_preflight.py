"""Offline preflight safety tests: no real sockets, devices, or SDK sessions."""
import socket
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sitdown_radio_preflight import check_radio


class RadioPreflightTests(unittest.TestCase):
    def test_tcp_connects_and_closes_without_reading_or_writing(self):
        with patch('sitdown_radio_preflight.socket.create_connection') as connect:
            report = check_radio('tcp', ' radio.local ')
            connect.assert_called_once_with(('radio.local', 4403), timeout=3)
            self.assertEqual([call[0] for call in connect.return_value.mock_calls],
                             ['__enter__', '__exit__'])
            self.assertIn('Reachable at check time', report)
            self.assertIn('Meshtastic protocol: Unverified', report)

    def test_invalid_hosts_never_connect(self):
        with patch('sitdown_radio_preflight.socket.create_connection') as connect:
            for host in ('', 'http://radio', 'radio:4403', 'a b', '-bad', 'a\nb'):
                self.assertIn('Invalid TCP host', check_radio('tcp', host))
            connect.assert_not_called()

    def test_ip_and_hostname_inputs(self):
        with patch('sitdown_radio_preflight.socket.create_connection'):
            for host in ('192.0.2.1', '::1', 'radio.local', 'radio.local.'):
                self.assertIn('Reachable', check_radio('tcp', host))

    def test_transport_errors_remain_unverified(self):
        for error, message in ((socket.gaierror(), 'resolved'), (TimeoutError(), 'Timed out'),
                               (ConnectionRefusedError(), 'refused'), (OSError(), 'unavailable')):
            with self.subTest(error=error), patch('sitdown_radio_preflight.socket.create_connection', side_effect=error):
                report = check_radio('tcp', 'radio.local')
                self.assertIn(message, report)
                self.assertIn('Meshtastic protocol: Unverified', report)

    def test_demo_and_busy_skip_all_io_for_both_transports(self):
        with patch('sitdown_radio_preflight.socket.create_connection') as connect, \
             patch.dict(sys.modules, {'serial.tools': Mock()}) as modules:
            serial = modules['serial.tools']
            for transport in ('tcp', 'serial'):
                for option in ({'demo': True}, {'busy': True}):
                    self.assertIn('Skipped', check_radio(transport, 'radio', **option))
            connect.assert_not_called()
            serial.list_ports.comports.assert_not_called()

    def test_usb_enumeration_never_opens_or_selects_a_device(self):
        serial = Mock()
        serial.list_ports.comports.return_value = [SimpleNamespace(device='/dev/cu.radio')]
        with patch.dict(sys.modules, {'serial.tools': serial}):
            for address, expected in (('/dev/cu.radio', 'Selected device is listed'),
                                      ('/dev/missing', 'not listed'), ('', 'Select an explicit')):
                report = check_radio('serial', address)
                self.assertIn(expected, report)
                self.assertIn('Meshtastic protocol: Unverified', report)
        self.assertTrue(all(call[0] == 'list_ports.comports' for call in serial.mock_calls))

    def test_usb_missing_dependency_and_enumeration_failure(self):
        with patch.dict(sys.modules, {'serial.tools': None}):
            self.assertIn('pyserial is missing', check_radio('serial', '/dev/cu.radio'))
        serial = Mock()
        serial.list_ports.comports.side_effect = OSError()
        with patch.dict(sys.modules, {'serial.tools': serial}):
            self.assertIn('enumeration failed', check_radio('serial', '/dev/cu.radio'))

    def test_unknown_transport(self):
        self.assertIn('Unsupported transport', check_radio('bluetooth', 'radio'))
