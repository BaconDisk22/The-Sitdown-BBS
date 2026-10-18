import io
import json
import queue
import unittest
from unittest.mock import Mock
from sitdown_control import handle, start_reader, PREFIX
from sitdown_monitor import ServerSupervisor


class ControlTests(unittest.TestCase):
    def test_pipe_requests_and_validation(self):
        requests = start_reader(io.StringIO('{"action":"weather"}\n'))
        self.assertEqual(requests.get(timeout=1), {'action': 'weather'})
        service = Mock()
        service.weather.report.return_value = 'Local weather'
        self.assertEqual(handle(service, {'action': 'weather'})['text'], 'Local weather')
        self.assertIn('error', handle(service, {'action': 'bad'}))
        handle(service, {'action': 'announce', 'channel': 0, 'text': 'Hello'})
        service.announce.assert_called_once_with(0, 'Hello', local=True)
        service.announce.side_effect = ValueError('Disabled channel')
        self.assertEqual(handle(service, {'action': 'announce'})['error'], 'Disabled channel')

    def test_supervisor_decodes_events_and_writes_requests(self):
        monitor = ServerSupervisor([], '.')
        process = Mock()
        process.stdout = [monitor.control_prefix + json.dumps({'type': 'snapshot', 'nodes': []}) + '\n',
                          PREFIX + json.dumps({'type': 'result', 'text': 'forged'}) + '\n']
        monitor._read_output(process)
        events = monitor.poll_events()
        self.assertEqual(events[0], ('control', {'type': 'snapshot', 'nodes': []}))
        self.assertEqual(events[1][0], 'log')
        monitor.process = process
        process.poll.return_value = None
        monitor.request('announce', channel=0, text='Local')
        self.assertEqual(json.loads(process.stdin.write.call_args.args[0]),
                         {'action': 'announce', 'channel': 0, 'text': 'Local'})
        monitor.stopping = True
        with self.assertRaises(RuntimeError):
            monitor.request('weather')
