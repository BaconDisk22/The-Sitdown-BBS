"""Non-transmitting, opt-in send preflight; cannot publish or call radio SDK."""
from sitdown_send_guard import SendPermission, can_send


def send_preflight(*, enabled=False, confirmed=False, radio_ready=False,
                   demo_mode=False, message=""):
    if not isinstance(message, str):
        return False, "Message must be text"
    if len(message.encode('utf-8')) > 200:
        return False, "Message exceeds 200 UTF-8 bytes"
    permission = SendPermission(enabled, confirmed, radio_ready, demo_mode)
    if demo_mode:
        return False, "Demo mode: transmissions disabled"
    if not enabled:
        return False, "Transmission opt-in disabled"
    if not confirmed:
        return False, "Operator confirmation required"
    if not radio_ready:
        return False, "Radio connection not verified"
    if not can_send(permission, message):
        return False, "Message must not be empty"
    return True, "Eligible for operator-initiated send; no message sent"
