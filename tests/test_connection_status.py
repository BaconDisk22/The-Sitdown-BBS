import unittest
from datetime import datetime, timezone
from sitdown_connection_status import Observation, describe_status


class StatusTests(unittest.TestCase):
    def test_never_conflates_connectivity_with_delivery(self):
        now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        result = describe_status(Observation("connected", now), Observation("connected", now))
        self.assertIn("Unverified", result["two_way_delivery"])
        self.assertEqual(result["radio"]["last_observed_utc"], now.isoformat())

    def test_missing_observations_stay_unknown(self):
        result = describe_status(Observation("unverified"), Observation("disabled"))
        self.assertIsNone(result["radio"]["last_observed_utc"])
        self.assertEqual(result["mqtt_monitor"]["state"], "disabled")

    def test_refuses_unsubstantiated_delivery_claim(self):
        with self.assertRaises(ValueError):
            describe_status(Observation("connected"), Observation("connected"), live_delivery_verified=True)

    def test_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            Observation("connected", datetime(2026, 1, 1))

    def test_rejects_unknown_state(self):
        with self.assertRaises(ValueError):
            Observation("transmitting")


if __name__ == "__main__":
    unittest.main()
