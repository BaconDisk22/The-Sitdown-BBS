"""Guard against stacked PRs marked merged without desktop MQTT features on main."""
import inspect
import unittest
from sitdown_desktop import SitdownApp


class MQTTDesktopIntegrationTests(unittest.TestCase):
    def test_expected_desktop_entrypoints_exist(self):
        for name in ('mqtt_network_action', 'start_opted_in_mqtt', 'mqtt_network_status'):
            self.assertTrue(callable(getattr(SitdownApp, name, None)), name)

    def test_startup_auto_connect_is_explicitly_gated(self):
        source = inspect.getsource(SitdownApp.start_opted_in_mqtt)
        self.assertIn("'auto_connect'", source)
        self.assertIn("'enabled'", source)
        self.assertIn('self.demo.get()', source)

    def test_desktop_status_is_receive_only(self):
        source = inspect.getsource(SitdownApp.mqtt_network_status)
        self.assertIn("MQTT RX", source)
        self.assertNotIn('.publish(', source)

    def test_close_stops_mqtt_sessions(self):
        source = inspect.getsource(SitdownApp.close)
        self.assertIn('self.dual_mqtt.stop()', source)


if __name__ == '__main__':
    unittest.main()
