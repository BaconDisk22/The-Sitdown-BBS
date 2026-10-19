"""Create complete BBS ZIP archives using consistent SQLite snapshots."""
import os
from pathlib import Path
import tempfile
import zipfile

from sitdown_db_health import backup_database


def create_backup_archive(destination, config_files, database_files):
    """Build a verified archive atomically; never raw-copy an active SQLite file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    configs = [Path(p) for p in config_files if Path(p).is_file()]
    databases = [Path(p) for p in database_files if Path(p).is_file()]
    used = set()
    with tempfile.TemporaryDirectory(prefix="sitdown-backup-") as workspace:
        workspace = Path(workspace)
        staging = workspace / "archive.zip"
        with zipfile.ZipFile(staging, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in [*configs, *databases]:
                name = source.name
                if name in used:
                    raise ValueError(f"Duplicate backup filename: {name}")
                used.add(name)
                if source.suffix.lower() == ".db":
                    snapshot = workspace / name
                    backup_database(source, snapshot)
                    archive.write(snapshot, name)
                else:
                    archive.write(source, name)
        with zipfile.ZipFile(staging) as archive:
            if archive.testzip() is not None:
                raise ValueError("Backup archive verification failed")
        # Stage on the destination filesystem before replacing the target.
        fd, temp_path = tempfile.mkstemp(prefix=".sitdown-", suffix=".zip", dir=destination.parent)
        os.close(fd)
        try:
            with open(staging, "rb") as src, open(temp_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
            os.replace(temp_path, destination)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    return destination
