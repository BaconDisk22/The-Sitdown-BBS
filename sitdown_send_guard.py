"""Side-effect-free transmission gate; default deny, never sends messages."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SendPermission:
    enabled: bool = False
    operator_confirmed: bool = False
    radio_ready: bool = False
    demo_mode: bool = False


def can_send(permission: SendPermission, message: str) -> bool:
    return bool(
        permission.enabled
        and permission.operator_confirmed
        and permission.radio_ready
        and not permission.demo_mode
        and isinstance(message, str)
        and bool(message.strip())
    )
