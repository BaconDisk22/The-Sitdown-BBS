"""Non-writing transport checks: never construct a Meshtastic SDK interface."""
import ipaddress
import re
import socket

TCP_PORT = 4403
PROTOCOL = (
    'Meshtastic protocol: Unverified. TCP reachability or USB enumeration does not '
    'verify a Meshtastic handshake, channel/PSK configuration, or mesh delivery. '
    'No SDK session is opened, no payload is sent, and no settings are changed.'
)


def _valid_host(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(len(host) <= 253 and all(
            re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
            for label in host.rstrip('.').split('.')))


def check_radio(connection, address, *, demo=False, busy=False):
    """Return a snapshot, not a connection guarantee; never open a serial port.

    TCP uses the same fixed port as the launcher. Socket operations have a short
    timeout; OS hostname resolution can take longer. Call off the UI thread.
    Skip while this launcher owns a session or has a recovery scheduled.
    """
    address = address.strip()
    heading = f'Radio Connection Preflight — {connection}\nEndpoint: {address or "(not selected)"}\n'
    if demo:
        result = 'Skipped: Demo mode does not contact a radio.'
    elif busy:
        result = 'Skipped: BBS session or recovery is active. No second connection was opened.'
    elif connection == 'tcp':
        if not address or not _valid_host(address):
            result = 'Invalid TCP host. Enter an IP address or hostname only (no URL or port).'
        else:
            try:
                with socket.create_connection((address, TCP_PORT), timeout=3):
                    pass
                result = f'TCP port {TCP_PORT}: Reachable at check time. Service identity is unverified.'
            except socket.gaierror:
                result = 'TCP: Hostname could not be resolved. Check the hostname and network.'
            except (TimeoutError, socket.timeout):
                result = 'TCP: Timed out. Check radio power, network access, and firewall.'
            except ConnectionRefusedError:
                result = f'TCP: Connection refused on port {TCP_PORT}. Check the radio TCP service.'
            except OSError:
                result = 'TCP: Connection unavailable. Check radio power, network access, and firewall.'
    elif connection == 'serial':
        try:
            from serial.tools import list_ports
            devices = sorted({port.device for port in list_ports.comports()})
            if not address:
                result = 'USB: Select an explicit device path before checking. No device was opened.'
            elif address in devices:
                result = 'USB: Selected device is listed. Access permissions and busy state are untested; device was not opened.'
            else:
                result = 'USB: Selected device is not listed. Check the cable, device path, and driver.'
            result += '\nDetected serial devices: ' + (', '.join(devices) or 'None')
        except ImportError:
            result = 'USB: pyserial is missing. Install requirements.txt.'
        except OSError:
            result = 'USB: Device enumeration failed. Check operating-system device access.'
    else:
        result = 'Unsupported transport. Select USB / Serial or TCP / Network.'
    return heading + result + '\n\n' + PROTOCOL
