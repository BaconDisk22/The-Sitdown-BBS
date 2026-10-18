import configparser
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from sitdown_online import WeatherDesk, ActivityCounter


class OnlineTests(unittest.TestCase):
    def setUp(self):
        self.config = configparser.ConfigParser()
        self.open = Mock()

    def test_defaults_never_touch_network(self):
        self.assertIn('disabled', WeatherDesk(self.config, self.open).report())
        self.open.assert_not_called()
        mqtt = ActivityCounter(self.config)
        mqtt.start(self.open)
        self.open.assert_not_called()
        self.assertEqual(mqtt.snapshot()['total'], 0)

    def test_local_weather_works_offline(self):
        self.config['weather'] = {'local_report': '10:00 UTC: clear skies'}
        self.assertIn('10:00 UTC', WeatherDesk(self.config, self.open).report())
        self.open.assert_not_called()

    def test_cache_timeout_stale_and_cooldown(self):
        self.config['weather'] = {'internet_enabled': 'true', 'latitude': '40', 'longitude': '-74'}
        now = [0]
        weather = WeatherDesk(self.config, self.open, lambda: now[0])
        context = Mock()
        self.open.return_value = context
        context.__enter__ = Mock(return_value=Mock(read=Mock(return_value=json.dumps({'current': {
            'temperature_2m': 70, 'wind_speed_10m': 5, 'weather_code': 0, 'time': '2026-10-18T12:00'}}).encode())))
        context.__exit__ = Mock(return_value=False)
        self.assertIn('70 F', weather.report())
        self.assertIn('70 F', weather.report())
        self.open.assert_called_once()
        self.assertEqual(self.open.call_args.kwargs['timeout'], 5)
        now[0] = 601
        self.open.side_effect = TimeoutError()
        self.assertIn('STALE', weather.report())
        self.assertIn('STALE', weather.report())
        self.assertEqual(self.open.call_count, 2)

    def test_invalid_coordinates_and_bad_response(self):
        self.config['weather'] = {'internet_enabled': 'true', 'latitude': 'nan', 'longitude': '0'}
        self.assertIn('unavailable', WeatherDesk(self.config, self.open).report())
        self.open.assert_not_called()

    def test_invalid_optional_flags_stay_offline(self):
        self.config['mqtt_monitor'] = {'enabled': 'invalid'}
        counter = ActivityCounter(self.config)
        counter.start(self.open)
        self.open.assert_not_called()
        self.assertIn('Unavailable', counter.status)
        self.config['weather'] = {'internet_enabled': 'invalid'}
        self.assertIn('no request', WeatherDesk(self.config, self.open).report())
        self.open.assert_not_called()

    def test_mqtt_opt_in_subscribe_count_and_stop(self):
        self.config['mqtt_monitor'] = {'enabled': 'true', 'host': 'example.invalid', 'topic': 'msh/test/#'}
        client = Mock()
        client.subscribe.return_value = (0, 1)
        counter = ActivityCounter(self.config)
        counter.start(lambda: client)
        client.tls_set.assert_called_once()
        client.connect_async.assert_called_once_with('example.invalid', 8883, 60)
        client.on_connect(client, None, None, 0, None)
        client.subscribe.assert_called_once_with('msh/test/#')
        for retain in (True, False, False):
            client.on_message(client, None, SimpleNamespace(topic='msh/test/node', retain=retain))
        self.assertEqual(counter.snapshot()['total'], 2)
        client.publish.assert_not_called()
        counter.stop()
        client.disconnect.assert_called_once()
        client.loop_stop.assert_called_once()

    def test_bad_mqtt_config_does_not_start_client(self):
        self.config['mqtt_monitor'] = {'enabled': 'true'}
        counter = ActivityCounter(self.config)
        counter.start(self.open)
        self.open.assert_not_called()
        self.assertIn('Unavailable', counter.status)
