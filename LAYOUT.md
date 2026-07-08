# Project Layout

Separate source code, public front end and media sections, allow execution of a predefined script.

## Project Purpose
I feed this a struct file and it tells me all about the database, draws diagrams and recongizes config_types - important in one of the schemas. Or lists registered PV entries (another type of content in a separate table).

## Top-Level Structure
| Path | Responsibility | Notes |
| --- | --- | --- |
| / | Project root for the CLI analyzer, docs and helper scripts | Keep root files limited to project metadata and entry helpers |

## Planned Directories And Files
List the folders and files you expect to exist, and what each one owns.

| Path | Type | Purpose |
| --- | --- | --- |
| src/ | directory | Python package source for database inspection and future analysis logic |
| tests/ | directory | Automated tests for the analyzer and CLI |
| scripts/ | directory | Helper scripts to run common project actions |
| public/ | directory | Reserved front-end/static assets area |
| media/ | directory | Reserved generated diagrams and media output area |
| .cache/database_analyser/ | directory | Disk cache for parsed reports and frequent-value summaries |
| analysis_inputs/ | directory | Local ignored area for uploaded or copied databases to inspect |
| README.md | file | Project overview and local usage instructions |
| pyproject.toml | file | Python project metadata and CLI entry point |
| public/index.html | file | Web UI shell for the table overview and radar charts |
| public/app.js | file | Front-end logic that renders the extracted report |
| public/styles.css | file | Visual styling for the web front end |

## Data And Control Flow
Describe how data moves through the project and where the main entry points live.

The main entry point is the CLI in `src/database_analyser/cli.py`.
The user passes a database file path.
The CLI verifies readability, opens the database in read-only mode, and asks the analyzer layer to extract schema metadata.
The analyzer returns a structured report that can later feed diagrams, a front end, or more specialized schema inspection.
The web entry point in `src/database_analyser/web.py` serves the report to the static files in `public/`.
The UI is organized as schema tabs first, then table tabs, with the selected table showing all distinct values for its focus column.

## Constraints
Record any layout rules Copilot should preserve.

- Keep database inspection logic under `src/database_analyser/`.
- Keep helper shell entry points under `scripts/`.
- Keep local uploaded databases under `analysis_inputs/` and out of git.
- Keep future generated diagrams or exports under `media/`.
- Keep the browser-facing UI assets under `public/`.
- Keep parsed-report cache entries under `.cache/database_analyser/` and out of git.
- Keep schema grouping stable so the front end can render tabs without recomputing the dump.

## Open Decisions
Capture unresolved layout questions before large structural changes.

- Decide whether the future front end should stay static in `public/` or move into its own application directory.
- Decide where diagram generation code should live once extraction expands beyond schema summaries.