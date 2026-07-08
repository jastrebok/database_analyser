# database_analyser

Minimal database inspection tool for local schema analysis.

## What It Does Today

- accepts a database file path
- verifies the file exists and is readable
- opens SQLite databases in read-only mode
- extracts basic schema information such as tables, views, and columns
- reads MySQL-style `.sql` dump files and extracts table/view definitions directly
- counts the most frequent values for each table's focus column
- groups tables into schema tabs and shows each table in its own tab
- collects all distinct values for the selected table's categorical focus column
- caches analysis results on disk so reopening the same file is fast in later sessions

## Project Structure

- `src/database_analyser/` contains the Python package and CLI
- `tests/` contains the initial test coverage
- `public/` is reserved for future front-end assets
- `media/` is reserved for generated diagrams or related media
- `analysis_inputs/` is ignored and intended for local database files

## Run

```bash
python3 -m database_analyser /path/to/database.sqlite
python3 -m database_analyser /path/to/dump.sql
database-analyser-web /path/to/dump.sql
```

The web view shows schema tabs first, then table tabs within the selected schema, and renders each table's distinct values plus a radar chart.

Or via the helper script:

```bash
./scripts/analyse-db.sh /path/to/database.sqlite
```

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```