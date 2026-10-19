"""Durable, at-most-once broadcast attempts; never retry uncertain radio sends."""
import sqlite3
from contextlib import contextmanager
import time
from datetime import datetime


class BroadcastStore:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS attempts (name TEXT PRIMARY KEY, at REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY, due REAL, '
                       'channel INTEGER, text TEXT, sender TEXT, local INTEGER, status TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, name, cooldown):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT at FROM attempts WHERE name=?', (name,)).fetchone()
            now = self.clock()
            if row and now - row[0] < cooldown:
                return False
            db.execute('INSERT OR REPLACE INTO attempts VALUES (?, ?)', (name, now))
            return True

    def schedule(self, when, channel, text, sender, local):
        try:
            date = datetime.fromisoformat(when.replace('Z', '+00:00'))
            if date.utcoffset() is None:
                raise ValueError()
            due = date.timestamp()
            if not self.clock() + 5 <= due <= self.clock() + 30 * 86400:
                raise ValueError()
        except (ValueError, TypeError, AttributeError, OverflowError):
            raise ValueError('Use an ISO timestamp with timezone, 5 seconds to 30 days ahead.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT count(*) FROM announcements WHERE status='pending'").fetchone()[0] >= 20:
                raise ValueError('Schedule is full (20 pending announcements).')
            cursor = db.execute('INSERT INTO announcements VALUES (NULL, ?, ?, ?, ?, ?, ?)',
                                (due, channel, text, sender, int(local), 'pending'))
            return cursor.lastrowid

    def pending(self):
        with self.connect() as db:
            return db.execute("SELECT id, due, channel, text FROM announcements WHERE status='pending' ORDER BY due").fetchall()

    def cancel(self, identity):
        with self.connect() as db:
            return db.execute("UPDATE announcements SET status='cancelled' WHERE id=? AND status='pending'",
                              (identity,)).rowcount == 1

    def claim_due(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id, due, channel, text, sender, local FROM announcements "
                             "WHERE status='pending' AND due<=? ORDER BY due, id LIMIT 1", (self.clock(),)).fetchone()
            if row:
                # Commit before touching the radio: a crash cannot replay this attempt.
                db.execute("UPDATE announcements SET status='claimed' WHERE id=?", (row[0],))
            return row

    def finish(self, identity, status):
        with self.connect() as db:
            db.execute('UPDATE announcements SET status=? WHERE id=?', (status, identity))
