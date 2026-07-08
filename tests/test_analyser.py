from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from database_analyser import AnalysisError, analyze_database


class AnalyzeDatabaseTests(unittest.TestCase):
    def test_extracts_tables_and_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "example.sqlite"
            connection = sqlite3.connect(database_path)
            connection.execute(
                "CREATE TABLE config_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.execute("CREATE VIEW config_type_names AS SELECT name FROM config_types")
            connection.commit()
            connection.close()

            report = analyze_database(database_path)

        self.assertEqual(report.path, database_path.resolve())
        self.assertEqual([obj.name for obj in report.objects], ["config_types", "config_type_names"])
        self.assertEqual(report.objects[0].columns[0].name, "id")
        self.assertEqual(report.objects[0].columns[1].name, "name")

    def test_rejects_missing_file(self) -> None:
        with self.assertRaises(AnalysisError):
            analyze_database("/tmp/this-file-should-not-exist.sqlite")


if __name__ == "__main__":
    unittest.main()