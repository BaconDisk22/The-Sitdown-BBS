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

    def test_recovery_backoff_is_opt_in_and_capped(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.auto_restart = Mock(get=Mock(return_value=True))
        app.demo = Mock(get=Mock(return_value=False))
        app.log = Mock()
        app.status = Mock()
        app.retry_count = 0
        app.restart_at = None
        with patch.object(desktop.time, "monotonic", return_value=100):
            for attempt in range(1, 9):
                app.schedule_recovery()
                self.assertEqual(app.retry_count, attempt)
                self.assertEqual(app.restart_at, 100 + min(60, 2 ** min(attempt, 6)))
        app.auto_restart.get.return_value = False
        app.restart_at = None
        app.schedule_recovery()
        self.assertIsNone(app.restart_at)
        app.auto_restart.get.return_value = True
        app.demo.get.return_value = True
        app.schedule_recovery()
        self.assertIsNone(app.restart_at)

    def test_explicit_stop_cancels_pending_recovery(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.restart_at = 200
        app.retry_count = 4
        app.supervisor = None
        app.status = Mock()
        app.radio_activity = Mock()
        app.uptime = Mock()
        app.link_warning = Mock()
        app.log = Mock()
        app.stop()
        self.assertIsNone(app.restart_at)
        self.assertEqual(app.retry_count, 0)

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
            self.assertIsNotNone(self.app.active_page)
            self.assertTrue(self.app.active_page.winfo_ismapped())

    def test_each_page_opens_in_demo_and_returns_home(self):
        self.app.demo.set(True)
        self.app.start()
        for title in ('BBS', 'MESSAGES', 'BOARDS', 'RADIO', 'NODES', 'SETTINGS', 'ABOUT'):
            self.app.select_page(title)
            self.root.update()
            self.assertTrue(self.app.active_page.winfo_ismapped())
        self.app.select_page('HOME')
        self.root.update()
        self.assertTrue(self.app.home_page.winfo_ismapped())
        with patch.object(self.app, 'show_info'):
            self.app.supervisor = Mock()
            self.app.control_request('announce', channel=0, text='Demo')
            self.app.supervisor.request.assert_not_called()

    def test_settings_save_preserves_existing_config_and_validates(self):
        path = Path(self.directory.name) / 'config.ini'
        path.write_text('[interface]\ntype = tcp\nhostname = 192.0.2.10\n[menu]\nmain_menu_items = B,X\n')
        with patch.object(self.app, 'config_path', return_value=path), patch.object(self.app, 'show_info'):
            self.app.select_page('SETTINGS')
            self.root.update()
            fields = self.app.setting_fields
            fields[('startup', 'enabled')].set(True)
            fields[('startup', 'message')].set('Hello Jersey')
            button = next(w for w in self.app.active_page.winfo_children()
                          if isinstance(w, tk.Label) and w.cget('text').startswith('SAVE'))
            button.event_generate('<Button-1>')
            config = self.app.read_config()
            self.assertEqual(config.get('interface', 'hostname'), '192.0.2.10')
            self.assertEqual(config.get('menu', 'main_menu_items'), 'B,X')
            self.assertTrue(config.getboolean('startup', 'enabled'))
            self.assertEqual(config.get('startup', 'message'), 'Hello Jersey')
            original = path.read_text()
            fields[('startup', 'channel')].set('99')
            button.event_generate('<Button-1>')
            self.assertEqual(path.read_text(), original)

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
