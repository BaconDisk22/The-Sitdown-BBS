"""Explicitly gated MQTT retry state; does not schedule or open connections."""
from dataclasses import dataclass
from sitdown_mqtt_retry import retry_delay, should_retry


@dataclass
class RecoveryState:
    enabled: bool = False
    stopped: bool = False
    attempts: int = 0

    def next_delay(self):
        if not should_retry(enabled=self.enabled, user_stopped=self.stopped,
                            attempt=self.attempts):
            return None
        delay = retry_delay(self.attempts)
        self.attempts += 1
        return delay

    def connected(self):
        self.attempts = 0

    def stop(self):
        self.stopped = True
