"""Read-only operator status must not imply end-to-end delivery."""
import unittest
from sitdown_status_view import format_operator_status


class OperatorStatusInvariantTests(unittest.TestCase):
    def test_all_observation_pairs_leave_delivery_unverified(self):
        states = ("disabled", "unverified", "reachable", "connected", "error")
        for radio in states:
            for mqtt in states:
                with self.subTest(radio=radio, mqtt=mqtt):
                    output = format_operator_status(radio, mqtt)
                    self.assertIn("Radio: " + radio, output)
                    self.assertIn("MQTT monitor: " + mqtt, output)
                    self.assertIn("Two-way: Unverified", output)

    def test_invalid_state_is_rejected(self):
        with self.assertRaises(ValueError):
            format_operator_status("transmitting", "connected")


if __name__ == "__main__":
    unittest.main()
