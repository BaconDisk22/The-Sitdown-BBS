#!/usr/bin/env python3
"""The Sitdown BBS desktop launcher. Standard-library Tkinter GUI."""
import json
import configparser
import sqlite3
from tkinter import ttk
from sitdown_utilities import format_node
from sitdown_online import WeatherDesk
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
THEME = {"background": "#030a0c", "panel": "#061013", "primary": "#ed001b",
         "connected": "#19e333", "text": "#F5F5F0", "highlight": "#d3dde0"}
COMMANDS = [
    ("/sitdown", "Main menu"), ("/help", "Quick help"),
    ("/mail", "Check your mail"), ("/boards", "The Social Club"),
    ("/fortune", "Jersey wisdom"), ("/tools", "Utilities"),
    ("/cancel", "Return to main menu"),
    ("/node <ID or name>", "Who’s Who"), ("/weather", "Jersey Weather Desk"),
    ("/wire", "MQTT activity"), ("/announce <channel> <text>", "Admin broadcast"),
]


class SitdownApp:
    def __init__(self, root):
        self.root = root
        self.snapshot = {'nodes': [], 'channels': [], 'mqtt': {'status': 'Disabled', 'total': 0, 'topics': []}}
        self.active_page = None
        self.proc = None
        self.supervisor = None
        self.restart_at = None
        self.retry_count = 0
        self.auto_restart = tk.BooleanVar(value=False)
        self.node_count = tk.StringVar(value='Observed nodes: 0')
        self.uptime = tk.StringVar(value='Uptime: 0s')
        self.radio_activity = tk.StringVar(value='Radio activity: Not observed')
        self.traffic = tk.StringVar(value='Messages observed: RX 0 / TX 0')
        self.link_warning = tk.StringVar(value='Radio link: Unverified')
        self.auto_start = tk.BooleanVar(value=False)
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
        self.root.geometry("1160x940")
        self.root.minsize(960, 760)
        self.root.configure(bg=THEME["background"])
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TNotebook', background=THEME['background'], borderwidth=0)
        style.configure('TNotebook.Tab', background=THEME['panel'], foreground=THEME['text'], padding=(15, 10))
        style.map('TNotebook.Tab', background=[('selected', THEME['primary'])], foreground=[('selected', 'white')])
        style.configure('Desk.TEntry', fieldbackground='#0B141A', foreground='white', insertcolor='white', padding=8)
        style.configure('TCombobox', fieldbackground=THEME['background'], foreground=THEME['text'])
        style.map('TCombobox', fieldbackground=[('readonly', THEME['background'])], foreground=[('readonly', THEME['text'])])
        self.root.option_add('*Entry.highlightThickness', 1)
        self.root.option_add('*Entry.highlightBackground', '#527079')
        self.root.option_add('*Entry.relief', 'flat')
        self.load()
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(1000, self.poll)
        if self.auto_start.get():
            self.root.after(200, self.start)

    def load(self):
        if CONFIG.exists():
            try:
                data = json.loads(CONFIG.read_text(encoding="utf-8"))
                self.auto_start.set(data.get("auto_start", False) is True)
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
            "auto_start": self.auto_start.get(), "connection": self.connection.get(), "address": self.address.get(),
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
        from PIL import Image
        self.banner_source = Image.open(ROOT / 'assets' / 'jersey-banner.png').convert('RGB')
        header = tk.Frame(self.root, bg=c['background'])
        header.pack(fill='x', padx=12, pady=(8, 0))
        self.banner = tk.Canvas(header, height=220, bg=c['background'], highlightthickness=0)
        self.banner.pack(fill='x')
        self.banner.bind('<Configure>', self.render_banner)
        navigation = tk.Frame(self.root, bg=c["panel"], pady=7)
        navigation.pack(fill="x", padx=12, pady=(2, 6))
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
            action = lambda name=title.split()[-1]: self.select_page(name)
            control = self.styled_button(
                navigation, title, action,
                c["primary"] if "HOME" in title else c["panel"],
                compact=True)
            self.nav_buttons.append(control)
        navigation.bind("<Configure>", self.layout_navigation)
        self.page_host = tk.Frame(self.root, bg=c['background'])
        self.page_host.pack(fill='both', expand=True)
        self.home_page = tk.Frame(self.page_host, bg=c['background'])
        self.home_page.pack(fill='both', expand=True)
        cards = tk.Frame(self.home_page, bg=c["background"])
        cards.pack(fill="x", padx=8, pady=(0, 4))
        for column in range(3):
            cards.grid_columnconfigure(column, weight=1, uniform="jersey")

        def card(column, title):
            frame = tk.Frame(cards, bg=c["panel"], padx=10, pady=7,
                             highlightbackground="#24404A", highlightthickness=1)
            frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=4)
            tk.Label(frame, text=title, bg=c["panel"], fg=c["highlight"],
                     font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 5))
            return frame

        radio = card(0, "Connection Status")
        tk.Label(radio, textvariable=self.radio_activity, bg=c['panel'], fg=c['connected'],
                 font=('Helvetica', 11, 'bold'), wraplength=300, justify='left').pack(anchor='w', pady=(0, 8))
        transport = tk.Frame(radio, bg=c['panel']); transport.pack(fill='x')
        for title, value in (('USB / Serial', 'serial'), ('TCP / Network', 'tcp')):
            tk.Radiobutton(transport, text=title, variable=self.connection, value=value,
                           bg=c['panel'], fg=c['text'], selectcolor='#17262b').pack(side='left')
        tk.Label(radio, text="Device path or radio IP", bg=c["panel"], fg=c["text"]).pack(anchor="w", pady=(10, 2))
        ttk.Entry(radio, textvariable=self.address, style='Desk.TEntry').pack(fill='x')
        self.styled_button(radio, "Find USB Ports", self.list_ports, "#233139").pack(
            fill="x", pady=(8, 0))
        self.connection_summary = tk.StringVar()
        tk.Label(radio, textvariable=self.connection_summary, bg=c["panel"],
                 fg=c["text"], justify="left", wraplength=280).pack(anchor="w", pady=(8, 0))
        self.connection.trace_add("write", self.refresh_connection_summary)
        self.address.trace_add("write", self.refresh_connection_summary)
        self.refresh_connection_summary()
        tk.Label(radio, text="Process status does not confirm a radio link.",
                 bg=c["panel"], fg=c["highlight"], wraplength=275,
                 justify="left").pack(anchor="w", pady=(10, 0))

        tk.Label(radio, textvariable=self.node_count, bg=c['panel'], fg=c['text']).pack(anchor='w', pady=3)
        tk.Label(radio, textvariable=self.uptime, bg=c['panel'], fg=c['text']).pack(anchor='w', pady=3)
        tk.Label(radio, textvariable=self.traffic, bg=c['panel'], fg=c['text']).pack(anchor='w', pady=3)
        tk.Label(radio, textvariable=self.link_warning, bg=c['panel'], fg=c['highlight'], wraplength=280).pack(anchor='w', pady=3)
        self.styled_button(radio, 'Disconnect', self.stop, c['primary']).pack(fill='x', pady=(10, 0))

        server = card(1, "BBS Server")
        self.status_row = tk.Frame(server, bg=c["panel"])
        self.status_row.pack(fill="x", pady=(0, 8))
        self.status_dot = tk.Label(self.status_row, text="●", bg=c["panel"],
                                   fg=c["primary"], font=("Helvetica", 16, "bold"))
        self.status_dot.pack(side="left", padx=(0, 6))
        tk.Label(self.status_row, textvariable=self.status, bg=c["panel"],
                 fg=c["text"], wraplength=230, justify="left").pack(side="left")
        self.status.trace_add("write", self.refresh_status_indicator)
        self.refresh_status_indicator()
        self.styled_button(server, 'Start BBS Server', self.start, '#233139').pack(fill='x', pady=3)
        self.toggle_row(server, 'Auto start at launch', self.auto_start)
        self.toggle_row(server, 'Restart on crash', self.auto_restart)
        self.toggle_row(server, 'Demo — no radio', self.demo)
        self.styled_button(server, '↻  Restart Server', self.restart, '#233139').pack(fill='x', pady=(10, 3))
        self.styled_button(server, '■  Stop Server', self.stop, c['primary']).pack(fill='x', pady=3)
        tk.Label(server, text='Process status is separate from radio RX.', bg=c['panel'], fg='#a6b4b8',
                 wraplength=280, justify='left').pack(anchor='w', pady=8)

        personality = card(2, "Jersey Personality • Attitude Adjustah")
        tk.Label(personality, text='Desktop greeting style', bg=c['panel'], fg='#a6b4b8').pack(anchor='w', pady=5)
        choices = tk.Frame(personality, bg=c['panel']); choices.pack(fill='x')
        for title, mode in (('CLEAN', 'clean'), ('JERSEY', 'attitude'), ('HEAVY', 'uncensored')):
            control = self.styled_button(choices, title, lambda m=mode: self.desktop_mouth.set(m), '#233139', compact=True)
            control.pack(side='left', expand=True, fill='x', padx=2)
            def selected(*_, button=control, value=mode):
                button.configure(bg=c['primary'] if self.desktop_mouth.get() == value else '#233139')
            self.desktop_mouth.trace_add('write', selected); selected()
        self.greeting_preview = tk.StringVar()
        def preview(*_):
            self.greeting_preview.set(Personality(self.desktop_mouth.get()).message('welcome'))
        self.desktop_mouth.trace_add('write', preview); preview()
        tk.Label(personality, text='Preview', bg=c['panel'], fg=c['text']).pack(anchor='w', pady=(12, 4))
        tk.Label(personality, textvariable=self.greeting_preview, font=('Menlo', 11), bg='#020b0d', fg=c['text'],
                 wraplength=275, justify='left', anchor='nw', height=4, padx=8, pady=8,
                 highlightbackground='#1e3035', highlightthickness=1).pack(fill='x')
        self.styled_button(personality, 'Save Settings', self.save, '#233139').pack(fill='x', pady=(10, 3))
        self.styled_button(personality, 'Public Broadcast Settings', self.settings, '#233139').pack(fill='x', pady=3)
        log_header = tk.Frame(self.home_page, bg=c["panel"], padx=12, pady=9,
                              highlightbackground="#24404A", highlightthickness=1)
        log_header.pack(fill="x", padx=20, pady=(10, 0))
        label(log_header, '▤  Server Log', 12, c['text']).pack(side='left')
        self.log_query = tk.StringVar()
        for title, action in (('Clear Log', self.clear_log), ('Save Log', self.export_log), ('Find', self.find_log)):
            self.styled_button(log_header, title, action, '#233139', compact=True).pack(side='right', padx=3)
        ttk.Entry(log_header, textvariable=self.log_query, width=20, style='Desk.TEntry').pack(side='right', padx=5)

        # Read-only footer: process status is not proof of a live radio link.
        footer = tk.Frame(self.home_page, bg=c["panel"], padx=14, pady=7,
                          highlightbackground="#24404A", highlightthickness=1)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 6))
        tk.Label(footer, text="THE SITDOWN BBS  •  NORTH JERSEY",
                 bg=c["panel"], fg=c["highlight"],
                 font=("Helvetica", 10, "bold")).pack(side="left")
        self.styled_button(footer, 'The Books', self.backup, c['panel'], compact=True).pack(side='left', padx=8)
        self.styled_button(footer, 'Diagnostics', self.copy_diagnostics, c['panel'], compact=True).pack(side='left')
        tk.Label(footer, textvariable=self.status, bg=c["panel"], fg=c["text"],
                 font=("Helvetica", 10)).pack(side="right", padx=(14, 0))
        tk.Label(footer, text="SERVER PROCESS:", bg=c["panel"], fg=c["highlight"],
                 font=("Helvetica", 10, "bold")).pack(side="right")
        self.output = tk.Text(self.home_page, bg="#01090b", fg="#42ed50", insertbackground=c["text"],
                              wrap="word", relief="flat", state="disabled", height=7,
                              font=("Menlo", 11), padx=16, pady=12,
                              highlightbackground="#24404A", highlightthickness=1)
        self.output.pack(fill="both", expand=True, padx=20, pady=(5, 5))
        self.output.tag_configure("event_error", foreground="#FF8B85")
        self.output.tag_configure("event_ready", foreground="#27ff3d")
        self.log(Personality(self.desktop_mouth.get(), self.public_mouth.get(), self.public_profanity.get()).message("welcome"))
        self.log("Pick a radio, or check Demo mode.")

    def render_banner(self, event):
        from PIL import Image, ImageTk
        self.banner_photo = ImageTk.PhotoImage(self.banner_source.resize(
            (max(1, event.width), max(1, event.height)), Image.Resampling.LANCZOS))
        self.banner.delete('all')
        self.banner.create_image(0, 0, anchor='nw', image=self.banner_photo)

    def toggle_row(self, parent, title, variable):
        row = tk.Frame(parent, bg=self.colors['panel']); row.pack(fill='x', pady=6)
        tk.Label(row, text=title, bg=self.colors['panel'], fg=self.colors['text']).pack(side='left')
        toggle = tk.Canvas(row, width=44, height=24, bg=self.colors['panel'], highlightthickness=0, takefocus=True, cursor='hand2')
        toggle.pack(side='right')
        def draw(*_):
            toggle.delete('all')
            color = '#16cb37' if variable.get() else '#34464d'
            toggle.create_oval(1, 2, 22, 23, fill=color, outline=color)
            toggle.create_oval(22, 2, 43, 23, fill=color, outline=color)
            toggle.create_rectangle(11, 2, 33, 23, fill=color, outline=color)
            x = 23 if variable.get() else 3
            toggle.create_oval(x, 4, x+17, 21, fill='white', outline='white')
        def change(_=None): variable.set(not variable.get())
        for event in ('<Button-1>', '<space>', '<Return>'): toggle.bind(event, change)
        toggle.bind('<FocusIn>', lambda _: toggle.configure(highlightthickness=1, highlightbackground='#ffffff'))
        toggle.bind('<FocusOut>', lambda _: toggle.configure(highlightthickness=0))
        variable.trace_add('write', draw); draw()

    def config_path(self):
        return (DATA if getattr(sys, 'frozen', False) else ROOT) / 'config.ini'

    def read_config(self):
        config = configparser.ConfigParser(interpolation=None)
        path = self.config_path()
        config.read(path if path.exists() else ROOT / 'example_config.ini')
        return config

    def control_request(self, action, **fields):
        if self.demo.get():
            self.show_info('Demo mode', 'Demonstration only — no radio or internet request was sent.')
            return
        try:
            if not self.supervisor:
                raise RuntimeError('Start the BBS server first.')
            self.supervisor.request(action, **fields)
            self.log('Requested ' + action + '; awaiting server response.')
        except RuntimeError as exc:
            self.show_info('The Sitdown', str(exc))

    def select_page(self, title):
        for button in self.nav_buttons:
            button.configure(bg=self.colors['primary'] if button.cget('text').split()[-1] == title else self.colors['background'])
        if self.active_page is not None:
            self.active_page.destroy()
            self.active_page = None
        self.home_page.pack_forget()
        if title == 'HOME':
            self.home_page.pack(fill='both', expand=True)
            return
        page = tk.Frame(self.page_host, bg=THEME['background'], padx=24, pady=15)
        page.pack(fill='both', expand=True)
        self.active_page = page
        tk.Label(page, text=title + '  /  THE SITDOWN', font=('Helvetica', 20, 'bold'),
                 bg=THEME['background'], fg=THEME['highlight']).pack(anchor='w', pady=(0, 15))
        if title == 'BBS':
            self.utility_page(page)
        elif title == 'NODES':
            self.nodes_page(page)
        elif title in ('MESSAGES', 'BOARDS'):
            self.database_page(page, title)
        elif title == 'SETTINGS':
            self.integration_settings(page)
        elif title == 'RADIO':
            for variable in (self.status, self.connection_summary, self.radio_activity, self.node_count, self.uptime):
                tk.Label(page, textvariable=variable, bg=THEME['background'], fg=THEME['text'],
                         font=('Helvetica', 14), justify='left').pack(anchor='w', pady=8)
            self.page_text(page, 'Channels from the connected radio:\n' + json.dumps(self.snapshot['channels'], indent=2))
        else:
            self.page_text(page, 'THE SITDOWN BBS\nNorth Jersey Communications Division\n\n'
                'Built for the mesh. Raised in Jersey.\nBased on TC²-BBS by TheCommsChannel. GPL-3.0.\n\n'
                'Weather: Open-Meteo (only when enabled).\nMQTT counts are separate from radio reception.\n'
                'Demo screens and build checks do not establish physical radio compatibility.')

    def page_text(self, parent, text):
        box = tk.Text(parent, bg='#0B141A', fg=THEME['text'], wrap='word',
                      font=('Menlo', 12), padx=15, pady=15, relief='flat')
        scroll = ttk.Scrollbar(parent, command=box.yview)
        scroll.pack(side='right', fill='y')
        box.configure(yscrollcommand=scroll.set)
        box.pack(fill='both', expand=True, pady=10)
        box.insert('1.0', text)
        box.configure(state='disabled')
        return box

    def utility_page(self, page):
        notebook = ttk.Notebook(page)
        notebook.pack(fill='both', expand=True)
        announcement = tk.Frame(notebook, bg=THEME['panel'], padx=20, pady=20)
        weather = tk.Frame(notebook, bg=THEME['panel'], padx=20, pady=20)
        wire = tk.Frame(notebook, bg=THEME['panel'], padx=20, pady=20)
        for frame, title in ((announcement, 'The Boss Has Spoken'), (weather, 'Jersey Weather Desk'), (wire, 'The Wire')):
            notebook.add(frame, text=title)
        tk.Label(announcement, text='Broadcast to an enabled radio channel (maximum 200 UTF-8 bytes).',
                 fg=THEME['text'], bg=THEME['panel']).pack(anchor='w')
        channel = tk.StringVar()
        options = [f"{ch['index']}: {ch['name']}" for ch in self.snapshot['channels']]
        if options:
            channel.set(options[0])
        ttk.Combobox(announcement, textvariable=channel, values=options, state='readonly').pack(fill='x', pady=10)
        text = tk.Text(announcement, height=5, bg=THEME['background'], fg=THEME['text'], insertbackground='white')
        text.pack(fill='x', pady=10)
        def send():
            message = text.get('1.0', 'end-1c')
            if not channel.get() or not message.strip() or len(message.encode('utf-8')) > 200:
                self.show_info('Check announcement', 'Choose an enabled channel and enter 1–200 UTF-8 bytes.')
                return
            if messagebox.askyesno('Broadcast announcement?', f'Channel {channel.get()}\n\n{message}', parent=self.root):
                self.control_request('announce', channel=int(channel.get().split(':', 1)[0]), text=message)
        self.styled_button(announcement, 'PREVIEW & BROADCAST', send).pack(anchor='w')
        tk.Label(announcement, text='Channel list updates when you reopen this tab after connecting.\n'
                 'Remote /announce commands require an administrator ID in Settings.',
                 bg=THEME['panel'], fg=THEME['highlight'], justify='left').pack(anchor='w', pady=15)
        self.styled_button(weather, 'GET WEATHER REPORT', lambda: self.control_request('weather')).pack(anchor='w')
        config = self.read_config()
        enabled = config.getboolean('weather', 'internet_enabled', fallback=False)
        self.page_text(weather, 'Internet weather: ' + ('Enabled' if enabled else 'Disabled') + '\n\n'
                       + config.get('weather', 'local_report', fallback='No local report configured.')
                       + '\n\nConfigure a local report or explicitly enable internet weather in Settings.\n'
                       'Internet results use Open-Meteo, cache for ten minutes, and label stale data.')
        self.styled_button(wire, 'REFRESH COUNTS', lambda: self.select_page('BBS')).pack(anchor='w')
        data = self.snapshot['mqtt']
        self.page_text(wire, f"MQTT: {data['status']}\nMessages this server session: {data['total']}\n\n"
                       + '\n'.join(f'{count}  {topic}' for topic, count in data['topics'])
                       + '\n\nMQTT is opt-in and never forwards messages to the radio.\n'
                       'Counts exclude retained messages; they are not proof of radio RX.')

    def nodes_page(self, page):
        query = tk.StringVar()
        tk.Label(page, text='Search the full radio node database by ID, short name, or long name.\n'
                 'Snapshot remains visible after disconnect; reopen this tab to refresh.',
                 bg=THEME['background'], fg=THEME['text'], justify='left').pack(anchor='w')
        tk.Entry(page, textvariable=query, bg=THEME['panel'], fg=THEME['text'],
                 insertbackground='white').pack(fill='x', pady=10)
        box = self.page_text(page, '')
        def refresh(*_):
            from sitdown_utilities import node_id
            key = query.get().strip().casefold()
            rows = [row for row in self.snapshot['nodes'] if not key or node_id(key) == row['id']
                    or key in (row['shortName'] + ' ' + row['longName']).casefold()]
            text = '\n\n'.join(format_node(row) for row in rows) or 'No matching nodes. Connect a radio to load its database.'
            box.configure(state='normal'); box.delete('1.0', 'end'); box.insert('1.0', text); box.configure(state='disabled')
        query.trace_add('write', refresh)
        refresh()

    def database_page(self, page, title):
        self.styled_button(page, 'REFRESH', lambda: self.select_page(title)).pack(anchor='w')
        path = self.config_path().parent / 'bulletins.db'
        text = 'No local database yet. Start the BBS to initialize it.'
        if self.demo.get():
            text = 'DEMO DATA — no radio connected\n\n' + ('Welcome to the Social Club\nGeneral: Stay local, stay connected.'
                    if title == 'BOARDS' else 'Sample mail\nAyyy, pull up a chair.')
        elif path.exists():
            try:
                with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
                    sql = ('SELECT board, sender_short_name, date, subject, content FROM bulletins ORDER BY id DESC LIMIT 100'
                           if title == 'BOARDS' else 'SELECT sender_short_name, recipient, date, subject, content FROM mail ORDER BY id DESC LIMIT 100')
                    rows = db.execute(sql).fetchall()
                text = '\n\n'.join('\n'.join(str(value) for value in row) for row in rows) or 'No messages yet.'
            except sqlite3.Error as exc:
                text = 'Could not read the local database: ' + str(exc)
        self.page_text(page, 'Local operator view — latest 100 records, read only.\n\n' + text)

    def integration_settings(self, page):
        config = self.read_config()
        tabs = ttk.Notebook(page)
        tabs.pack(fill='both', expand=True)
        fields = {}
        self.setting_fields = fields
        sections = {
            'startup': [('enabled', 'Broadcast on server start', 'bool'), ('channel', 'Channel index', '0'), ('message', 'Custom welcome (blank = personality)', '')],
            'announcements': [('admin_nodes', 'Remote administrator node IDs (comma separated)', '')],
            'weather': [('internet_enabled', 'Enable internet weather', 'bool'), ('local_report', 'Offline report (include time)', ''), ('latitude', 'Latitude', '40.7357'), ('longitude', 'Longitude', '-74.1724')],
            'mqtt_monitor': [('enabled', 'Enable MQTT counter', 'bool'), ('host', 'Broker hostname', ''), ('topic', 'Subscription topic', ''), ('tls', 'Use TLS', 'bool_true'), ('port', 'Port', '8883'), ('username', 'Username', ''), ('password', 'Password', '')],
            'personality': [('public_mode', 'Public greeting: clean / attitude / uncensored', 'clean'), ('allow_public_profanity', 'Allow profanity in generated public greetings', 'bool')],
        }
        for section, entries in sections.items():
            frame = tk.Frame(tabs, bg=THEME['panel'], padx=20, pady=15)
            tabs.add(frame, text={'mqtt_monitor': 'MQTT', 'startup': 'Startup', 'announcements': 'Admins', 'weather': 'Weather', 'personality': 'Personality'}[section])
            for key, label, default in entries:
                if default.startswith('bool'):
                    var = tk.BooleanVar(value=config.getboolean(section, key, fallback=default == 'bool_true'))
                    tk.Checkbutton(frame, text=label, variable=var, bg=THEME['panel'], fg=THEME['text'], selectcolor=THEME['background']).pack(anchor='w', pady=8)
                else:
                    var = tk.StringVar(value=config.get(section, key, fallback=default))
                    tk.Label(frame, text=label, bg=THEME['panel'], fg=THEME['text']).pack(anchor='w', pady=(8, 2))
                    ttk.Entry(frame, textvariable=var, show='*' if key == 'password' else '', style='Desk.TEntry').pack(fill='x', pady=(3, 8))
                fields[(section, key)] = var
        def save():
            for (section, key), var in fields.items():
                if not config.has_section(section):
                    config.add_section(section)
                config.set(section, key, str(var.get()).lower() if isinstance(var, tk.BooleanVar) else var.get())
            try:
                Personality(public_mode=config.get('personality', 'public_mode'))
                channel = config.getint('startup', 'channel')
                if not 0 <= channel <= 7:
                    raise ValueError('Startup channel must be 0–7.')
                if len(config.get('startup', 'message').encode('utf-8')) > 200:
                    raise ValueError('Startup message exceeds 200 UTF-8 bytes.')
                if config.getboolean('weather', 'internet_enabled'):
                    if not (-90 <= config.getfloat('weather', 'latitude') <= 90 and -180 <= config.getfloat('weather', 'longitude') <= 180):
                        raise ValueError('Invalid weather coordinates.')
                if config.getboolean('mqtt_monitor', 'enabled'):
                    if not config.get('mqtt_monitor', 'host').strip() or not config.get('mqtt_monitor', 'topic').strip():
                        raise ValueError('MQTT requires an explicit broker and topic.')
                    if not 1 <= config.getint('mqtt_monitor', 'port') <= 65535:
                        raise ValueError('Invalid MQTT port.')
                path = self.config_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix('.ini.tmp')
                with temporary.open('w') as stream:
                    config.write(stream)
                temporary.chmod(0o600)
                temporary.replace(path)
                self.show_info('Settings saved', 'Restart the server to apply these settings.')
            except (ValueError, OSError) as exc:
                self.show_info('Settings not saved', str(exc))
        self.styled_button(page, 'SAVE — APPLY ON NEXT SERVER START', save, THEME['connected']).pack(pady=10)

    def layout_navigation(self, event):
        """Wrap measured controls so every action survives font/window resizing."""
        cell_width = max(control.winfo_reqwidth() for control in self.nav_buttons) + 6
        columns = max(1, min(len(self.nav_buttons), event.width // cell_width))
        for column in range(len(self.nav_buttons)):
            self.navigation.grid_columnconfigure(column, weight=1 if column < columns else 0,
                                                 uniform='nav' if column < columns else '')
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
        # Aqua Tk does not render stippled fills transparently; keep skyline visible.
        canvas.create_rectangle(0, 0, width * .52, height * .86, fill='#071017', outline='')
        canvas.create_text(width * .035, height * .2, text='THE', fill='#F5F5F0', anchor='w',
                           font=('Helvetica', max(12, int(width / 70)), 'bold'))
        x = width * .035
        for word, color in (('SIT', '#008C45'), ('DOWN', '#F5F5F0'), (' BBS', '#E13232')):
            item = canvas.create_text(x, height * .5, text=word, fill=color, anchor='w', font=title_font)
            x = canvas.bbox(item)[2]
        canvas.create_text(width * .038, height * .78,
                           text='NORTH JERSEY  •  COMMUNICATIONS DIVISION',
                           fill='#F5F5F0', anchor='w',
                           font=('Helvetica', max(9, min(13, int(width / 82))), 'bold'))


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
        self.select_page("HOME")
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
                           padx=8 if compact else 13, pady=7,
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
        self.select_page('NODES')

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
            self.snapshot = {'type': 'snapshot', 'channels': [{'index': 0, 'name': 'DEMO Local'}],
                'nodes': [{'id': '!abcdef01', 'shortName': 'DEMO', 'longName': 'Demonstration node',
                          'hardware': 'Demo', 'role': 'CLIENT', 'lastHeard': None, 'snr': None,
                          'hopsAway': None, 'deviceMetrics': {}, 'position': {}}],
                'mqtt': {'status': 'Disabled (demo)', 'total': 0, 'topics': []}}
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
        self.snapshot = {'nodes': [], 'channels': [], 'mqtt': {'status': 'Awaiting server', 'total': 0, 'topics': []}}
        self.save()
        cmd = ([sys.executable, "--sitdown-server"] if getattr(sys, "frozen", False)
               else [sys.executable, "-u", str(ROOT / "server.py")]) + ["--config", str(config), "--desktop-control",
               "--interface-type", self.connection.get()]
        if addr:
            cmd += ["--host" if self.connection.get() == "tcp" else "--port", addr]
        try:
            self.supervisor = ServerSupervisor(cmd, DATA if getattr(sys, "frozen", False) else ROOT)
            self.supervisor.start()
            self.status.set("Starting...")
            if hasattr(self, "radio_activity"):
                self.radio_activity.set("Radio activity: Awaiting messages")
            self.log("Starting The Sitdown BBS...")
        except OSError as exc:
            self.supervisor = None
            self.status.set("Start failed")
            self.log(f"Start failed: {exc}")

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
                elif kind == "link_state":
                    self.link_warning.set("Radio disconnected — awaiting SDK recovery (30s)" if value == "disconnected" else "SDK session established; continuous link unverified")
                elif kind == "control":
                    if value.get('type') == 'snapshot':
                        self.snapshot = value
                    else:
                        self.log(value.get('error') or value.get('text', 'Operation complete.'))
                        self.show_info('The Sitdown', value.get('error') or value.get('text', 'Operation complete.'))
                elif kind == "link_error":
                    self.link_warning.set("Radio transport error — see server log")
                elif kind == "node":
                    self.node_count.set(f"Observed nodes: {len(monitor.nodes)}")
            if hasattr(self, "traffic"):
                self.traffic.set(f"Messages observed: RX {monitor.rx_count} / TX {monitor.tx_count}")
            if monitor.running:
                if monitor.link_state == "disconnected":
                    self.link_warning.set("Radio disconnected — awaiting SDK recovery (30s)")
                if monitor.last_rx_at is not None:
                    age = max(0, int(time.time() - monitor.last_rx_at))
                    self.radio_activity.set(f"Radio RX observed {age}s ago")
                self.uptime.set(f"Uptime: {monitor.uptime_seconds()}s")
            elif not monitor.stopping and self.restart_at is None:
                code = monitor.process.poll() if monitor.process else "unknown"
                self.log(f"BBS process exited ({code}).")
                self.status.set("Disconnected / process stopped")
                self.schedule_recovery()
                self.supervisor = None
                self.radio_activity.set("Radio activity: Process stopped")
        if self.restart_at is not None and (not self.auto_restart.get() or self.demo.get()):
            self.restart_at = None
            self.status.set("Stopped — recovery cancelled")
        if self.restart_at is not None and time.monotonic() >= self.restart_at:
            self.restart_at = None
            self.start()
        if self.root.winfo_exists():
            self.root.after(500, self.poll)

    def schedule_recovery(self):
        """Opt-in capped backoff; no retries when recovery is disabled."""
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
            f"Observed RX/TX: {monitor.rx_count if monitor else 0}/{monitor.tx_count if monitor else 0}",
            f"Last transport error: {monitor.last_link_error if monitor else None}",
            "Radio connection verified: Log-observed activity only, not continuous link health",
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
        self.select_page('SETTINGS')

    def backup(self):
        DATA.mkdir(parents=True, exist_ok=True)
        destination = filedialog.asksaveasfilename(defaultextension=".zip",
                     initialfile="sitdown-backup.zip", filetypes=[("Zip archive", "*.zip")])
        if not destination:
            return
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [CONFIG, self.config_path(), *self.config_path().parent.glob("*.db")]:
                if path.exists() and path.is_file():
                    archive.write(path, path.name)
        self.log("The Books: backup saved. Treat backups as sensitive; they may contain messages and keys.")

    def close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    if '--sitdown-smoke-test' in sys.argv:
        # Exercise the packaged imports and actual Tk pages without user config/radio.
        import tempfile
        import server
        import paho.mqtt.client
        with tempfile.TemporaryDirectory() as folder:
            DATA = Path(folder)
            CONFIG = DATA / 'launcher.json'
            root = tk.Tk()
            app = SitdownApp(root)
            app.demo.set(True)
            app.start()
            for page in ('BBS', 'NODES', 'SETTINGS', 'HOME'):
                app.select_page(page)
                root.update()
            assert app.status.get() == 'Demo running — no radio'
            root.destroy()
        sys.exit(0)
    if "--sitdown-server" in sys.argv:
        sys.argv.remove("--sitdown-server")
        import server  # Ensures PyInstaller includes the server and its dependencies.
        runpy.run_module("server", run_name="__main__")
        sys.exit(0)
    root = tk.Tk()
    SitdownApp(root)
    root.mainloop()
