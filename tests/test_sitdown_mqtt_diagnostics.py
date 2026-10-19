"""Offline checks for MQTT monitoring diagnostics; no broker or radio required."""
import configparser
import unittest

from sitdown_online import ActivityCounter


def monitor(**values):
    config = configparser.ConfigParser()
    config['mqtt_monitor'] = {'enabled': 'false', 'host': '', 'topic': '',
                              'port': '8883', 'username': '', 'password': ''}
    config['mqtt_monitor'].update({k: str(v) for k, v in values.items()})
    return ActivityCounter(config)


class MQTTDiagnosticsTests(unittest.TestCase):
    def test_disabled_is_explicit(self):
        self.assertIn('disabled', monitor().diagnostics())

    def test_missing_topic_is_reported(self):
        self.assertIn('subscription topic', monitor(enabled='true', host='mqtt.meshtastic.org').diagnostics())

    def test_broad_topic_warns(self):
        self.assertIn('broad', monitor(enabled='true', host='mqtt.meshtastic.org', topic='msh/US/#').diagnostics())

    def test_invalid_port_warns(self):
        self.assertIn('invalid MQTT port', monitor(enabled='true', host='mqtt.meshtastic.org', topic='msh/US/2/e', port='70000').diagnostics())

    def test_diagnostics_never_reveal_password(self):
        counter = monitor(enabled='true', host='mqtt.meshtastic.org', topic='msh/US/2/e',
                          username='private-user', password='secret-value')
        result = counter.diagnostics()
        self.assertIn('configured', result)
        self.assertNotIn('secret-value', result)
        self.assertNotIn('private-user', result)
