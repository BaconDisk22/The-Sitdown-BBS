# Dual MQTT network foundation

The `sitdown_dual_mqtt.DualMQTTMonitors` backend supports **independent**
CentralNJ and SJMesh receive-only MQTT counters. Both are disabled by default.
The existing single `[mqtt_monitor]` integration is unchanged; the new manager
is not yet wired to the desktop Settings or startup lifecycle.

Use `[mqtt_centralnj]` and `[mqtt_sjmesh]` with explicit `enabled=true`,
a narrow `topic`, and broker credentials supplied locally. Defaults for the
hostnames are `mqtt.meshtastic.org` and `mqtt.sjmesh.net` respectively.
No username, password, PSK, or broad wildcard topic is supplied by the app.
TLS defaults on; port defaults to 8883. Topic wildcard subscriptions are rejected
by the manager before connecting.

Next PR: independent Settings toggles, per-network auto-connect preferences,
connect/disconnect controls, status and counters, and lifecycle wiring. An
additional PR can implement opt-in *protocol-correct* sending with independent
authorization, rate limits, and loop protection. This foundation **cannot**
publish, decrypt, bridge, or reply to Meshtastic messages over MQTT. The existing
radio BBS command/reply path is unaffected.
