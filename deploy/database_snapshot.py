"""Take/restore a private MySQL snapshot without exposing credentials in argv."""

import argparse
import gzip
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--confirm-database-restore", action="store_true")
    args = parser.parse_args()
    if args.operation == "restore" and not args.confirm_database_restore:
        parser.error("Restoring replaces database contents; use --confirm-database-restore only while the API is stopped.")
    os.chdir(args.backend.resolve())
    sys.path.insert(0, str(args.backend.resolve()))
    from app.core.config import settings
    from sqlalchemy.engine import make_url

    database = make_url(settings.DATABASE_URL)
    if database.get_backend_name() != "mysql" or not database.database:
        raise RuntimeError("Production snapshots require a configured MySQL database.")

    # MySQL option-file quoting prevents special password characters from
    # changing the syntax. Only the temporary path is visible in the process list.
    def quote(value):
        return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'

    descriptor, options_name = tempfile.mkstemp(prefix="mango-mysql-", suffix=".cnf")
    try:
        os.chmod(options_name, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as options:
            options.write("[client]\n")
            for key, value in {
                "host": database.host or "127.0.0.1",
                "port": database.port or 3306,
                "user": database.username or "",
                "password": database.password or "",
                "default-character-set": "utf8mb4",
            }.items():
                options.write(f"{key}={quote(value)}\n")
        snapshot = args.snapshot.resolve()
        if args.operation == "backup":
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            with snapshot.open("xb") as destination:
                os.chmod(snapshot, 0o600)
                process = subprocess.Popen(
                    ["mysqldump", f"--defaults-extra-file={options_name}",
                     "--single-transaction", "--no-tablespaces", "--set-gtid-purged=OFF",
                     "--hex-blob", database.database], stdout=subprocess.PIPE,
                )
                with gzip.GzipFile(fileobj=destination, mode="wb") as compressed:
                    while block := process.stdout.read(1024 * 1024):
                        compressed.write(block)
                result = process.wait()
                process.stdout.close()
            if result != 0:
                snapshot.unlink(missing_ok=True)
                raise RuntimeError("MySQL backup failed; deployment must not continue.")
            if snapshot.stat().st_size < 100:
                raise RuntimeError("MySQL backup is unexpectedly small.")
            with gzip.open(snapshot, "rb") as compressed:
                while compressed.read(1024 * 1024):
                    pass
        else:
            process = subprocess.Popen(
                ["mysql", f"--defaults-extra-file={options_name}", database.database],
                stdin=subprocess.PIPE,
            )
            with gzip.open(snapshot, "rb") as compressed:
                while block := compressed.read(1024 * 1024):
                    process.stdin.write(block)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError("MySQL restore failed; keep the API stopped and inspect the error.")
        print(f"Database {args.operation} completed: {snapshot}")
    finally:
        os.unlink(options_name)


if __name__ == "__main__":
    main()
