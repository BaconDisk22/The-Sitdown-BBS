import unittest
from sitdown_send_guard import SendPermission, can_send


class SendGuardTests(unittest.TestCase):
    def test_default_denied(self):
        self.assertFalse(can_send(SendPermission(), "hello"))

    def test_explicit_confirmation_required(self):
        self.assertFalse(can_send(SendPermission(enabled=True, radio_ready=True), "hello"))

    def test_demo_never_sends(self):
        self.assertFalse(can_send(SendPermission(True, True, True, True), "hello"))

    def test_empty_message_denied(self):
        self.assertFalse(can_send(SendPermission(True, True, True), "  "))

    def test_all_conditions_required(self):
        self.assertTrue(can_send(SendPermission(True, True, True), "hello"))
