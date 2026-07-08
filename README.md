# database_analyser

Minimal database inspection tool for local schema analysis.

## What It Does Today

- accepts a database file path
- verifies the file exists and is readable
- opens the database in read-only mode
- extracts basic schema information such as tables, views, and columns

## Project Structure

- `src/database_analyser/` contains the Python package and CLI
- `tests/` contains the initial test coverage
- `public/` is reserved for future front-end assets
- `media/` is reserved for generated diagrams or related media
- `analysis_inputs/` is ignored and intended for local database files

## Run

```bash
python3 -m database_analyser /path/to/database.sqlite
```

Or via the helper script:

```bash
./scripts/analyse-db.sh /path/to/database.sqlite
```

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```