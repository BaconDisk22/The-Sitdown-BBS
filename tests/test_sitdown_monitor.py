import queue
import time
import unittest
from unittest.mock import Mock

from sitdown_monitor import ServerSupervisor, NODE_PATTERN, READY_PATTERN


class SupervisorTests(unittest.TestCase):
    def test_log_patterns(self):
        self.assertIsNotNone(READY_PATTERN.search("INFO - TC²-BBS is running on serial interface..."))
        result = NODE_PATTERN.search("Received message from user 'JERZ' (!abcd1234) to BBS: hello")
        self.assertEqual(result.groups(), ("JERZ", "!abcd1234"))

    def test_queue_is_bounded_per_poll(self):
        supervisor = ServerSupervisor(["python", "server.py"], ".")
        for i in range(5):
            supervisor.events.put(("log", str(i)))
        self.assertEqual(len(supervisor.poll_events(limit=2)), 2)
        self.assertEqual(len(supervisor.poll_events()), 3)

    def test_start_is_idempotent(self):
        fake = Mock()
        fake.poll.return_value = None
        fake.stdout = iter([])
        factory = Mock(return_value=fake)
        supervisor = ServerSupervisor(["python", "server.py"], ".", factory=factory)
        self.assertTrue(supervisor.start())
        self.assertFalse(supervisor.start())
        factory.assert_called_once()

    def test_observed_rx_updates_activity_and_node(self):
        fake = Mock()
        fake.poll.return_value = None
        fake.stdout = iter(["INFO - Received message from user 'JERZ' (!abcd1234) to BBS: hello\n"])
        supervisor = ServerSupervisor(["python", "server.py"], ".", factory=Mock(return_value=fake))
        self.assertTrue(supervisor.start())
        # The reader runs on a daemon thread; wait briefly for its completion.
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and supervisor.last_rx_at is None:
            time.sleep(0.01)
        self.assertIsNotNone(supervisor.last_rx_at)
        self.assertIn("!abcd1234", supervisor.nodes)
        self.assertIn(("activity", "rx"), supervisor.poll_events())

    def test_restart_resets_stale_radio_activity(self):
        first = Mock()
        first.poll.return_value = 1
        first.stdout = iter([])
        second = Mock()
        second.poll.return_value = None
        second.stdout = iter([])
        factory = Mock(side_effect=[first, second])
        supervisor = ServerSupervisor(["python", "server.py"], ".", factory=factory)
        supervisor.start()
        supervisor.last_rx_at = time.time()
        supervisor.nodes["!abcd1234"] = ("JERZ", time.time())
        self.assertTrue(supervisor.start())
        self.assertIsNone(supervisor.last_rx_at)
        self.assertEqual(supervisor.nodes, {})

    def test_transport_error_and_traffic_counters(self):
        fake = Mock()
        fake.poll.return_value = None
        fake.stdout = iter([
            "INFO - Received message from user 'JERZ' (!abcd1234) to BBS: hi\\n",
            "Sending message to user !abcd1234\\n",
            "OSError: [Errno 65] No route to host\\n",
        ])
        supervisor = ServerSupervisor(["python", "server.py"], ".", factory=Mock(return_value=fake))
        supervisor.start()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and supervisor.last_link_error is None:
            time.sleep(0.01)
        self.assertEqual(supervisor.rx_count, 1)
        self.assertEqual(supervisor.tx_count, 1)
        self.assertIn("No route to host", supervisor.last_link_error)
        self.assertTrue(any(kind == "link_error" for kind, _ in supervisor.poll_events()))
        fake.poll.return_value = 1
        supervisor.start()
        self.assertEqual(supervisor.rx_count, 0)
        self.assertEqual(supervisor.tx_count, 0)
        self.assertIsNone(supervisor.last_link_error)

    def test_uptime_when_stopped(self):
        supervisor = ServerSupervisor(["python"], ".")
        self.assertEqual(supervisor.uptime_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
