from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from database_analyser.cli import main
from database_analyser.reporting import report_to_dict
from database_analyser import analyze_database


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

    def test_json_output_supports_sql_dump(self) -> None:
        sql_dump = """
        CREATE TABLE `device` (
          `eun` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`eun`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "dump.sql"
            dump_path.write_text(sql_dump)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(dump_path), "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["objects"][0]["name"], "device")

    def test_json_output_includes_tables(self) -> None:
        sql_dump = """
        CREATE TABLE `device` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        INSERT INTO `device` VALUES (1,'alpha'),(2,'alpha'),(3,'beta');
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "dump.sql"
            dump_path.write_text(sql_dump)
            report = analyze_database(dump_path)

        payload = report_to_dict(report)
        self.assertEqual(payload["tables"][0]["name"], "device")
        self.assertEqual(payload["tables"][0]["top_values"][0]["value"], "alpha")

    def test_json_output_includes_schemas(self) -> None:
        sql_dump = """
        CREATE DATABASE `schema_a`;
        USE `schema_a`;

        CREATE TABLE `device` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        INSERT INTO `device` VALUES (1,'alpha'),(2,'beta');
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "dump.sql"
            dump_path.write_text(sql_dump)
            report = analyze_database(dump_path)

        payload = report_to_dict(report)
        self.assertEqual(payload["schemas"][0]["name"], "schema_a")
        self.assertEqual(payload["schemas"][0]["tables"][0]["name"], "device")
        self.assertEqual(payload["schemas"][0]["tables"][0]["distinct_values"][0]["value"], "alpha")


if __name__ == "__main__":
    unittest.main()