"""Offline SQLite reliability tests; no Meshtastic hardware required."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from sitdown_db_health import check_integrity, backup_database


class DatabaseHealthTests(unittest.TestCase):
    def test_integrity_and_consistent_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "bulletins.db"
            destination = Path(folder) / "backup.db"
            with sqlite3.connect(source) as conn:
                conn.execute("CREATE TABLE mail (body TEXT)")
                conn.execute("INSERT INTO mail VALUES (?)", ("Jersey test message",))
            self.assertEqual(check_integrity(source), (True, ["ok"]))
            backup_database(source, destination)
            self.assertEqual(check_integrity(destination), (True, ["ok"]))
            with sqlite3.connect(destination) as conn:
                self.assertEqual(conn.execute("SELECT body FROM mail").fetchone()[0], "Jersey test message")

    def test_missing_db_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                check_integrity(missing)
            with self.assertRaises(FileNotFoundError):
                backup_database(missing, Path(folder) / "backup.db")
            self.assertFalse(missing.exists())

    def test_backup_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "bulletins.db"
            with sqlite3.connect(source) as conn:
                conn.execute("CREATE TABLE mail (body TEXT)")
            with self.assertRaises(ValueError):
                backup_database(source, source)
            self.assertTrue(check_integrity(source)[0])
