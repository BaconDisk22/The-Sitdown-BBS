"""Read-only preflight for Sitdown backup ZIP files before any future restore."""
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from sitdown_db_health import check_integrity


def inspect_backup_archive(path):
    """Validate archive contents without writing to live BBS paths."""
    path = Path(path)
    with zipfile.ZipFile(path, "r") as archive:
        entries = archive.infolist()
        if not entries:
            raise ValueError("Backup archive is empty")
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError("Backup archive has duplicate entries")
        for entry in entries:
            name = entry.filename
            if (entry.is_dir() or name in (".", "..") or
                    "/" in name or "\\" in name or
                    Path(name).name != name):
                raise ValueError("Backup archive contains an unsafe path")
            if not name.endswith((".db", ".ini", ".json")):
                raise ValueError("Backup archive contains an unexpected file type")
            if entry.file_size > 512 * 1024 * 1024:
                raise ValueError("Backup archive contains an oversized file")
        if archive.testzip() is not None:
            raise ValueError("Backup archive failed checksum verification")
        with tempfile.TemporaryDirectory(prefix="sitdown-restore-check-") as temp:
            databases = []
            for entry in entries:
                if entry.filename.endswith(".db"):
                    target = Path(temp) / entry.filename
                    with archive.open(entry) as source, target.open("wb") as output:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            output.write(block)
                    valid, errors = check_integrity(target)
                    if not valid:
                        raise sqlite3.DatabaseError("Backup SQLite integrity check failed: " + "; ".join(errors))
                    databases.append(entry.filename)
    return {"files": names, "databases": databases, "valid": True}
