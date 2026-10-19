import configparser
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from sitdown_utilities import LocalUtilities, lookup_nodes


class UtilityTests(unittest.TestCase):
    def setUp(self):
        self.config = configparser.ConfigParser()
        self.radio = Mock(nodes={'!abcdef01': {'num': 2882400001, 'user': {
            'id': '!abcdef01', 'shortName': 'NJ01', 'longName': 'North Jersey'},
            'snr': 0, 'position': {'latitude': 40.7}, 'deviceMetrics': {'batteryLevel': 80}},
            '!00000002': {}})
        self.radio.localNode.channels = [SimpleNamespace(role=1, settings=SimpleNamespace(name='Local')),
                                         SimpleNamespace(role=0, settings=SimpleNamespace(name='Disabled'))]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = LocalUtilities(self.radio, self.config, state_path=Path(self.temp.name) / 'state.db')

    def test_full_lookup_ids_names_incomplete_records(self):
        for query in ('!abcdef01', 'abcdef01', '2882400001', 'nj01', 'north jersey'):
            result = lookup_nodes(self.radio.nodes, query)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['snr'], 0)
        self.assertEqual(len(lookup_nodes(self.radio.nodes)), 2)
        self.assertEqual(lookup_nodes(self.radio.nodes, 'missing'), [])

    def test_admin_default_denies_and_validates_channel_and_bytes(self):
        self.assertIn('administrator', self.service.command('/announce 0 hello', 2882400001))
        self.radio.sendText.assert_not_called()
        self.config['announcements'] = {'admin_nodes': '!abcdef01'}
        self.assertIn('submitted', self.service.command('/announce 0 hello', 2882400001))
        self.radio.sendText.assert_called_once_with(text='hello', destinationId=0xffffffff,
            channelIndex=0, wantAck=False, wantResponse=False)
        self.radio.sendText.reset_mock()
        for text in ('/announce 1 hello', '/announce 0 ' + '🗽'*51, '/announce -1 hello', '/announce 0 '):
            self.service.command(text, 2882400001)
        self.radio.sendText.assert_not_called()

    def test_startup_off_once_and_clean_by_default(self):
        self.assertFalse(self.service.startup())
        self.radio.sendText.assert_not_called()
        self.config['startup'] = {'enabled': 'true'}
        self.config['personality'] = {'public_mode': 'uncensored'}
        self.assertTrue(self.service.startup())
        self.assertFalse(self.service.startup())
        self.assertEqual(self.radio.sendText.call_args.kwargs['text'], 'Ayyy, pull up a chair. We gotta talk.')

    def test_startup_failure_is_not_retried(self):
        self.config['startup'] = {'enabled': 'true'}
        self.radio.sendText.side_effect = OSError('offline')
        with self.assertLogs(level='ERROR'):
            self.assertFalse(self.service.startup())
        self.assertFalse(self.service.startup())
        self.radio.sendText.assert_called_once()

    def test_commands_preserve_pending_text_and_sync(self):
        import message_processing as mp
        for state in ({'command': 'MAIL', 'step': 1}, {'command': 'BULLETIN_POST_CONTENT', 'step': 1}):
            with patch.object(mp, 'get_user_state', return_value=state), \
                 patch.object(mp, 'handle_mail_steps'), patch.object(mp, 'handle_bb_steps'):
                self.radio.sitdown = Mock()
                mp.process_message(1, '/announce 0 user text', self.radio)
                self.radio.sitdown.command.assert_not_called()
        with patch.object(mp, 'get_user_state', return_value=None):
            mp.process_message(1, '/announce 0 sync', self.radio, is_sync_message=True)
            self.radio.sitdown.command.assert_not_called()

    def test_receive_routes_only_direct_messages_to_utilities(self):
        import message_processing as mp
        self.radio.bbs_nodes = []
        self.radio.myInfo.my_node_num = 42
        self.radio.sitdown = self.service
        packet = {'from': 2882400001, 'fromId': '!abcdef01', 'to': 42,
                  'decoded': {'portnum': 'TEXT_MESSAGE_APP', 'payload': b'/node NJ01'}}
        with patch.object(mp, 'get_user_state', return_value=None), patch.object(mp, 'send_message') as send:
            mp.on_receive(packet, self.radio)
            self.assertIn('North Jersey', send.call_args.args[0])
            send.reset_mock()
            packet['to'] = 0xffffffff
            mp.on_receive(packet, self.radio)
            send.assert_not_called()

    def test_radio_reply_chunks_preserve_unicode_within_byte_budget(self):
        from utils import message_chunks
        text = 'Jersey 🗽 ' * 80
        chunks = list(message_chunks(text))
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(0 < len(chunk.encode('utf-8')) <= 200 for chunk in chunks))
        self.assertEqual(list(message_chunks('')), [])

    def test_tcp_interface_uses_hostname(self):
        from config_init import get_interface
        with patch('config_init.meshtastic.tcp_interface.TCPInterface') as tcp:
            self.assertIs(get_interface({'interface_type': 'tcp', 'hostname': '192.0.2.10'}), tcp.return_value)
            tcp.assert_called_once_with(hostname='192.0.2.10')
