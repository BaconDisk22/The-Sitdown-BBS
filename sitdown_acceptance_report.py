"""Offline hardware acceptance record; never claims tests were run."""
from datetime import datetime, timezone


VALID = {"not_run", "transport_reachable", "protocol_connected", "two_way_verified"}


def acceptance_record(result="not_run", *, evidence="", observed_at=None):
    if result not in VALID:
        raise ValueError("unknown acceptance result")
    if not isinstance(evidence, str):
        raise ValueError("evidence must be text")
    if len(evidence.encode("utf-8")) > 4096:
        raise ValueError("evidence exceeds 4096 bytes")
    if result == "two_way_verified" and not evidence.strip():
        raise ValueError("independent two-way delivery evidence required")
    if observed_at is not None and (
        not isinstance(observed_at, datetime) or observed_at.tzinfo is None
    ):
        raise ValueError("timestamp must be timezone-aware")
    return {"result": result, "evidence": evidence,
            "observed_at_utc": (observed_at.astimezone(timezone.utc).isoformat()
                                if observed_at else None)}
