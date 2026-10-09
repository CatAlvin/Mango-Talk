"""Offline regression checks for credential handling and backup failure paths."""

import contextlib
import gzip
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from sqlalchemy.engine import make_url  # Load platform-dependent imports before mocking subprocess.


SPEC = importlib.util.spec_from_file_location("database_snapshot", Path(__file__).with_name("database_snapshot.py"))
snapshot_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot_tool)


class FakePipe(io.BytesIO):
    def close(self):
        self.closed_value = self.getvalue()
        super().close()


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.initial_directory = Path.cwd()
        self.temporary = tempfile.TemporaryDirectory(prefix="mango-snapshot-test-")
        self.directory = Path(self.temporary.name)
        self.backend = self.directory / "backend"
        self.backend.mkdir()
        self.output = self.directory / "database.sql.gz"
        self.fake_config = types.ModuleType("app.core.config")
        self.fake_config.settings = types.SimpleNamespace(
            DATABASE_URL="mysql+pymysql://reader:p%23%22%5Cword@127.0.0.1:3306/actual_database",
        )
        self.payload = b"-- test dump\n" + b"\n".join(
            f"INSERT INTO messages VALUES ({i}, 'message {i * 71}');".encode() for i in range(100)
        )
        self.commands = []
        self.option_paths = []
        self.processes = []

    def tearDown(self):
        os.chdir(self.initial_directory)
        sys.path[:] = [entry for entry in sys.path if entry != str(self.backend)]
        self.temporary.cleanup()

    def process(self, command, **kwargs):
        self.commands.append(command)
        self.assertNotIn("p#", " ".join(command))
        options = Path(command[1].split("=", 1)[1])
        self.option_paths.append(options)
        content = options.read_text()
        self.assertIn('password="p#\\"\\\\word"', content)
        self.assertEqual(command[-1], "actual_database")
        process = types.SimpleNamespace(
            stdout=io.BytesIO(self.payload), stdin=FakePipe(), wait=lambda: 0,
        )
        self.processes.append(process)
        return process

    def run_tool(self, operation, *extra, process=None):
        arguments = ["database_snapshot.py", operation, "--backend", str(self.backend), "--snapshot", str(self.output), *extra]
        with patch.dict(sys.modules, {"app.core.config": self.fake_config}), patch.object(sys, "argv", arguments), patch.object(snapshot_tool.subprocess, "Popen", process or self.process), contextlib.redirect_stdout(io.StringIO()):
            snapshot_tool.main()

    def test_snapshot_round_trip_and_private_option_cleanup(self):
        self.run_tool("backup")
        with gzip.open(self.output, "rb") as source:
            self.assertEqual(source.read(), self.payload)
        self.run_tool("restore", "--confirm-database-restore")
        self.assertEqual(self.processes[-1].stdin.closed_value, self.payload)
        self.assertTrue(all(not path.exists() for path in self.option_paths))
        self.assertIn("--single-transaction", self.commands[0])

    def test_failed_dump_is_not_kept_as_a_valid_snapshot(self):
        def failing_process(command, **kwargs):
            process = self.process(command, **kwargs)
            process.wait = lambda: 1
            return process

        with self.assertRaisesRegex(RuntimeError, "backup failed"):
            self.run_tool("backup", process=failing_process)
        self.assertFalse(self.output.exists())
        self.assertTrue(all(not path.exists() for path in self.option_paths))

    def test_restore_requires_explicit_database_restore_flag(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            self.run_tool("restore")
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.commands, [])

    def test_existing_snapshot_is_never_overwritten(self):
        self.output.write_bytes(b"existing checkpoint")
        with self.assertRaises(FileExistsError):
            self.run_tool("backup")
        self.assertEqual(self.output.read_bytes(), b"existing checkpoint")


if __name__ == "__main__":
    unittest.main()
