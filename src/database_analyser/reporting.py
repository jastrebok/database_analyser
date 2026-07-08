from __future__ import annotations

from .analyser import DatabaseReport


def report_to_dict(report: DatabaseReport) -> dict[str, object]:
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