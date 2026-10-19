"""Track the SDK radio session separately from BBS process health."""
import json
import time

PREFIX = "SITDOWN_LINK "


class RadioLinkMonitor:
    """Allow SDK recovery, then exit a disconnected session for supervision.

    The SDK flag confirms its protocol handshake, not continuous reachability
    or delivery to another mesh node. Silence alone is never a disconnect.
    """
    def __init__(self, interface, grace_seconds=30, clock=time.monotonic, emit=None):
        self.interface = interface
        self.grace_seconds = grace_seconds
        self.clock = clock
        self.emit = emit or (lambda value: print(PREFIX + json.dumps(value), flush=True))
        self.lost_at = None
        self.last_state = None

    def check(self):
        connected = self.interface.isConnected.is_set()
        state = "sdk_connected" if connected else "disconnected"
        now = self.clock()
        if connected:
            self.lost_at = None
        elif self.lost_at is None:
            self.lost_at = now
        if state != self.last_state:
            self.emit({"state": state})
            self.last_state = state
        return not connected and now - self.lost_at >= self.grace_seconds
