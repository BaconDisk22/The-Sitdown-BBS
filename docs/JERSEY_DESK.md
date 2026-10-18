# Jersey desktop and utilities

The eight dashboard tabs are Home, BBS, Messages, Boards, Radio, Nodes, Settings,
and About. Home retains connection selection, process/RX status, restart controls,
Jersey greeting preview, searchable/exportable logs, and the skyline design.
Messages and Boards are read-only local operator views (latest 100 records).
The BBS tab has announcements, weather, and MQTT panels. Nodes searches the
entire connected radio database, including nodes that have never messaged the BBS.
Node details include names/ID, hardware, role, last-heard timestamp, signal/hops,
position and device metrics when provided by the radio. Missing data is not invented.

## Configure and operate

Copy `example_config.ini` to `config.ini` for source use. The packaged Mac app
uses `~/.sitdown-bbs/config.ini`. Settings preserves unrelated INI sections and
applies changes on the next server start. MQTT passwords are masked; the saved
INI has owner-only permissions. Source use needs `pip install -r requirements.txt`.
Optional MQTT additionally needs `pip install -r requirements-mqtt.txt`; the Mac
package includes it but leaves connections disabled.

- **The Boss Has Spoken:** select an enabled channel, compose up to 200 UTF-8
  bytes, preview, then broadcast. The local desktop operator is authorized by
  access to the app. Over radio, `/announce <channel> <text>` requires the sender's
  node ID in `[announcements] admin_nodes`. Empty means deny everyone. This uses
  Meshtastic packet identity, not cryptographic user authentication. Protect your
  mesh channel keys. A successful call means submission, not confirmed delivery.
- **Startup:** `[startup] enabled = false` by default. Enable it and choose a
  channel for one broadcast attempt per server process start, including crash
  restarts. Empty message uses the generated public personality greeting; a custom
  message is sent verbatim. Invalid/failed broadcasts do not stop the BBS.
- **Personality:** desktop greeting choices stay local. The Settings personality
  tab controls the generated startup greeting. Public profanity requires its own
  explicit opt-in. User mail, announcements, and technical diagnostics are never
  rewritten. The optional app auto-start checkbox is saved with Home's Save Settings.
- **Jersey Weather Desk:** `/weather` returns an operator-written `local_report`
  offline. `internet_enabled = true` explicitly enables a request to Open-Meteo
  for configured coordinates, only on demand. Requests have a five-second timeout,
  a ten-minute cache/backoff and stale-data labels. No automatic geolocation.
  Weather is model data, not an emergency warning service.
- **The Wire:** `/wire` reports this process's MQTT counts. `[mqtt_monitor] enabled`
  defaults false; broker and topic have no defaults. TLS is on by default. The
  monitor subscribes only, excludes retained history, stores at most 1,000 topics,
  shows the top ten and never forwards MQTT messages to the radio. Counts reset
  on restart and are independent of radio RX. Failures do not stop the radio BBS.
- **Who's Who:** `/node <ID, short name, or long name>` supports numeric IDs,
  `!`-prefixed IDs and eight-digit hex IDs. Radio results are limited to three
  matches; refine ambiguous searches. Desktop lookup lists all matches from the
  latest server snapshot. Reopen the tab to refresh. A snapshot left after
  disconnection is historical, not a live presence claim.

Use `/tools` to discover the radio utilities. Commands do not intercept pending
mail/bulletin composition or peer synchronization. The desktop shares the existing
radio connection using a private parent/child pipe, with no HTTP listener.

## Reference and verification

The reference's dark skyline, bridge, tricolor accents, red controls and Jersey
identity guide the real Tk interface. The generated icon adds a New Jersey
silhouette. Screenshots are captured from demo mode and labeled accordingly.
They are not evidence of a connected radio.

CI runs unit tests, real Tk layout/navigation checks on Intel macOS, captures the
app, and packages an x86_64 app/DMG. It also launches the packaged app in isolated
demo mode to verify bundled imports and Tk pages without a radio. These checks do not prove a physical radio
works with the packaged app. Before a release, test the actual DMG on an Intel Mac:
launch it, connect to your TCP Meshtastic radio, send/receive a DM, read/write a
board message, restart/disconnect, and verify each opt-in feature independently.
Do not claim hardware validation until those observations are recorded.

API references: [Open-Meteo](https://open-meteo.com/en/docs),
[Paho MQTT](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html).
See [upstream audit](UPSTREAM_AUDIT.md) for adoption decisions.
