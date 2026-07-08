from __future__ import annotations

from pathlib import Path
from unittest import mock
import sqlite3
import tempfile
import unittest
import os

from database_analyser import AnalysisError, analyze_database
from database_analyser.cache import get_cache_dir


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

    def test_extracts_tables_from_mysql_dump(self) -> None:
        sql_dump = """
        CREATE TABLE `config_types` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE TABLE `pv_entries` (
          `id` bigint NOT NULL,
          `pv_name` varchar(255) DEFAULT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        CREATE ALGORITHM=UNDEFINED VIEW `pv_names` AS
        SELECT `pv_entries`.`pv_name` AS `pv_name`
        FROM `pv_entries`;
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "dump.sql"
            dump_path.write_text(sql_dump)

            report = analyze_database(dump_path)

        self.assertEqual([obj.name for obj in report.objects], ["config_types", "pv_entries", "pv_names"])
        self.assertEqual(report.objects[0].columns[0].name, "id")
        self.assertEqual(report.objects[0].columns[0].primary_key_position, 1)
        self.assertEqual(report.objects[0].columns[1].name, "name")

    def test_extracts_frequent_values_from_mysql_dump(self) -> None:
        sql_dump = """
        CREATE TABLE `device` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          `status` varchar(50) DEFAULT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        INSERT INTO `device` VALUES
        (1,'alpha','up'),
        (2,'alpha','down'),
        (3,'beta','up'),
        (4,'alpha','up');
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "dump.sql"
            dump_path.write_text(sql_dump)

            report = analyze_database(dump_path)

        self.assertEqual(report.tables[0].name, "device")
        self.assertEqual(report.tables[0].focus_column, "name")
        self.assertEqual(report.tables[0].row_count, 4)
        self.assertEqual(report.tables[0].top_values[0].value, "alpha")
        self.assertEqual(report.tables[0].top_values[0].count, 3)

        def test_groups_tables_by_schema_and_keeps_distinct_values(self) -> None:
                sql_dump = """
                CREATE DATABASE `schema_a`;
                USE `schema_a`;

                CREATE TABLE `device` (
                    `id` int NOT NULL,
                    `name` varchar(255) NOT NULL,
                    PRIMARY KEY (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

                INSERT INTO `device` VALUES
                (1,'alpha'),
                (2,'beta'),
                (3,'alpha');

                CREATE DATABASE `schema_b`;
                USE `schema_b`;

                CREATE TABLE `sensor` (
                    `id` int NOT NULL,
                    `category` varchar(255) NOT NULL,
                    PRIMARY KEY (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

                INSERT INTO `sensor` VALUES
                (1,'x'),
                (2,'y');
                """

                with tempfile.TemporaryDirectory() as temp_dir:
                        dump_path = Path(temp_dir) / "dump.sql"
                        dump_path.write_text(sql_dump)

                        report = analyze_database(dump_path)

                self.assertEqual([schema.name for schema in report.schemas], ["schema_a", "schema_b"])
                self.assertEqual(report.schemas[0].tables[0].name, "device")
                self.assertEqual(report.schemas[0].tables[0].distinct_values[0].value, "alpha")
                self.assertEqual(report.schemas[0].tables[0].distinct_values[0].count, 2)
                self.assertEqual(report.schemas[1].tables[0].name, "sensor")
                self.assertEqual(report.schemas[1].tables[0].distinct_values[0].value, "x")

    def test_reuses_cached_sql_dump_report(self) -> None:
        sql_dump = """
        CREATE TABLE `device` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        INSERT INTO `device` VALUES (1,'alpha'),(2,'alpha'),(3,'beta');
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            with mock.patch.dict(os.environ, {"DATABASE_ANALYSER_CACHE_DIR": str(cache_dir)}):
                dump_path = Path(temp_dir) / "dump.sql"
                dump_path.write_text(sql_dump)

                first_report = analyze_database(dump_path)

                with mock.patch("database_analyser.analyser._analyze_sql_dump", side_effect=AssertionError("cache miss")):
                    second_report = analyze_database(dump_path)

        self.assertEqual(first_report.tables[0].top_values[0].value, "alpha")
        self.assertEqual(second_report.tables[0].top_values[0].count, 2)

    def test_invalidates_cache_when_file_changes(self) -> None:
        sql_dump = """
        CREATE TABLE `device` (
          `id` int NOT NULL,
          `name` varchar(255) NOT NULL,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

        INSERT INTO `device` VALUES (1,'alpha'),(2,'beta');
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            with mock.patch.dict(os.environ, {"DATABASE_ANALYSER_CACHE_DIR": str(cache_dir)}):
                dump_path = Path(temp_dir) / "dump.sql"
                dump_path.write_text(sql_dump)
                first_report = analyze_database(dump_path)

                dump_path.write_text(sql_dump + "\nINSERT INTO `device` VALUES (3,'alpha');\n")
                second_report = analyze_database(dump_path)

        self.assertEqual(first_report.tables[0].row_count, 2)
        self.assertEqual(second_report.tables[0].row_count, 3)


if __name__ == "__main__":
    unittest.main()