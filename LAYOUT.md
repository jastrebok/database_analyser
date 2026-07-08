# Project Layout

Separate source code, public front end and media sections, allow execution of a predefined script.

## Project Purpose
I feed this a struct file and it tells me all about the database, draws diagrams and recongizes config_types - important in one of the schemas. Or lists registered PV entries (another type of content in a separate table).

## Top-Level Structure
| Path | Responsibility | Notes |
| --- | --- | --- |
| / | Describe the repository root | |

## Planned Directories And Files
List the folders and files you expect to exist, and what each one owns.

| Path | Type | Purpose |
| --- | --- | --- |
| src/ | directory | |
| README.md | file | |

## Data And Control Flow
Describe how data moves through the project and where the main entry points live.

## Constraints
Record any layout rules Copilot should preserve.

- Example: Keep database access under `src/data/`.
- Example: Keep CLI entry points under `src/cli/`.

## Open Decisions
Capture unresolved layout questions before large structural changes.

- Make a separate tests directory and also a place that is ignored for commits where I can upload the analyzed file.