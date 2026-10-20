"""Pure MQTT retry policy; does not create connections or start retries."""
def retry_delay(attempt, *, base=2, cap=120):
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 0:
        raise ValueError("attempt must be a nonnegative integer")
    if base <= 0 or cap < base:
        raise ValueError("invalid retry bounds")
    return min(cap, base * (2 ** min(attempt, 32)))


def should_retry(*, enabled, user_stopped, attempt, max_attempts=5):
    if not isinstance(attempt, int) or attempt < 0 or max_attempts < 0:
        raise ValueError("invalid retry count")
    return bool(enabled and not user_stopped and attempt < max_attempts)
