"""Offline utilities shared by radio commands and the desktop operator."""
import configparser
import logging
import re
import threading
from sitdown_personality import Personality
from sitdown_online import WeatherDesk, ActivityCounter


def node_id(value):
    try:
        if isinstance(value, int) or str(value).isdigit():
            number = int(value)
        elif re.fullmatch(r'!?[0-9a-fA-F]{8}', str(value)):
            number = int(str(value).lstrip('!'), 16)
        else:
            return None
        return f'!{number:08x}' if 0 <= number <= 0xffffffff else None
    except (TypeError, ValueError):
        return None


def lookup_nodes(nodes, query=''):
    """Search all radio nodes, including ones that never sent the BBS a DM."""
    query = query.strip().casefold()
    wanted_id = node_id(query) if query else None
    results = []
    for key, node in list((nodes or {}).items()):
        user = node.get('user') or {}
        identity = node_id(user.get('id')) or node_id(key) or node_id(node.get('num'))
        names = [str(user.get(field, '')) for field in ('shortName', 'longName')]
        if query and not ((wanted_id is not None and wanted_id == identity) or any(query in name.casefold() for name in names)):
            continue
        results.append({'id': identity or str(key), 'shortName': names[0], 'longName': names[1],
                        'hardware': user.get('hwModel'), 'role': user.get('role'),
                        'lastHeard': node.get('lastHeard'), 'snr': node.get('snr'),
                        'hopsAway': node.get('hopsAway'), 'position': node.get('position', {}),
                        'deviceMetrics': node.get('deviceMetrics', {})})
    return sorted(results, key=lambda row: row['id'])


def format_node(row):
    return (f"{row['id']} {row['shortName']} / {row['longName']}\n"
            f"HW: {row['hardware']} Role: {row['role']}\n"
            f"Last heard: {row['lastHeard']} SNR: {row['snr']} Hops: {row['hopsAway']}\n"
            f"Metrics: {row['deviceMetrics']}\nPosition: {row['position']}")


class LocalUtilities:
    def __init__(self, interface, config=None):
        self.interface = interface
        self.config = config if config is not None else configparser.ConfigParser()
        self.lock = threading.RLock()
        self.startup_attempted = False
        self.weather = WeatherDesk(self.config)
        self.mqtt = ActivityCounter(self.config)

    def channels(self):
        channels = getattr(getattr(self.interface, 'localNode', None), 'channels', [])
        return [{'index': i, 'name': ch.settings.name or f'Channel {i}'}
                for i, ch in enumerate(channels) if ch.role != 0]

    def is_admin(self, sender):
        admins = self.config.get('announcements', 'admin_nodes', fallback='').split(',')
        identity = node_id(sender)
        return identity is not None and identity in {node_id(a.strip()) for a in admins if a.strip()}

    def announce(self, channel, text, *, sender=None, local=False):
        if not local and not self.is_admin(sender):
            raise ValueError('Announcements require a configured administrator node.')
        if isinstance(channel, bool) or not isinstance(channel, int):
            raise ValueError('Select a numeric channel index.')
        if channel not in {ch['index'] for ch in self.channels()}:
            raise ValueError('Channel is disabled or unavailable on this radio.')
        if not text.strip() or len(text.encode('utf-8')) > 200:
            raise ValueError('Announcement must contain 1–200 UTF-8 bytes.')
        with self.lock:
            self.interface.sendText(text=text, destinationId=0xffffffff,
                                    channelIndex=channel, wantAck=False, wantResponse=False)
        return 'Announcement submitted to radio (delivery unconfirmed).'

    def startup(self):
        """One attempt per process start; disabled by default."""
        if self.startup_attempted:
            return False
        try:
            if not self.config.getboolean('startup', 'enabled', fallback=False):
                return False
            self.startup_attempted = True
            style = Personality(public_mode=self.config.get('personality', 'public_mode', fallback='clean'),
                                allow_public_profanity=self.config.getboolean(
                                    'personality', 'allow_public_profanity', fallback=False))
            text = self.config.get('startup', 'message', fallback='').strip() or style.message('welcome', public=True)
            self.announce(self.config.getint('startup', 'channel', fallback=0), text, local=True)
            logging.info('Startup broadcast submitted (delivery unconfirmed).')
            return True
        except Exception:
            logging.exception('Startup broadcast failed; BBS remains available.')
            return False

    def command(self, message, sender):
        command, _, argument = message.strip().partition(' ')
        command = command.casefold()
        if command == '/weather':
            return self.weather.report()
        if command == '/wire':
            return self.mqtt.report()
        if command == '/node':
            if not argument.strip():
                return "Who's Who: /node <ID, short name or long name>"
            results = lookup_nodes(self.interface.nodes, argument)
            if not results:
                return 'No matching nodes in the radio database.'
            return '\n\n'.join(format_node(row) for row in results[:3]) + (
                f'\n{len(results)} matches; refine your search.' if len(results) > 3 else '')
        if command == '/announce':
            if not self.is_admin(sender):
                return 'Announcements require a configured administrator node.'
            channel, _, text = argument.partition(' ')
            try:
                return self.announce(int(channel), text, sender=sender)
            except ValueError as exc:
                return f'{exc}\nUsage: /announce <channel index> <message>'
            except Exception:
                logging.exception('Announcement send failed')
                return 'Radio send failed; announcement delivery unconfirmed.'
        return None
