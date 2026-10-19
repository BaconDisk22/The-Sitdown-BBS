"""Safe SQLite health checks and consistent online backups (no radio required)."""
import sqlite3
from pathlib import Path


def check_integrity(path):
    """Return SQLite integrity status without creating a missing database."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=5) as connection:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    return rows == [("ok",)], [row[0] for row in rows]


def backup_database(source, destination):
    """Copy a live SQLite database using the backup API, never raw file copying."""
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Backup destination must differ from source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True, timeout=5) as original:
        with sqlite3.connect(destination, timeout=5) as backup:
            original.backup(backup)
    valid, errors = check_integrity(destination)
    if not valid:
        raise sqlite3.DatabaseError("Backup integrity check failed: " + "; ".join(errors))
    return destination
