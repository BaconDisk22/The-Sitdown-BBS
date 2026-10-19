"""Desktop regressions; real-window checks run on the Intel macOS build runner."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

import sitdown_desktop as desktop


class DesktopTests(unittest.TestCase):
    def test_connection_summary_has_real_line_break_for_both_transports(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.connection_summary = Mock()
        app.address = Mock()
        app.address.get.return_value = " 10.0.0.76 "
        app.connection = Mock()
        for transport, name in (("tcp", "TCP / Network"), ("serial", "USB / Serial")):
            app.connection.get.return_value = transport
            app.refresh_connection_summary()
            self.assertEqual(app.connection_summary.set.call_args.args[0].splitlines(),
                             [f"Configured: {name}", "Endpoint: 10.0.0.76"])

    def test_start_passes_transport_and_endpoint_and_stop_cancels_restart(self):
        for transport, flag, address in (("tcp", "--host", "10.0.0.76"),
                                         ("serial", "--port", "/dev/cu.usbmodem1")):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "config.ini").touch()
                app = desktop.SitdownApp.__new__(desktop.SitdownApp)
                app.supervisor = None
                app.demo = Mock(get=Mock(return_value=False))
                app.connection = Mock(get=Mock(return_value=transport))
                app.address = Mock(get=Mock(return_value=address))
                app.status = Mock()
                app.uptime = Mock()
                app.traffic = Mock()
                app.link_warning = Mock()
                app.save = Mock()
                app.log = Mock()
                with patch.object(desktop, "ROOT", root), patch.object(desktop, "DATA", root), \
                     patch.object(desktop, "ServerSupervisor") as factory:
                    app.start()
                    args = factory.call_args.args[0]
                    self.assertEqual(args[-4:], ["--interface-type", transport, flag, address])
                    monitor = factory.return_value
                    monitor.start.assert_called_once()
                    app.restart_at = 100
                    app.retry_count = 2
                    app.stop()
                    monitor.stop.assert_called_once()
                    self.assertIsNone(app.restart_at)
                    self.assertIsNone(app.supervisor)
                    app.status.set.assert_called_with("Stopped")

    def test_recovery_backoff_is_capped_and_opt_in(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.auto_restart = Mock(get=Mock(return_value=True))
        app.demo = Mock(get=Mock(return_value=False))
        app.retry_count = 0
        app.status = Mock()
        app.log = Mock()
        with patch.object(desktop.time, "monotonic", return_value=100):
            for delay in (2, 4, 8, 16, 32, 60, 60):
                app.schedule_recovery()
                self.assertEqual(app.restart_at, 100 + delay)
        app.restart_at = None
        app.auto_restart.get.return_value = False
        app.schedule_recovery()
        self.assertIsNone(app.restart_at)

    def test_tx_event_does_not_claim_rx_and_disabling_recovery_cancels_timer(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.supervisor = Mock(running=True, last_rx_at=None, link_state="unverified",
                              rx_count=0, tx_count=1)
        app.supervisor.poll_events.return_value = [("activity", "tx")]
        for name in ("radio_activity", "traffic", "uptime", "status", "root", "link_warning"):
            setattr(app, name, Mock())
        app.auto_restart = Mock(get=Mock(return_value=False))
        app.demo = Mock(get=Mock(return_value=False))
        app.restart_at = 1
        app.start = Mock()
        app.poll()
        app.radio_activity.set.assert_not_called()
        app.start.assert_not_called()
        self.assertIsNone(app.restart_at)


@unittest.skipUnless(os.environ.get("SITDOWN_UI_TESTS") == "1", "requires a GUI session")
class DesktopWindowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config_patch = patch.object(desktop, "CONFIG", Path(self.directory.name) / "launcher.json")
        self.config_patch.start()
        self.root = tk.Tk()
        self.app = desktop.SitdownApp(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.config_patch.stop()
        self.directory.cleanup()

    def test_all_navigation_controls_fit_after_resize_and_larger_fonts(self):
        for size in (12, 18):
            for control in self.app.nav_buttons:
                control.configure(font=("Helvetica", size, "bold"))
            for width, height in ((1120, 740), (1280, 900), (1600, 1000), (1120, 740)):
                self.root.geometry(f"{width}x{height}")
                self.root.update()
                nav = self.app.navigation
                for control in self.app.nav_buttons:
                    with self.subTest(size=size, width=width, title=control.cget("text")):
                        self.assertTrue(control.winfo_ismapped())
                        self.assertGreaterEqual(control.winfo_x(), 0)
                        self.assertLessEqual(control.winfo_x() + control.winfo_width(), nav.winfo_width())
                        self.assertLessEqual(control.winfo_y() + control.winfo_height(), nav.winfo_height())
        for title in ("SETTINGS", "ABOUT"):
            control = next(c for c in self.app.nav_buttons if c.cget("text").split()[-1] == title)
            control.event_generate("<Button-1>")
            self.root.update()
            windows = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
            self.assertTrue(windows, title)
            for window in windows:
                window.destroy()

    def test_info_is_themed_nonblocking_and_keyboard_dismissible(self):
        for key in ("<Escape>", "<Return>", "<space>"):
            win = self.app.show_info("Radio Connection", "First line\nSecond line")
            self.root.update()
            self.assertEqual(win.cget("bg"), desktop.THEME["background"])
            self.assertEqual(str(win.transient()), str(self.root))
            self.assertIsNone(self.root.grab_current())
            ran = []
            self.root.after(0, lambda: ran.append(True))
            self.root.update()
            self.assertTrue(ran)
            control = next(w for w in win.winfo_children() if isinstance(w, tk.Label) and w.cget("text") == "OK")
            control.focus_force()
            self.root.update()
            control.event_generate(key)
            self.root.update()
            self.assertFalse(win.winfo_exists())
