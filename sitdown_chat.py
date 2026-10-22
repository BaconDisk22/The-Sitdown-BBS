"""Receive-only radio channel chat for the desktop.

Channel (broadcast) text messages heard by the BBS radio are passed to the
desktop for display. Direct messages stay with the BBS command handler.
Nothing here transmits.
"""
import time
from collections import deque

BROADCAST = 0xFFFFFFFF
MAX_TEXT = 500
MAX_CHANNELS = 8


def chat_event(packet, interface, clock=time.time):
    """Return a desktop chat event for a channel text message, or None."""
    try:
        decoded = packet['decoded']
        if decoded.get('portnum') != 'TEXT_MESSAGE_APP' or packet.get('to') != BROADCAST:
            return None
        text = bytes(decoded['payload']).decode('utf-8', errors='replace')[:MAX_TEXT]
        channel = int(packet.get('channel', 0))
        sender = packet.get('fromId') or f"!{int(packet['from']):08x}"
    except (KeyError, TypeError, ValueError):
        return None
    if not 0 <= channel < MAX_CHANNELS:
        return None
    nodes = getattr(interface, 'nodes', None) or {}
    user = (nodes.get(sender) or {}).get('user') or {}
    mine = packet.get('from') == getattr(getattr(interface, 'myInfo', None), 'my_node_num', None)
    return {'type': 'chat', 'channel': channel, 'from': sender,
            'short': str(user.get('shortName', '')), 'long': str(user.get('longName', '')),
            'text': text, 'rx_time': int(packet.get('rxTime') or clock()), 'mine': mine}


def format_message(event):
    stamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(event['rx_time']))
    who = ' '.join(part for part in (event['short'], f"({event['long']})" if event['long'] else '') if part)
    who = 'You' if event['mine'] else (who + ' ' if who else '') + event['from']
    return f"{stamp}  {who}\n    {event['text']}"


class ChatLog:
    """Bounded in-memory history per radio channel for this session."""

    def __init__(self, limit=200):
        self.limit = limit
        self._messages = {}

    def add(self, event):
        try:
            channel = int(event['channel'])
            valid = (event.get('type') == 'chat' and 0 <= channel < MAX_CHANNELS
                     and isinstance(event.get('text'), str) and isinstance(event.get('from'), str))
        except (KeyError, TypeError, ValueError):
            return False
        if not valid:
            return False
        self._messages.setdefault(channel, deque(maxlen=self.limit)).append(event)
        return True

    def channels(self):
        return sorted(self._messages)

    def messages(self, channel):
        return list(self._messages.get(channel, ()))

    def render(self, channel, name):
        rows = self.messages(channel)
        header = (f'{name} — channel messages your radio heard this session (last {len(rows)}).\n'
                  'Receive-only for now. Direct messages to the BBS are handled by the BBS.\n\n')
        if not rows:
            return header + 'No messages yet. Start the BBS server to listen on this channel.'
        return header + '\n'.join(format_message(row) for row in rows)
