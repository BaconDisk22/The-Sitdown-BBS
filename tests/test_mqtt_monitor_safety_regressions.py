import configparser
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from sitdown_online import ActivityCounter


class MqttSafetyTests(unittest.TestCase):
    def setUp(self):
        self.counter = ActivityCounter(configparser.ConfigParser())

    def test_retained_payload_is_not_activity(self):
        self.counter._message(None, None, SimpleNamespace(retain=True, topic="msh/test"))
        self.assertEqual(self.counter.snapshot()["total"], 0)

    def test_receive_does_not_publish(self):
        client = Mock()
        self.counter._message(client, None, SimpleNamespace(retain=False, topic="msh/test"))
        self.assertEqual(self.counter.snapshot()["total"], 1)
        client.publish.assert_not_called()

    def test_topic_storage_is_bounded(self):
        for i in range(1002):
            self.counter._message(None, None, SimpleNamespace(retain=False, topic=f"msh/{i}"))
        snap = self.counter.snapshot()
        self.assertEqual(snap["total"], 1002)
        self.assertEqual(snap["overflow"], 2)
        self.assertEqual(len(self.counter.counts), 1000)
