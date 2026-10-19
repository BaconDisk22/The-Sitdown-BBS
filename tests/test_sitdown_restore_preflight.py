import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from sitdown_backup import create_backup_archive
from sitdown_restore_preflight import inspect_backup_archive


class RestorePreflightTests(unittest.TestCase):
    def test_valid_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "bulletins.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE messages (body TEXT)")
                conn.execute("INSERT INTO messages VALUES ('Ayyy')")
            target = root / "backup.zip"
            create_backup_archive(target, [], [db])
            result = inspect_backup_archive(target)
            self.assertTrue(result["valid"])
            self.assertEqual(result["databases"], ["bulletins.db"])
            self.assertTrue(db.exists())

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("../config.ini", "unsafe")
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                inspect_backup_archive(target)

    def test_corrupt_database_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "corrupt.zip"
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("bulletins.db", "not sqlite")
            with self.assertRaises(sqlite3.DatabaseError):
                inspect_backup_archive(target)

    def test_duplicate_entries_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "duplicate.zip"
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("config.ini", "one")
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr("config.ini", "two")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                inspect_backup_archive(target)
