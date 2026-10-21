"""Opt-in, independent, receive-only MQTT monitor sessions.

This foundation does not publish, decode, bridge, or transmit Meshtastic packets.
The existing legacy mqtt_monitor remains unchanged until UI integration.
"""
import configparser
from sitdown_online import ActivityCounter

NETWORKS = {
    'centralnj': ('mqtt_centralnj', 'mqtt.meshtastic.org'),
    'sjmesh': ('mqtt_sjmesh', 'mqtt.sjmesh.net'),
}


def network_config(source, network):
    """Return an isolated ActivityCounter config; never fill in credentials."""
    section, default_host = NETWORKS[network]
    config = configparser.ConfigParser()
    enabled = source.getboolean(section, 'enabled', fallback=False)
    topic = source.get(section, 'topic', fallback='').strip()
    host = source.get(section, 'host', fallback=default_host).strip()
    config['mqtt_monitor'] = {
        'enabled': str(enabled).lower(),
        'host': host,
        'topic': topic,
        'tls': source.get(section, 'tls', fallback='true'),
        'port': source.get(section, 'port', fallback='8883'),
        'username': source.get(section, 'username', fallback=''),
        'password': source.get(section, 'password', fallback=''),
    }
    return config


class DualMQTTMonitors:
    """Own separate Paho clients and counters for each opt-in broker."""

    def __init__(self, config):
        self.config = config
        self.monitors = {
            name: ActivityCounter(network_config(config, name))
            for name in NETWORKS
        }

    def start(self, factories=None):
        """Start only explicitly enabled networks with configured narrow topics."""
        factories = factories or {}
        for name, monitor in self.monitors.items():
            if not monitor.config.getboolean('mqtt_monitor', 'enabled'):
                continue
            self.connect(name, factory=factories.get(name))

    def connect(self, network, factory=None):
        """Connect one explicitly enabled profile; never connect the other."""
        monitor = self.monitors[network]
        if not monitor.config.getboolean('mqtt_monitor', 'enabled', fallback=False):
            monitor.status = 'Disabled — enable profile first'
            return False
        topic = monitor.config.get('mqtt_monitor', 'topic', fallback='').strip()
        if not topic or '#' in topic or '+' in topic:
            monitor.status = 'Disabled — explicit narrow topic required'
            return False
        host = monitor.config.get('mqtt_monitor', 'host', fallback='').strip()
        if not host or any(ch.isspace() for ch in host):
            monitor.status = 'Disabled — valid broker hostname required'
            return False
        try:
            port = monitor.config.getint('mqtt_monitor', 'port', fallback=8883)
            if not 1 <= port <= 65535:
                raise ValueError('port out of range')
        except ValueError:
            monitor.status = 'Disabled — invalid broker port'
            return False
        monitor.start(factory=factory)
        return monitor.client is not None

    def stop(self, network=None):
        if network is not None:
            self.monitors[network].stop()
        else:
            for monitor in self.monitors.values():
                monitor.stop()

    def snapshot(self):
        return {name: monitor.snapshot() for name, monitor in self.monitors.items()}

    def diagnostics(self):
        return {name: monitor.diagnostics() for name, monitor in self.monitors.items()}
