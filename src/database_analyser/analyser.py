from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


class AnalysisError(Exception):
    """Raised when a database file cannot be analyzed."""


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    not_null: bool
    primary_key_position: int


@dataclass(frozen=True)
class ObjectInfo:
    name: str
    object_type: str
    columns: list[ColumnInfo]


@dataclass(frozen=True)
class DatabaseReport:
    path: Path
    size_bytes: int
    objects: list[ObjectInfo]


def analyze_database(file_path: str | Path) -> DatabaseReport:
    path = Path(file_path).expanduser().resolve()
    _ensure_readable_file(path)

    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise AnalysisError(f"Could not open database in read-only mode: {exc}") from exc

    try:
        objects = _read_objects(connection)
    except sqlite3.Error as exc:
        raise AnalysisError(f"Could not extract database metadata: {exc}") from exc
    finally:
        connection.close()

    return DatabaseReport(path=path, size_bytes=path.stat().st_size, objects=objects)


def _ensure_readable_file(path: Path) -> None:
    if not path.exists():
        raise AnalysisError(f"File does not exist: {path}")
    if not path.is_file():
        raise AnalysisError(f"Path is not a file: {path}")

    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise AnalysisError(f"File is not readable: {path}") from exc


def _read_objects(connection: sqlite3.Connection) -> list[ObjectInfo]:
    object_rows = connection.execute(
        """
        SELECT type, name
        FROM sqlite_master
        WHERE type IN ('table', 'view')
          AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()

    objects: list[ObjectInfo] = []
    for object_type, name in object_rows:
        pragma_name = name.replace("'", "''")
        column_rows = connection.execute(f"PRAGMA table_info('{pragma_name}')").fetchall()
        columns = [
            ColumnInfo(
                name=row[1],
                data_type=row[2] or "",
                not_null=bool(row[3]),
                primary_key_position=int(row[5]),
            )
            for row in column_rows
        ]
        objects.append(ObjectInfo(name=name, object_type=object_type, columns=columns))

    return objects