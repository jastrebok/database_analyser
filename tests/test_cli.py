from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from database_analyser.cli import main


class CliTests(unittest.TestCase):
    def test_json_output_contains_schema_information(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "example.sqlite"
            connection = sqlite3.connect(database_path)
            connection.execute("CREATE TABLE pv_entries (id INTEGER PRIMARY KEY, pv TEXT)")
            connection.commit()
            connection.close()

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(database_path), "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["objects"][0]["name"], "pv_entries")


if __name__ == "__main__":
    unittest.main()