from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import re
import sqlite3
from typing import TextIO

from .cache import load_cached_report, store_cached_report


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
class ValueCount:
    value: str
    count: int


@dataclass(frozen=True)
class TableOverview:
    schema_name: str
    name: str
    row_count: int
    focus_column: str
    top_values: list[ValueCount]
    distinct_values: list[ValueCount]


@dataclass(frozen=True)
class SchemaOverview:
    name: str
    tables: list[TableOverview]


@dataclass(frozen=True)
class DatabaseReport:
    path: Path
    size_bytes: int
    objects: list[ObjectInfo]
    tables: list[TableOverview] = field(default_factory=list)
    schemas: list[SchemaOverview] = field(default_factory=list)


def analyze_database(file_path: str | Path) -> DatabaseReport:
    path = Path(file_path).expanduser().resolve()
    _ensure_readable_file(path)

    cached_report = load_cached_report(path)
    if cached_report is not None:
        return cached_report

    if path.suffix.lower() == ".sql":
        report = _analyze_sql_dump(path)
        store_cached_report(report)
        return report

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

    report = DatabaseReport(path=path, size_bytes=path.stat().st_size, objects=objects)
    store_cached_report(report)
    return report


def _analyze_sql_dump(path: Path) -> DatabaseReport:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            objects, tables, schemas = _read_objects_from_sql_dump_stream(handle)
    except OSError as exc:
        raise AnalysisError(f"Could not read SQL dump: {path}") from exc

    if not objects:
        raise AnalysisError("Could not extract database metadata from SQL dump")

    return DatabaseReport(path=path, size_bytes=path.stat().st_size, objects=objects, tables=tables, schemas=schemas)


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


def _read_objects_from_sql_dump_stream(handle: TextIO) -> tuple[list[ObjectInfo], list[TableOverview], list[SchemaOverview]]:
    objects: list[ObjectInfo] = []
    tables: dict[tuple[str, str], _TableAccumulator] = {}
    table_columns_by_name: dict[tuple[str, str], list[ColumnInfo]] = {}
    current_schema_name = "default"
    current_table_schema = current_schema_name
    current_table_name: str | None = None
    current_table_lines: list[str] = []
    inside_table = False
    current_insert_statement: list[str] = []
    inside_insert = False
    seen_views: set[str] = set()

    for raw_line in handle:
        line = raw_line.strip()

        schema_name = _match_use_schema_name(line)
        if schema_name is not None and not inside_table and not inside_insert:
            current_schema_name = schema_name
            continue

        database_name = _match_create_database_name(line)
        if database_name is not None and not inside_table and not inside_insert:
            current_schema_name = database_name
            continue

        if inside_table:
            current_table_lines.append(raw_line)
            if _is_end_of_mysql_table_definition(line):
                columns = _parse_mysql_table_columns("".join(current_table_lines))
                table_name = current_table_name or ""
                table_key = (current_table_schema, table_name)
                objects.append(ObjectInfo(name=table_name, object_type="table", columns=columns))
                table_columns_by_name[table_key] = columns
                tables[table_key] = _TableAccumulator(
                    schema_name=current_table_schema,
                    name=table_name,
                    focus_column=_choose_focus_column(columns),
                )
                current_table_name = None
                current_table_lines = []
                inside_table = False
            continue

        if inside_insert:
            current_insert_statement.append(raw_line)
            if line.endswith(";"):
                _process_insert_statement(
                    "".join(current_insert_statement),
                    current_schema_name,
                    table_columns_by_name,
                    tables,
                )
                current_insert_statement = []
                inside_insert = False
            continue

        table_name = _match_create_table_name(line)
        if table_name is not None:
            inside_table = True
            current_table_schema = current_schema_name
            current_table_name = table_name
            current_table_lines = []
            continue

        view_name = _match_create_view_name(line)
        if view_name is not None and view_name not in seen_views:
            seen_views.add(view_name)
            objects.append(ObjectInfo(name=view_name, object_type="view", columns=[]))
            continue

        insert_table_name = _match_insert_table_name(line)
        if insert_table_name is not None:
            inside_insert = True
            current_insert_statement = [raw_line]
            if line.endswith(";"):
                _process_insert_statement(
                    "".join(current_insert_statement),
                    current_schema_name,
                    table_columns_by_name,
                    tables,
                )
                current_insert_statement = []
                inside_insert = False

    objects.sort(key=lambda obj: (obj.object_type, obj.name))
    schema_map: dict[str, list[TableOverview]] = {}
    table_overviews = []
    for accumulator in sorted(tables.values(), key=lambda item: (item.schema_name, -item.row_count, item.name)):
        overview = accumulator.to_overview()
        table_overviews.append(overview)
        schema_map.setdefault(accumulator.schema_name, []).append(overview)

    schema_overviews = [
        SchemaOverview(name=schema_name, tables=schema_tables)
        for schema_name, schema_tables in schema_map.items()
    ]
    return objects, table_overviews, schema_overviews


def _match_create_table_name(line: str) -> str | None:
    match = re.match(r"CREATE\s+TABLE\s+`(?P<name>[^`]+)`\s*\(", line, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group("name")


def _match_create_view_name(line: str) -> str | None:
    match = re.match(
        r"CREATE\s+(?:ALGORITHM=.*?\s+)?VIEW\s+`(?P<name>[^`]+)`",
        line,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group("name")


def _match_create_database_name(line: str) -> str | None:
    match = re.match(
        r"CREATE\s+DATABASE(?:\s+IF\s+NOT\s+EXISTS)?\s+`?(?P<name>[^`\s;]+)`?",
        line,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group("name")


def _match_use_schema_name(line: str) -> str | None:
    match = re.match(r"USE\s+`?(?P<name>[^`\s;]+)`?;?", line, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group("name")


def _match_insert_table_name(line: str) -> str | None:
    match = re.match(r"INSERT\s+(?:IGNORE\s+)?INTO\s+`(?P<name>[^`]+)`", line, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group("name")


def _is_end_of_mysql_table_definition(line: str) -> bool:
    upper_line = line.upper()
    return line.startswith(")") and (
        "ENGINE=" in upper_line or line == ");" or line == ")"
    )


def _parse_mysql_table_columns(table_body: str) -> list[ColumnInfo]:
    columns: list[ColumnInfo] = []
    primary_key_columns = _extract_primary_key_columns(table_body)

    for line in table_body.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped.startswith("`"):
            continue

        column_match = re.match(r"`(?P<name>[^`]+)`\s+(?P<definition>.+)", stripped)
        if not column_match:
            continue

        name = column_match.group("name")
        definition = column_match.group("definition")
        data_type = _extract_mysql_data_type(definition)
        columns.append(
            ColumnInfo(
                name=name,
                data_type=data_type,
                not_null="NOT NULL" in definition.upper(),
                primary_key_position=primary_key_columns.get(name, 0),
            )
        )

    return columns


def _extract_primary_key_columns(table_body: str) -> dict[str, int]:
    match = re.search(r"PRIMARY\s+KEY\s*\((?P<columns>[^)]+)\)", table_body, flags=re.IGNORECASE)
    if not match:
        return {}

    primary_key_columns: dict[str, int] = {}
    for index, raw_name in enumerate(match.group("columns").split(","), start=1):
        cleaned_name = raw_name.strip().strip("`").split("(", 1)[0].strip()
        if cleaned_name:
            primary_key_columns[cleaned_name] = index

    return primary_key_columns


def _extract_mysql_data_type(definition: str) -> str:
    upper_definition = definition.upper()
    boundary_keywords = (
        " NOT NULL",
        " NULL",
        " DEFAULT ",
        " AUTO_INCREMENT",
        " COMMENT ",
        " COLLATE ",
        " CHARACTER SET ",
        " PRIMARY KEY",
        " UNIQUE ",
        " REFERENCES ",
        " CHECK ",
        " GENERATED ",
        " VIRTUAL",
        " STORED",
    )

    paren_depth = 0
    quote_char: str | None = None
    index = 0
    while index < len(definition):
        char = definition[index]
        if quote_char is not None:
            if char == quote_char and (index == 0 or definition[index - 1] != "\\"):
                quote_char = None
            index += 1
            continue

        if char in {"'", '"'}:
            quote_char = char
            index += 1
            continue

        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1

        if paren_depth == 0:
            for keyword in boundary_keywords:
                if upper_definition.startswith(keyword, index):
                    return definition[:index].strip()

        index += 1

    return definition.strip()


@dataclass
class _TableAccumulator:
    schema_name: str
    name: str
    focus_column: str
    row_count: int = 0
    top_values: Counter[str] = field(default_factory=Counter)

    def to_overview(self) -> TableOverview:
        distinct_values = [
            ValueCount(value=value, count=count)
            for value, count in self.top_values.most_common()
        ]
        return TableOverview(
            schema_name=self.schema_name,
            name=self.name,
            row_count=self.row_count,
            focus_column=self.focus_column,
            top_values=distinct_values[:5],
            distinct_values=distinct_values,
        )


def _process_insert_statement(
    statement: str,
    schema_name: str,
    table_columns_by_name: dict[str, list[ColumnInfo]],
    tables: dict[tuple[str, str], _TableAccumulator],
) -> None:
    match = re.match(
        r"INSERT\s+(?:IGNORE\s+)?INTO\s+`(?P<table>[^`]+)`\s*(?:\((?P<columns>.*?)\))?\s*VALUES\s*(?P<values>.*);\s*$",
        statement.strip(),
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return

    table_name = match.group("table")
    table_key = (schema_name, table_name)
    table_accumulator = tables.get(table_key)
    schema_columns = table_columns_by_name.get(table_key)
    if table_accumulator is None or schema_columns is None:
        return

    insert_columns = _parse_insert_columns(match.group("columns"), schema_columns)
    if table_accumulator.focus_column not in insert_columns:
        return

    focus_index = insert_columns.index(table_accumulator.focus_column)
    values_text = match.group("values")
    for row in _parse_mysql_insert_rows(values_text):
        table_accumulator.row_count += 1
        if focus_index >= len(row):
            continue
        value = _normalize_mysql_value(row[focus_index])
        if value is None or value == "":
            continue
        table_accumulator.top_values[value] += 1


def _parse_insert_columns(columns_text: str | None, schema_columns: list[ColumnInfo]) -> list[str]:
    if columns_text is None:
        return [column.name for column in schema_columns]

    return [match.group("name") for match in re.finditer(r"`(?P<name>[^`]+)`", columns_text)]


def _choose_focus_column(columns: list[ColumnInfo]) -> str:
    for column in columns:
        if column.primary_key_position:
            continue
        if _is_string_like_type(column.data_type):
            return column.name

    for column in columns:
        if not column.primary_key_position:
            return column.name

    return columns[0].name if columns else ""


def _is_string_like_type(data_type: str) -> bool:
    data_type_lower = data_type.lower()
    return any(keyword in data_type_lower for keyword in ("char", "text", "enum", "set", "json"))


def _parse_mysql_insert_rows(values_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    current_row: list[str] = []
    current_token: list[str] = []
    paren_depth = 0
    in_string = False
    quote_char: str | None = None
    escape_next = False

    for char in values_text:
        if in_string:
            current_token.append(char)
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == quote_char:
                in_string = False
            continue

        if char in {"'", '"'}:
            in_string = True
            quote_char = char
            current_token.append(char)
            continue

        if char == "(":
            paren_depth += 1
            if paren_depth > 1:
                current_token.append(char)
            continue

        if char == ")":
            if paren_depth > 1:
                current_token.append(char)
            paren_depth -= 1
            if paren_depth == 0:
                current_row.append("".join(current_token).strip())
                rows.append(current_row)
                current_row = []
                current_token = []
            continue

        if char == "," and paren_depth == 1:
            current_row.append("".join(current_token).strip())
            current_token = []
            continue

        if paren_depth >= 1:
            current_token.append(char)

    return rows


def _normalize_mysql_value(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value or value.upper() == "NULL":
        return None

    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return _unescape_mysql_string(value[1:-1])

    return value


def _unescape_mysql_string(value: str) -> str:
    replacements = {
        "\\0": "\x00",
        "\\b": "\b",
        "\\n": "\n",
        "\\r": "\r",
        "\\t": "\t",
        "\\Z": "\x1a",
        "\\'": "'",
        '\\\"': '"',
        "\\\\": "\\",
    }

    for source, target in replacements.items():
        value = value.replace(source, target)

    return value