#!/usr/bin/env python3
"""The Sitdown BBS desktop launcher. Standard-library Tkinter GUI."""
import json
import runpy
import shutil
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from sitdown_monitor import ServerSupervisor
from sitdown_personality import Personality
import zipfile

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA = Path.home() / ".sitdown-bbs"
CONFIG = DATA / "launcher.json"
THEME = {"background": "#121212", "panel": "#242424", "primary": "#C62828",
         "connected": "#008C45", "text": "#F5F5F0", "highlight": "#F4B942"}
COMMANDS = [
    ("/sitdown", "Main menu"), ("/help", "Quick help"),
    ("/mail", "Check your mail"), ("/boards", "The Social Club"),
    ("/fortune", "Jersey wisdom"), ("/tools", "Utilities"),
    ("/cancel", "Return to main menu"),
]


class SitdownApp:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.supervisor = None
        self.restart_at = None
        self.retry_count = 0
        self.auto_restart = tk.BooleanVar(value=False)
        self.node_count = tk.StringVar(value='Observed nodes: 0')
        self.uptime = tk.StringVar(value='Uptime: 0s')
        self.radio_activity = tk.StringVar(value='Radio activity: Not observed')
        self.traffic = tk.StringVar(value='Messages observed: RX 0 / TX 0')
        self.link_warning = tk.StringVar(value='TCP health: Not checked')
        self.demo = tk.BooleanVar(value=False)
        self.connection = tk.StringVar(value="serial")
        self.address = tk.StringVar()
        self.community = tk.StringVar(value="The Sitdown BBS")
        self.welcome = tk.StringVar(value="Ayyy, pull up a chair. We gotta talk.")
        self.desktop_mouth = tk.StringVar(value="clean")
        self.public_mouth = tk.StringVar(value="clean")
        self.public_profanity = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Stopped")
        self.colors = THEME
        self.root.title("THE SITDOWN BBS | North Jersey Communications Division")
        self.root.geometry("1280x900")
        self.root.minsize(960, 650)
        self.root.configure(bg=THEME["background"])
        self.load()
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(1000, self.poll)

    def load(self):
        if CONFIG.exists():
            try:
                data = json.loads(CONFIG.read_text(encoding="utf-8"))
                self.connection.set(data.get("connection", "serial"))
                self.address.set(data.get("address", ""))
                self.community.set(data.get("community", "The Sitdown BBS"))
                self.welcome.set(data.get("welcome", self.welcome.get()))
                desktop_mode = data.get("desktop_mouth", "clean")
                public_mode = data.get("public_mouth", "clean")
                enabled = data.get("public_profanity", False) is True
                Personality(desktop_mode, public_mode, enabled)
                self.desktop_mouth.set(desktop_mode)
                self.public_mouth.set(public_mode)
                self.public_profanity.set(enabled)
            except (ValueError, OSError):
                pass

    def save(self):
        try:
            Personality(self.desktop_mouth.get(), self.public_mouth.get(), self.public_profanity.get())
        except ValueError as exc:
            messagebox.showerror("Invalid Jersey Mouth setting", str(exc))
            return
        DATA.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({
            "connection": self.connection.get(), "address": self.address.get(),
            "community": self.community.get(), "welcome": self.welcome.get(),
            "desktop_mouth": self.desktop_mouth.get(),
            "public_mouth": self.public_mouth.get(),
            "public_profanity": self.public_profanity.get()
        }, indent=2), encoding="utf-8")
        self.log("The Family Business: settings saved.")
        self.log(Personality(self.desktop_mouth.get(), self.public_mouth.get(), self.public_profanity.get()).message("welcome"))

    def build(self):
        c = self.colors
        def label(parent, text, size=11, color=None):
            return tk.Label(parent, text=text, font=("Helvetica", size, "bold"),
                            fg=color or c["text"], bg=c["background"])
        button = self.styled_button
        # A single full-width banner keeps the skyline and title together on Intel Macs.
        header = tk.Frame(self.root, bg="#071017")
        header.pack(fill="x", padx=18, pady=(8, 4))
        skyline = tk.Canvas(header, height=112, bg="#071017",
                            highlightthickness=0, bd=0)
        skyline.pack(fill="x", expand=True)
        skyline.bind("<Configure>", lambda event: self.draw_skyline(
            skyline, event.width, event.height))
        navigation = tk.Frame(self.root, bg=c["panel"], pady=7)
        navigation.pack(fill="x", padx=18, pady=(0, 7))
        self.navigation = navigation
        self.nav_buttons = []
        for title, action in [
            ("⌂  HOME", self.show_home),
            ("▣  BBS", self.commands),
            ("✉  MESSAGES", lambda: self.show_command_info("/mail")),
            ("▤  BOARDS", lambda: self.show_command_info("/boards")),
            ("◉  RADIO", self.show_radio),
            ("◎  NODES", self.show_nodes),
            ("⚙  SETTINGS", self.settings),
            ("ⓘ  ABOUT", self.show_about),
        ]:
            control = self.styled_button(
                navigation, title, action,
                c["primary"] if "HOME" in title else c["background"],
                compact=True)
            self.nav_buttons.append(control)
        navigation.bind("<Configure>", self.layout_navigation)
        tk.Frame(self.root, bg=c["connected"], height=4).pack(fill="x", padx=18)
        tk.Frame(self.root, bg=c["primary"], height=4).pack(fill="x", padx=18, pady=(3, 0))
        label(self.root, "Ayyy, pull up a chair. We gotta talk.", 12, c["highlight"]).pack(pady=(2, 10))
        cards = tk.Frame(self.root, bg=c["background"])
        cards.pack(fill="x", padx=18, pady=(0, 4))
        for column in range(3):
            cards.grid_columnconfigure(column, weight=1, uniform="jersey")

        def card(column, title):
            frame = tk.Frame(cards, bg=c["panel"], padx=10, pady=7,
                             highlightbackground="#24404A", highlightthickness=1)
            frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=4)
            tk.Label(frame, text=title, bg=c["panel"], fg=c["highlight"],
                     font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 5))
            return frame

        radio = card(0, "◉  CONNECTION STATUS")
        tk.Radiobutton(radio, text="USB / Serial", variable=self.connection, value="serial",
                       bg=c["panel"], fg=c["text"], selectcolor=c["background"]).pack(anchor="w")
        tk.Radiobutton(radio, text="TCP / Network", variable=self.connection, value="tcp",
                       bg=c["panel"], fg=c["text"], selectcolor=c["background"]).pack(anchor="w")
        tk.Label(radio, text="Device path or radio IP", bg=c["panel"], fg=c["text"]).pack(anchor="w", pady=(10, 2))
        tk.Entry(radio, textvariable=self.address, bg=c["background"], fg=c["text"],
                 insertbackground=c["text"], relief="flat").pack(fill="x", ipady=7)
        self.styled_button(radio, "Find USB Ports", self.list_ports, c["background"]).pack(
            anchor="w", pady=(10, 0))
        self.connection_summary = tk.StringVar()
        tk.Label(radio, textvariable=self.connection_summary, bg=c["panel"],
                 fg=c["text"], justify="left", wraplength=280).pack(anchor="w", pady=(8, 0))
        self.connection.trace_add("write", self.refresh_connection_summary)
        self.address.trace_add("write", self.refresh_connection_summary)
        self.refresh_connection_summary()
        tk.Label(radio, text="Process status does not confirm a radio link.",
                 bg=c["panel"], fg=c["highlight"], wraplength=275,
                 justify="left").pack(anchor="w", pady=(10, 0))

        server = card(1, "▣  BBS SERVER")
        self.status_row = tk.Frame(server, bg=c["panel"])
        self.status_row.pack(fill="x", pady=(0, 8))
        self.status_dot = tk.Label(self.status_row, text="●", bg=c["panel"],
                                   fg=c["primary"], font=("Helvetica", 16, "bold"))
        self.status_dot.pack(side="left", padx=(0, 6))
        tk.Label(self.status_row, textvariable=self.status, bg=c["panel"],
                 fg=c["text"], wraplength=230, justify="left").pack(side="left")
        self.status.trace_add("write", self.refresh_status_indicator)
        self.refresh_status_indicator()
        tk.Label(server, textvariable=self.radio_activity, bg=c["panel"], fg=c["highlight"], wraplength=250).pack(anchor="w")
        tk.Label(server, textvariable=self.node_count, bg=c["panel"], fg=c["text"]).pack(anchor="w")
        tk.Label(server, textvariable=self.traffic, bg=c["panel"], fg=c["text"]).pack(anchor="w")
        tk.Label(server, textvariable=self.link_warning, bg=c["panel"], fg=c["highlight"], wraplength=260).pack(anchor="w")
        tk.Label(server, textvariable=self.uptime, bg=c["panel"], fg=c["text"]).pack(anchor="w", pady=(4, 10))
        self.styled_button(server, "START THE SITDOWN", self.start, c["connected"]).pack(fill="x", pady=3)
        self.styled_button(server, "STOP SERVER", self.stop, c["primary"]).pack(fill="x", pady=3)
        self.styled_button(server, "RESTART SERVER", self.restart, c["background"]).pack(fill="x", pady=3)
        tk.Checkbutton(server, text="Demo mode (no radio)", variable=self.demo,
                       bg=c["panel"], fg=c["text"], selectcolor=c["background"]).pack(anchor="w", pady=(8, 0))
        tk.Checkbutton(server, text="Recover after crash / disconnect", variable=self.auto_restart,
                       bg=c["panel"], fg=c["text"], selectcolor=c["background"]).pack(anchor="w")

        personality = card(2, "◈  JERSEY PERSONALITY")
        tk.Label(personality, text="Desktop greeting style", bg=c["panel"],
                 fg=c["text"]).pack(anchor="w")
        for title, mode in (("Clean Jersey", "clean"), ("Jersey Attitude", "attitude"),
                            ("Full Jersey Mouth", "uncensored")):
            tk.Radiobutton(personality, text=title, variable=self.desktop_mouth, value=mode,
                           bg=c["panel"], fg=c["text"],
                           selectcolor=c["background"]).pack(anchor="w")
        self.styled_button(personality, "SAVE SETTINGS", self.save, c["connected"]).pack(
            fill="x", pady=(12, 4))
        self.styled_button(personality, "THE FAMILY BUSINESS", self.settings,
                           c["background"]).pack(fill="x", pady=4)
        tk.Label(personality, text="Public radio style is configured separately. "
                 "These options do not change radio replies yet.",
                 bg=c["panel"], fg=c["highlight"], wraplength=285,
                 justify="left").pack(anchor="w", pady=(8, 0))

        tools = tk.Frame(self.root, bg=c["background"])
        tools.pack(fill="x", padx=23, pady=(0, 4))
        for title, action in (("THE PLAYBOOK", self.commands),
                              ("THE BOOKS", self.backup), ("WHO'S WHO", self.show_nodes)):
            self.styled_button(tools, title, action, c["panel"]).pack(side="left", padx=(0, 8))
        log_header = tk.Frame(self.root, bg=c["panel"], padx=12, pady=9,
                              highlightbackground="#24404A", highlightthickness=1)
        log_header.pack(fill="x", padx=20, pady=(10, 0))
        label(log_header, "▤  SERVER LOG  •  THE BACKROOM", 12, c["highlight"]).pack(side="left")
        button(log_header, "Save Log", self.export_log, c["panel"]).pack(side="right", padx=(8, 0))
        button(log_header, "Copy Diagnostics", self.copy_diagnostics, c["panel"]).pack(
            side="right", padx=(8, 0))
        button(log_header, "Clear Log", self.clear_log, c["panel"]).pack(side="right")
        button(log_header, "Nodes", self.show_nodes, c["panel"]).pack(side="right", padx=(0, 8))
        self.log_query = tk.StringVar()
        search_row = tk.Frame(self.root, bg=c["panel"], padx=12, pady=7)
        search_row.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(search_row, text="SEARCH LOG", bg=c["panel"], fg=c["highlight"],
                 font=("Helvetica", 10, "bold")).pack(side="left")
        tk.Entry(search_row, textvariable=self.log_query, bg=c["panel"], fg=c["text"],
                 insertbackground=c["text"], relief="flat").pack(side="left", fill="x", expand=True, padx=8)
        button(search_row, "Find Next", self.find_log, c["panel"]).pack(side="right")


        # Read-only footer: process status is not proof of a live radio link.
        footer = tk.Frame(self.root, bg=c["panel"], padx=14, pady=7,
                          highlightbackground="#24404A", highlightthickness=1)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 6))
        tk.Label(footer, text="THE SITDOWN BBS  •  NORTH JERSEY",
                 bg=c["panel"], fg=c["highlight"],
                 font=("Helvetica", 10, "bold")).pack(side="left")
        tk.Label(footer, textvariable=self.status, bg=c["panel"], fg=c["text"],
                 font=("Helvetica", 10)).pack(side="right", padx=(14, 0))
        tk.Label(footer, text="SERVER PROCESS:", bg=c["panel"], fg=c["highlight"],
                 font=("Helvetica", 10, "bold")).pack(side="right")
        self.output = tk.Text(self.root, bg="#0B141A", fg=c["text"], insertbackground=c["text"],
                              wrap="word", relief="flat", state="disabled", height=7,
                              font=("Menlo", 11), padx=16, pady=12,
                              highlightbackground="#24404A", highlightthickness=1)
        self.output.pack(fill="both", expand=True, padx=20, pady=(5, 5))
        self.output.tag_configure("event_error", foreground="#FF8B85")
        self.output.tag_configure("event_ready", foreground="#82D9A0")
        self.log(Personality(self.desktop_mouth.get(), self.public_mouth.get(), self.public_profanity.get()).message("welcome"))
        self.log("Pick a radio, or check Demo mode.")

    def layout_navigation(self, event):
        """Wrap measured controls so every action survives font/window resizing."""
        cell_width = max(control.winfo_reqwidth() for control in self.nav_buttons) + 6
        columns = max(1, min(len(self.nav_buttons), event.width // cell_width))
        for index, control in enumerate(self.nav_buttons):
            row, column = divmod(index, columns)
            control.grid(row=row, column=column, sticky="ew", padx=3, pady=2)

    @staticmethod
    def draw_skyline(canvas, width, height):
        """Original vector skyline and suspension bridge, inspired by the app icon."""
        canvas.delete("all")
        def line(points, color, thickness=1):
            canvas.create_line(*[value * (width if i % 2 == 0 else height)
                                 for i, value in enumerate(points)],
                               fill=color, width=thickness)
        for index, top in enumerate((.48, .3, .55, .2, .4, .32, .5, .16, .38, .25, .52)):
            left = index / 11
            right = left + .065
            canvas.create_rectangle(left * width, top * height, right * width,
                                    .88 * height, fill="#10181D", outline="")
            for level in range(3):
                y = top + .1 + level * .12
                if y < .84:
                    line((left + .02, y, right - .02, y), "#A47D3D", 2)
        for tower in (.22, .78):
            line((tower, .12, tower, .9), "#C8C8BD", 3)
        cables = ((.02, .62), (.22, .18), (.5, .58), (.78, .18), (.98, .62))
        for (x1, y1), (x2, y2) in zip(cables, cables[1:]):
            line((x1, y1, x2, y2), "#C8C8BD", 2)
            for step in range(1, 6):
                t = step / 6
                x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                line((x, y, x, .88), "#64747B")
        line((0, .88, 1, .88), THEME["highlight"], 3)
        # Layer the identity over the skyline rather than shrinking it into a side panel.
        title_font = ("Helvetica", max(22, min(47, int(width / 24))), "bold")
        canvas.create_rectangle(0, height * .1, width, height * .88,
                                fill="#071017", stipple="gray50", outline="")
        canvas.create_text(width * .035, height * .35, text="THE",
                           fill="#F5F5F0", anchor="w",
                           font=("Helvetica", max(12, int(width / 58)), "bold"))
        canvas.create_text(width * .035, height * .59, text="SITDOWN",
                           fill="#008C45", anchor="w", font=title_font)
        canvas.create_text(width * .62, height * .59, text="BBS",
                           fill="#C62828", anchor="w", font=title_font)
        canvas.create_text(width * .038, height * .79,
                           text="NORTH JERSEY  •  COMMUNICATIONS DIVISION",
                           fill="#F5F5F0", anchor="w",
                           font=("Helvetica", max(9, min(13, int(width / 82))), "bold"))


    def show_info(self, title, message):
        """Non-blocking themed information window; server polling stays active."""
        previous_focus = self.root.focus_get()
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.configure(bg=self.colors["background"])
        win.resizable(False, False)
        tk.Frame(win, bg=self.colors["connected"], height=4).pack(fill="x")
        tk.Label(win, text=title, bg=self.colors["background"],
                 fg=self.colors["highlight"], font=("Helvetica", 16, "bold"),
                 wraplength=440, justify="left").pack(anchor="w", padx=22, pady=(18, 12))
        tk.Label(win, text=message, bg=self.colors["background"],
                 fg=self.colors["text"], font=("Helvetica", 12),
                 wraplength=440, justify="left").pack(anchor="w", padx=22, pady=(0, 18))
        def dismiss(_event=None):
            win.destroy()
            if previous_focus is not None and previous_focus.winfo_exists():
                previous_focus.focus_set()
            return "break"
        close = self.styled_button(win, "OK", dismiss, self.colors["primary"])
        close.pack(fill="x", padx=22, pady=(0, 18))
        win.bind("<Escape>", dismiss)
        win.bind("<Return>", dismiss)
        win.protocol("WM_DELETE_WINDOW", dismiss)
        win.update_idletasks()
        x = max(0, self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = max(0, self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_reqheight()) // 2)
        win.geometry(f"+{x}+{y}")
        close.focus_set()
        return win

    def refresh_connection_summary(self, *_args):
        """Display configured endpoint without claiming it is connected."""
        kind = "TCP / Network" if self.connection.get() == "tcp" else "USB / Serial"
        endpoint = self.address.get().strip() or "Not specified (auto/default)"
        self.connection_summary.set(f"Configured: {kind}\nEndpoint: {endpoint}")

    def refresh_status_indicator(self, *_args):
        """Color denotes BBS process state, not a verified radio link."""
        state = self.status.get().lower()
        if "demo" in state or "starting" in state or "retry" in state:
            color = THEME["highlight"]
        elif "running" in state or "initialized" in state:
            color = THEME["connected"]
        else:
            color = THEME["primary"]
        self.status_dot.configure(fg=color)

    def show_home(self):
        """Home is the main live dashboard."""
        self.log("HOME: Dashboard is already open.")

    def show_command_info(self, shortcut):
        """Show the actual radio command; do not imply desktop mail is implemented."""
        self.show_info("The Sitdown BBS — Radio Commands",
                            f"Send {shortcut} as a direct message to your BBS node.\n"
                            "This desktop build does not provide a direct message composer.")

    def show_radio(self):
        """Bring attention to real radio connection settings on the dashboard."""
        self.show_info("Radio Connection",
                            "Choose USB / Serial or Network radio on the dashboard, "
                            "then enter the device path or radio IP address. "
                            "Start the Sitdown to launch the configured BBS. "
                            "A running server process does not prove a radio link.")

    def show_about(self):
        self.show_info(
            "About The Sitdown BBS",
            "THE SITDOWN BBS — North Jersey Communications Division\n"
            "Jersey-themed Meshtastic bulletin board.\n"
            "Built for the mesh. Raised in Jersey.\n\n"
            "Original project: TC²-BBS by TheCommsChannel.\n"
            "https://github.com/TheCommsChannel/TC2-BBS-mesh\n\n"
            "Connection details shown here come from the running app, "
            "not from promotional demo artwork."
        )

    def styled_button(self, parent, text, command, color=None, compact=False):
        # macOS Aqua ignores custom backgrounds on native Tk buttons,
        # producing white-on-white labels. Use a keyboard-accessible Label.
        background = color or self.colors["primary"]
        control = tk.Label(parent, text=text, bg=background, fg="#FFFFFF",
                           padx=8 if compact else 13, pady=7 if compact else 10,
                           cursor="hand2",
                           font=("Helvetica", 10 if compact else 12, "bold"), relief="flat",
                           highlightthickness=2, highlightbackground=self.colors["background"],
                           takefocus=True)
        control.bind("<Button-1>", lambda _event: command())
        control.bind("<Return>", lambda _event: command())
        control.bind("<space>", lambda _event: command())
        control.bind("<FocusIn>", lambda _event: control.configure(
            highlightbackground=self.colors["highlight"]))
        control.bind("<FocusOut>", lambda _event: control.configure(
            highlightbackground=self.colors["background"]))
        return control

    def log(self, message):
        self.output.configure(state="normal")
        tag = ("event_error" if any(word in message.lower() for word in
                ("error", "failed", "traceback")) else
               "event_ready" if any(word in message.lower() for word in
                ("initialized", "ready", "running")) else None)
        display = message.replace("\\n", "\n    ") if "Sending message to user" in message else message
        self.output.insert("end", display + "\n", (tag,) if tag else ())
        if int(self.output.index("end-1c").split(".")[0]) > 2000:
            self.output.delete("1.0", "300.0")
        self.output.see("end")
        self.output.configure(state="disabled")

    def find_log(self):
        """Find the next match without altering or filtering server output."""
        query = self.log_query.get().strip()
        if not query:
            return
        self.output.tag_remove("search_hit", "1.0", "end")
        start = self.output.index("insert + 1c")
        match = self.output.search(query, start, stopindex="end", nocase=True)
        if not match:
            match = self.output.search(query, "1.0", stopindex="end", nocase=True)
        if match:
            end = self.output.index(f"{match} + {len(query)}c")
            self.output.tag_add("search_hit", match, end)
            self.output.tag_configure("search_hit", background=THEME["highlight"], foreground=THEME["background"])
            self.output.mark_set("insert", match)
            self.output.see(match)
        else:
            self.show_info("The Backroom", "No matching log entry found.")

    def show_nodes(self):
        """Display observed node IDs only; no network lookup or radio traffic."""
        win = tk.Toplevel(self.root)
        win.title("Who's Who — Observed Nodes")
        win.configure(bg=THEME["background"])
        tk.Label(win, text="WHO'S WHO IN THE FAMILY", fg=THEME["highlight"],
                 bg=THEME["background"], font=("Helvetica", 16, "bold")).pack(padx=18, pady=12)
        nodes = sorted(str(node) for node in (self.supervisor.nodes if self.supervisor else []))
        display = "\n".join(nodes) if nodes else "No nodes observed in this session."
        tk.Label(win, text=display, fg=THEME["text"], bg=THEME["background"],
                 justify="left", wraplength=480).pack(padx=18, pady=(0, 18))

    def clear_log(self):
        """Clear the visible log only; the running server is unaffected."""
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.log("The Backroom: visible log cleared.")

    def export_log(self):
        """Save a snapshot of the visible log without stopping the server."""
        destination = filedialog.asksaveasfilename(
            parent=self.root, title="Save The Backroom log",
            defaultextension=".txt", initialfile="sitdown-bbs-log.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not destination:
            return
        try:
            snapshot = self.output.get("1.0", "end-1c")
            Path(destination).write_text(snapshot + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Couldn't save log", str(exc))
            return
        self.log("The Backroom: log exported.")

    def list_ports(self):
        try:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports()]
            self.log("USB ports: " + (", ".join(ports) if ports else "None detected"))
            if len(ports) == 1 and self.connection.get() == "serial":
                self.address.set(ports[0])
        except ImportError:
            self.log("pyserial is missing. Install requirements.txt.")

    def start(self):
        if self.supervisor and self.supervisor.running:
            return
        self.restart_at = None
        if self.demo.get():
            self.status.set("Demo running — no radio")
            self.radio_activity.set("Radio activity: Demo only")
            self.log("DEMO: No radio messages are sent.")
            self.retry_count = 0
            return
        DATA.mkdir(parents=True, exist_ok=True)
        config = DATA / "config.ini" if getattr(sys, "frozen", False) else ROOT / "config.ini"
        if not config.exists() and getattr(sys, "frozen", False) and (ROOT / "example_config.ini").exists():
            shutil.copy2(ROOT / "example_config.ini", config)
            self.log("Created config.ini in ~/.sitdown-bbs. Review it before connecting a radio.")
        if not config.exists():
            messagebox.showerror("Need a Guy?", "Missing config.ini. Copy example_config.ini to config.ini and configure it first.")
            return
        addr = self.address.get().strip()
        if self.connection.get() == "tcp" and not addr:
            messagebox.showerror("Need a Guy?", "Enter the radio IP or hostname for TCP.")
            return
        self.save()
        cmd = ([sys.executable, "--sitdown-server"] if getattr(sys, "frozen", False)
               else [sys.executable, "-u", str(ROOT / "server.py")]) + ["--config", str(config),
               "--interface-type", self.connection.get()]
        if addr:
            cmd += ["--host" if self.connection.get() == "tcp" else "--port", addr]
        try:
            self.supervisor = ServerSupervisor(cmd, DATA if getattr(sys, "frozen", False) else ROOT)
            self.supervisor.start()
            self.status.set("Starting...")
            if hasattr(self, "radio_activity"):
                self.radio_activity.set("Radio activity: Awaiting messages")
            self.traffic.set("Messages observed: RX 0 / TX 0")
            self.link_warning.set("TCP health: Awaiting observed traffic" if self.connection.get() == "tcp" else "Radio link: Unverified")
            self.log("Starting The Sitdown BBS...")
        except OSError as exc:
            self.supervisor = None
            self.status.set("Start failed")
            self.log(f"Start failed: {exc}")
            self.schedule_recovery()

    def poll(self):
        monitor = self.supervisor
        if monitor:
            for kind, value in monitor.poll_events():
                if kind == "log":
                    self.log(value)
                elif kind == "state":
                    self.status.set(value)
                elif kind == "activity" and value == "rx":
                    self.radio_activity.set("Radio RX observed in BBS logs")
                elif kind == "link_error":
                    self.link_warning.set("Radio transport error — see server log")
                elif kind == "node":
                    self.node_count.set(f"Observed nodes: {len(monitor.nodes)}")
            self.traffic.set(f"Messages observed: RX {monitor.rx_count} / TX {monitor.tx_count}")
            if monitor.running:
                if monitor.link_state == "disconnected":
                    self.link_warning.set("Radio disconnected — awaiting SDK recovery (30s)")
                elif monitor.link_state == "sdk_connected":
                    self.link_warning.set("SDK session established; continuous link unverified")
                if monitor.last_rx_at is not None:
                    age = max(0, int(time.time() - monitor.last_rx_at))
                    self.radio_activity.set(f"Radio RX observed {age}s ago")
                    if not monitor.last_link_error and monitor.link_state == "unverified":
                        self.link_warning.set("Radio traffic observed (not continuous link health)")
                self.uptime.set(f"Uptime: {monitor.uptime_seconds()}s")
            elif not monitor.stopping and self.restart_at is None:
                code = monitor.process.poll() if monitor.process else "unknown"
                self.log(f"BBS process exited ({code}).")
                self.status.set("Disconnected / process stopped")
                self.schedule_recovery()
                self.supervisor = None
                self.radio_activity.set("Radio activity: Process stopped")
                self.uptime.set("Uptime: 0s")
                self.link_warning.set("Radio link: Disconnected / process stopped")
        if self.restart_at is not None and (not self.auto_restart.get() or self.demo.get()):
            self.restart_at = None
            self.status.set("Stopped — recovery cancelled")
        if self.restart_at is not None:
            remaining = max(0, int(self.restart_at - time.monotonic()) + 1)
            self.status.set(f"Retry in {remaining}s (attempt {self.retry_count})")
        if self.restart_at is not None and time.monotonic() >= self.restart_at:
            self.restart_at = None
            self.start()
        if self.root.winfo_exists():
            self.root.after(500, self.poll)

    def schedule_recovery(self):
        if self.auto_restart.get() and not self.demo.get():
            self.retry_count += 1
            delay = min(60, 2 ** min(self.retry_count, 6))
            self.restart_at = time.monotonic() + delay
            self.log(f"Retrying process in {delay}s (attempt {self.retry_count}).")
            self.status.set(f"Retry in {delay}s (attempt {self.retry_count})")

    def restart(self):
        """Restart on demand without scheduling crash recovery."""
        self.stop()
        self.log("Manual server restart requested.")
        self.start()

    def copy_diagnostics(self):
        """Copy useful local state; do not assert radio connectivity."""
        monitor = self.supervisor
        details = [
            "The Sitdown BBS — local diagnostics",
            f"Process status: {self.status.get()}",
            f"Mode: {'Demo (no radio)' if self.demo.get() else self.connection.get().upper()}",
            f"Endpoint: {self.address.get().strip() or '(default)'}",
            f"Server process running: {bool(monitor and monitor.running)}",
            f"Observed nodes: {len(monitor.nodes) if monitor else 0}",
            f"Uptime: {monitor.uptime_seconds() if monitor else 0}s",
            f"Radio activity: {self.radio_activity.get()}",
            f"Traffic: {self.traffic.get()}",
            f"Link warning: {self.link_warning.get()}",
            f"Automatic restart: {self.auto_restart.get()}",
            f"Restart attempts: {self.retry_count}",
            f"SDK radio session: {monitor.link_state if monitor else 'unverified'}",
            "Continuous radio reachability / mesh delivery verified: No",
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(details))
        self.root.update()
        self.log("Local diagnostics copied to clipboard.")

    def stop(self):
        self.restart_at = None
        self.retry_count = 0
        if self.supervisor:
            self.supervisor.stop()
            self.supervisor = None
        self.status.set("Stopped")
        if hasattr(self, "radio_activity"):
            self.radio_activity.set("Radio activity: Process stopped")
        self.uptime.set("Uptime: 0s")
        self.traffic.set("Messages observed: RX 0 / TX 0")
        self.link_warning.set("Radio link: Unverified")
        self.log("Fuggedaboutit. Server stopped.")

    def commands(self):
        win = tk.Toplevel(self.root)
        win.title("The Playbook | Radio Commands")
        win.configure(bg=THEME["background"])
        tk.Label(win, text="DM these commands to your BBS radio", bg=THEME["background"],
                 fg=THEME["highlight"], font=("Helvetica", 14, "bold")).pack(padx=20, pady=12)
        selected = tk.StringVar(value=COMMANDS[0][0])
        for cmd, desc in COMMANDS:
            tk.Radiobutton(win, text=f"{cmd} — {desc}", value=cmd, variable=selected,
                           bg=THEME["background"], fg=THEME["text"],
                           selectcolor=THEME["panel"], anchor="w").pack(fill="x", padx=20)
        def copy():
            win.clipboard_clear()
            win.clipboard_append(selected.get())
            win.update()
        self.styled_button(win, "Copy selected command", copy, THEME["primary"]).pack(pady=15)

    def settings(self):
        win = tk.Toplevel(self.root)
        win.title("The Family Business")
        win.configure(bg=THEME["background"])
        for name, var in [("Community name", self.community), ("Welcome message (local setting)", self.welcome)]:
            tk.Label(win, text=name, bg=THEME["background"], fg=THEME["text"]).pack(anchor="w", padx=20, pady=(12, 0))
            tk.Entry(win, textvariable=var, width=55, bg=THEME["panel"], fg=THEME["text"],
                     insertbackground=THEME["text"]).pack(padx=20)
        tk.Label(win, text="Custom welcome is saved locally; radio reply integration is pending.",
                 bg=THEME["background"], fg=THEME["highlight"]).pack(padx=20, pady=10)
        tk.Label(win, text="JERSEY MOUTH CONTROL — DESKTOP", bg=THEME["background"], fg=THEME["highlight"]).pack(padx=20, pady=(10, 2))
        for text, mode in [("Clean Jersey", "clean"), ("Jersey Attitude", "attitude"), ("Full Jersey Mouth", "uncensored")]:
            tk.Radiobutton(win, text=text, variable=self.desktop_mouth, value=mode,
                           bg=THEME["background"], fg=THEME["text"], selectcolor=THEME["panel"]).pack(anchor="w", padx=20)
        tk.Label(win, text="PUBLIC RADIO MESSAGE STYLE (future integration)", bg=THEME["background"], fg=THEME["highlight"]).pack(padx=20, pady=(10, 2))
        for text, mode in [("Clean Jersey", "clean"), ("Jersey Attitude", "attitude"), ("Full Jersey Mouth", "uncensored")]:
            tk.Radiobutton(win, text=text, variable=self.public_mouth, value=mode,
                           bg=THEME["background"], fg=THEME["text"], selectcolor=THEME["panel"]).pack(anchor="w", padx=20)
        tk.Checkbutton(win, text="I explicitly allow profanity in future public radio broadcasts",
                       variable=self.public_profanity, bg=THEME["background"], fg=THEME["text"],
                       selectcolor=THEME["panel"]).pack(anchor="w", padx=20, pady=6)
        tk.Label(win, text="Preferences are local only; BBS radio integration is not yet active.",
                 bg=THEME["background"], fg=THEME["highlight"]).pack(padx=20)
        preview = tk.StringVar()
        def refresh_preview(*_args):
            try:
                personality = Personality(self.desktop_mouth.get(), self.public_mouth.get(),
                                          self.public_profanity.get())
                preview.set("Desktop: " + personality.message("welcome") +
                            "\nPublic (not transmitted): " + personality.message("welcome", public=True))
            except ValueError:
                preview.set("Invalid personality settings")
        for variable in (self.desktop_mouth, self.public_mouth, self.public_profanity):
            variable.trace_add("write", refresh_preview)
        refresh_preview()
        tk.Label(win, textvariable=preview, justify="left", wraplength=490,
                 bg=THEME["panel"], fg=THEME["text"], padx=12, pady=10).pack(fill="x", padx=20, pady=10)
        self.styled_button(win, "Save", self.save, THEME["connected"]).pack(pady=12)

    def backup(self):
        DATA.mkdir(parents=True, exist_ok=True)
        destination = filedialog.asksaveasfilename(defaultextension=".zip",
                     initialfile="sitdown-backup.zip", filetypes=[("Zip archive", "*.zip")])
        if not destination:
            return
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [CONFIG, ROOT / "config.ini", *ROOT.glob("*.db")]:
                if path.exists() and path.is_file():
                    archive.write(path, path.name)
        self.log("The Books: backup saved. Treat backups as sensitive; they may contain messages and keys.")

    def close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    if "--sitdown-server" in sys.argv:
        sys.argv.remove("--sitdown-server")
        import server  # Ensures PyInstaller includes the server and its dependencies.
        runpy.run_module("server", run_name="__main__")
        sys.exit(0)
    root = tk.Tk()
    SitdownApp(root)
    root.mainloop()
