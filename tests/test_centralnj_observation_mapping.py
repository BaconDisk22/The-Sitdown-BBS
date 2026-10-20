import unittest
from sitdown_status_view import format_operator_status


class ObservationTests(unittest.TestCase):
    def test_connected_still_unverified_delivery(self):
        self.assertIn("Unverified", format_operator_status("connected", "connected"))

    def test_disconnected_radio_is_error(self):
        self.assertIn("Radio: error", format_operator_status("error", "disabled"))
