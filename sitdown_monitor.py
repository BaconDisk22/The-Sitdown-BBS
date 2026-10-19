"""Process supervision and log parsing for the Sitdown desktop.

This supervises the BBS *process*, not the radio link. A running process is
not proof of a successful radio connection.
"""
import queue
import json
import os
import secrets
from sitdown_control import PREFIX
from sitdown_link import PREFIX as LINK_PREFIX
import re
import subprocess
import threading
import time

NODE_PATTERN = re.compile(r"Received message from user '([^']+)' \((![0-9a-fA-F]+)\)")
TX_PATTERN = re.compile(r"Sending message to user", re.I)
LINK_ERROR_PATTERN = re.compile(r"(?:no route to host|connection refused|connection reset|broken pipe|network is unreachable|timed out)", re.I)
READY_PATTERN = re.compile(r"(?:THE SITDOWN BBS|TC²-BBS|BBS) is running on", re.I)


class ServerSupervisor:
    def __init__(self, command, cwd, factory=None):
        self.control_token = secrets.token_hex(24)
        self.control_prefix = PREFIX + self.control_token + ' '
        self.command = list(command)
        self.cwd = str(cwd)
        self.factory = factory or subprocess.Popen
        self.events = queue.Queue()
        self.process = None
        self.started_at = None
        self.nodes = {}
        self.ready = False
        self.last_rx_at = None
        self.stopping = False
        self.rx_count = 0
        self.tx_count = 0
        self.last_link_error = None
        self.link_state = 'unverified'

    def start(self):
        if self.process and self.process.poll() is None:
            return False
        self.stopping = False
        self.ready = False
        self.last_rx_at = None
        self.nodes.clear()
        self.rx_count = 0
        self.tx_count = 0
        self.last_link_error = None
        self.process = self.factory(
            self.command, cwd=self.cwd, stdout=subprocess.PIPE,
            env={**os.environ, 'SITDOWN_CONTROL_TOKEN': self.control_token},
            stderr=subprocess.STDOUT, stdin=subprocess.PIPE, text=True, bufsize=1)
        self.started_at = time.monotonic()
        threading.Thread(target=self._read_output, args=(self.process,), daemon=True).start()
        self.events.put(("state", "Starting BBS process..."))
        return True

    def _read_output(self, process):
        try:
            for raw in process.stdout:
                line = raw.rstrip("\r\n")
                if line.startswith(self.control_prefix):
                    try:
                        self.events.put(('control', json.loads(line[len(self.control_prefix):])))
                    except ValueError:
                        self.events.put(('log', 'Invalid desktop event ignored.'))
                    continue
                if line.startswith(LINK_PREFIX):
                    try:
                        state = json.loads(line[len(LINK_PREFIX):])['state']
                        if state in ('sdk_connected', 'disconnected'):
                            self.link_state = state
                            self.events.put(('link_state', state))
                    except (ValueError, KeyError, TypeError):
                        pass
                    continue
                if READY_PATTERN.search(line):
                    self.ready = True
                    self.events.put(("state", "Server initialized (radio link unverified)"))
                if LINK_ERROR_PATTERN.search(line):
                    self.last_link_error = line
                    self.events.put(("link_error", line))
                if TX_PATTERN.search(line):
                    self.tx_count += 1
                    self.events.put(("activity", "tx"))
                match = NODE_PATTERN.search(line)
                if match:
                    self.rx_count += 1
                    self.last_rx_at = time.time()
                    self.events.put(("activity", "rx"))
                    name, node_id = match.groups()
                    self.nodes[node_id] = (name, time.time())
                    self.events.put(("node", node_id))
                self.events.put(("log", line))
        except (OSError, ValueError) as exc:
            self.events.put(("log", f"Log reader stopped: {exc}"))
        finally:
            self.events.put(("reader_done", None))

    def request(self, action, **fields):
        if not self.running or self.stopping:
            raise RuntimeError('Start the BBS server first.')
        try:
            self.process.stdin.write(json.dumps({'action': action, **fields}) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise RuntimeError('Server control pipe closed.') from exc

    def uptime_seconds(self):
        return int(time.monotonic() - self.started_at) if self.started_at is not None and self.running else 0

    @property
    def running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        self.stopping = True
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        self.process = None
        self.started_at = None
        self.ready = False
        self.last_rx_at = None
        self.link_state = 'unverified'

    def poll_events(self, limit=100):
        items = []
        for _ in range(limit):
            try:
                items.append(self.events.get_nowait())
            except queue.Empty:
                break
        return items
