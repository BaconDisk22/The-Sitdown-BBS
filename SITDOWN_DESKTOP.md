# The Sitdown desktop

See the [Jersey desktop guide](docs/JERSEY_DESK.md) for the eight tab pages,
announcements, startup broadcasts, offline/online weather, optional MQTT, and
full node lookup. The reference is implemented as a real Tk app with original
skyline/icon artwork; demo screenshots are not hardware validation.

Start from source with `python sitdown_desktop.py`. Select TCP and enter your
radio hostname/IP, or select USB/Serial. Configure `config.ini` first. Packaged
Mac builds keep configuration and BBS data in `~/.sitdown-bbs`.

### Radio Connection Preflight

Use **Check Radio Connection** in the Connection Status card before starting.
It checks the currently displayed endpoint without saving it or starting the BBS.
TCP connects to port 4403 and immediately closes without sending application data.
USB only enumerates serial devices; it never opens a device, so permissions and
whether another program holds the device remain untested. Select an explicit USB
path; preflight never guesses or changes it.

An open TCP port or listed USB device is **not Meshtastic protocol verification**.
Preflight always reports protocol unverified: it does not construct an SDK
interface, request configuration, transmit mesh packets, or change settings.
The running BBS's existing SDK session status remains a separate diagnostic.
Checks are skipped in Demo mode and while this BBS is running or awaiting recovery.
Close other radio clients before a TCP check: a TCP connection can briefly occupy
a radio client slot even without sending data.

Checks run in the background, with a three-second socket timeout. Operating-system
hostname resolution can take longer; the window stays responsive. Duplicate checks
and starting the BBS are blocked until the check finishes. Results identify the
endpoint snapshot checked, which may differ from fields edited during the check.
