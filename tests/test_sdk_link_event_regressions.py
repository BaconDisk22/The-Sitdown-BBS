import io
import json
import unittest
from unittest.mock import Mock
from sitdown_monitor import ServerSupervisor
from sitdown_link import PREFIX


class LinkEventTests(unittest.TestCase):
    def make_supervisor(self, lines):
        supervisor = ServerSupervisor(["python", "server.py"], ".")
        process = Mock()
        process.stdout = io.StringIO("".join(lines))
        supervisor._read_output(process)
        return supervisor

    def test_sdk_connected_and_disconnected(self):
        s = self.make_supervisor([
            PREFIX + json.dumps({"state": "sdk_connected"}) + "\n",
            PREFIX + json.dumps({"state": "disconnected"}) + "\n",
        ])
        self.assertEqual(s.link_state, "disconnected")
        events = s.poll_events()
        self.assertIn(("link_state", "sdk_connected"), events)
        self.assertIn(("link_state", "disconnected"), events)

    def test_invalid_link_event_does_not_connect(self):
        s = self.make_supervisor([PREFIX + '{"state":"fake_connected"}\n'])
        self.assertEqual(s.link_state, "unverified")
