import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from sitdown_backup import create_backup_archive


class BackupArchiveTests(unittest.TestCase):
    def test_sqlite_and_config_are_saved_and_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / "bulletins.db"
            config = root / "config.ini"
            config.write_text("[bbs]\\nname=Sitdown\\n")
            with sqlite3.connect(database) as conn:
                conn.execute("CREATE TABLE messages (body TEXT)")
                conn.execute("INSERT INTO messages VALUES ('Ayyy')")
            archive_path = root / "export.zip"
            create_backup_archive(archive_path, [config], [database])
            with zipfile.ZipFile(archive_path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), {"config.ini", "bulletins.db"})
                restored = root / "restored.db"
                restored.write_bytes(archive.read("bulletins.db"))
            with sqlite3.connect(restored) as conn:
                self.assertEqual(conn.execute("SELECT body FROM messages").fetchone()[0], "Ayyy")

    def test_duplicate_filenames_do_not_replace_existing_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a").mkdir()
            (root / "b").mkdir()
            first = root / "a" / "config.ini"
            second = root / "b" / "config.ini"
            first.write_text("first")
            second.write_text("second")
            target = root / "backup.zip"
            target.write_bytes(b"existing archive")
            with self.assertRaises(ValueError):
                create_backup_archive(target, [first, second], [])
            self.assertEqual(target.read_bytes(), b"existing archive")
