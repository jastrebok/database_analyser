from __future__ import annotations

import argparse
import json
from typing import Sequence

from .analyser import AnalysisError, DatabaseReport, analyze_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="database-analyser",
        description="Verify a database file is readable and extract basic schema metadata.",
    )
    parser.add_argument("database_path", help="Path to the database file to inspect")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the extracted report as JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = analyze_database(args.database_path)
    except AnalysisError as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")

    if args.json:
        print(json.dumps(_report_to_dict(report), indent=2))
    else:
        print(_format_text_report(report))

    return 0


def _report_to_dict(report: DatabaseReport) -> dict[str, object]:
    return {
        "path": str(report.path),
        "size_bytes": report.size_bytes,
        "objects": [
            {
                "name": obj.name,
                "type": obj.object_type,
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
    }


def _format_text_report(report: DatabaseReport) -> str:
    lines = [
        f"Database: {report.path}",
        f"Size: {report.size_bytes} bytes",
        f"Objects: {len(report.objects)}",
    ]

    for obj in report.objects:
        lines.append(f"- {obj.object_type}: {obj.name} ({len(obj.columns)} columns)")
        for column in obj.columns:
            fragments = [column.name]
            if column.data_type:
                fragments.append(column.data_type)
            if column.primary_key_position:
                fragments.append(f"pk={column.primary_key_position}")
            if column.not_null:
                fragments.append("not-null")
            lines.append(f"  - {' | '.join(fragments)}")

    return "\n".join(lines)