from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any

from typing import TYPE_CHECKING

CACHE_VERSION = 4

if TYPE_CHECKING:
    from .analyser import DatabaseReport, ValueCount, ColumnInfo, ObjectInfo, SchemaOverview, TableOverview


def get_cache_dir() -> Path:
    override = os.environ.get("DATABASE_ANALYSER_CACHE_DIR")
    if override:
        return Path(override).expanduser()

    return Path(__file__).resolve().parents[2] / ".cache" / "database_analyser"


def load_cached_report(source_path: Path) -> DatabaseReport | None:
    cache_file = _cache_file_for(source_path)
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except OSError:
        return None
    except json.JSONDecodeError:
        return None

    if payload.get("version") != CACHE_VERSION:
        return None

    if payload.get("signature") != _build_signature(source_path):
        return None

    report_data = payload.get("report")
    if not isinstance(report_data, dict):
        return None

    return _report_from_dict(report_data)


def store_cached_report(report: DatabaseReport) -> None:
    cache_file = _cache_file_for(report.path)
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CACHE_VERSION,
            "signature": _build_signature(report.path),
            "report": _report_to_dict(report),
        }
        cache_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        return


def _cache_file_for(source_path: Path) -> Path:
    digest = _stable_key(source_path)
    return get_cache_dir() / f"{digest}.json"


def _stable_key(source_path: Path) -> str:
    return str(source_path.resolve()).replace("/", "_").replace(":", "_")


def _build_signature(source_path: Path) -> dict[str, Any]:
    stat_result = source_path.stat()
    return {
        "path": str(source_path.resolve()),
        "size_bytes": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
    }


def _report_to_dict(report: DatabaseReport) -> dict[str, Any]:
    return {
        "path": str(report.path),
        "size_bytes": report.size_bytes,
        "objects": [
            {
                "name": obj.name,
                "object_type": obj.object_type,
                "columns": [
                    {
                        "name": column.name,
                        "data_type": column.data_type,
                        "not_null": column.not_null,
                        "primary_key_position": column.primary_key_position,
                    }
                    for column in obj.columns
                ],
            }
            for obj in report.objects
        ],
        "tables": [
            {
                "schema_name": table.schema_name,
                "name": table.name,
                "row_count": table.row_count,
                "focus_column": table.focus_column,
                "top_values": [
                    {"value": item.value, "count": item.count}
                    for item in table.top_values
                ],
                "distinct_values": [
                    {"value": item.value, "count": item.count}
                    for item in table.distinct_values
                ],
            }
            for table in report.tables
        ],
        "schemas": [
            {
                "name": schema.name,
                "tables": [
                    {
                        "schema_name": table.schema_name,
                        "name": table.name,
                        "row_count": table.row_count,
                        "focus_column": table.focus_column,
                        "top_values": [
                            {"value": item.value, "count": item.count}
                            for item in table.top_values
                        ],
                        "distinct_values": [
                            {"value": item.value, "count": item.count}
                            for item in table.distinct_values
                        ],
                    }
                    for table in schema.tables
                ],
            }
            for schema in report.schemas
        ],
    }


def _report_from_dict(payload: dict[str, Any]) -> DatabaseReport:
    from .analyser import ColumnInfo, DatabaseReport, ObjectInfo, SchemaOverview, TableOverview, ValueCount

    objects = [
        ObjectInfo(
            name=str(item["name"]),
            object_type=str(item.get("object_type", item.get("type", ""))),
            columns=[
                ColumnInfo(
                    name=str(column["name"]),
                    data_type=str(column.get("data_type", "")),
                    not_null=bool(column.get("not_null", False)),
                    primary_key_position=int(column.get("primary_key_position", 0)),
                )
                for column in item.get("columns", [])
            ],
        )
        for item in payload.get("objects", [])
    ]

    tables = [
        TableOverview(
            schema_name=str(item.get("schema_name", "default")),
            name=str(item["name"]),
            row_count=int(item.get("row_count", 0)),
            focus_column=str(item.get("focus_column", "")),
            top_values=[
                ValueCount(value=str(value["value"]), count=int(value.get("count", 0)))
                for value in item.get("top_values", [])
            ],
            distinct_values=[
                ValueCount(value=str(value["value"]), count=int(value.get("count", 0)))
                for value in item.get("distinct_values", item.get("top_values", []))
            ],
        )
        for item in payload.get("tables", [])
    ]

    schemas_payload = payload.get("schemas")
    if isinstance(schemas_payload, list) and schemas_payload:
        schemas = [
            SchemaOverview(
                name=str(item.get("name", "default")),
                tables=[
                    TableOverview(
                        schema_name=str(table.get("schema_name", item.get("name", "default"))),
                        name=str(table["name"]),
                        row_count=int(table.get("row_count", 0)),
                        focus_column=str(table.get("focus_column", "")),
                        top_values=[
                            ValueCount(value=str(value["value"]), count=int(value.get("count", 0)))
                            for value in table.get("top_values", [])
                        ],
                        distinct_values=[
                            ValueCount(value=str(value["value"]), count=int(value.get("count", 0)))
                            for value in table.get("distinct_values", table.get("top_values", []))
                        ],
                    )
                    for table in item.get("tables", [])
                ],
            )
            for item in schemas_payload
        ]
    else:
        grouped: dict[str, list[TableOverview]] = {}
        for table in tables:
            grouped.setdefault(table.schema_name, []).append(table)
        schemas = [SchemaOverview(name=name, tables=grouped_tables) for name, grouped_tables in grouped.items()]

    return DatabaseReport(
        path=Path(str(payload["path"])),
        size_bytes=int(payload.get("size_bytes", 0)),
        objects=objects,
        tables=tables,
        schemas=schemas,
    )