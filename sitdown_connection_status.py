"""Credential-free operator status snapshots; observations are not delivery proof.

This module never opens a socket, publishes MQTT, or sends radio packets.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class Observation:
    state: str
    observed_at: Optional[datetime] = None
    detail: str = ""

    def __post_init__(self):
        if self.state not in {"disabled", "unverified", "reachable", "connected", "error"}:
            raise ValueError("unsupported observation state")
        if self.observed_at is not None and self.observed_at.tzinfo is None:
            raise ValueError("observation timestamps must be timezone-aware")


def describe_status(radio: Observation, mqtt: Observation, *, live_delivery_verified=False):
    """Return a safe status summary for UI or logs.

    'connected' means an observed connection, not verified delivery.
    No automatic inference of two-way delivery from radio/MQTT state.
    """
    if live_delivery_verified is not False:
        raise ValueError("delivery verification requires separate audited evidence")
    def entry(obs):
        return {
            "state": obs.state,
            "last_observed_utc": (
                obs.observed_at.astimezone(timezone.utc).isoformat()
                if obs.observed_at else None
            ),
            "detail": obs.detail,
        }
    return {
        "radio": entry(radio),
        "mqtt_monitor": entry(mqtt),
        "two_way_delivery": "Unverified — requires a live end-to-end radio test",
    }
