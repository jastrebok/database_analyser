# database_analyser

A Node.js CLI for analyzing database content from an imported structure file that also contains table data.

## Setup

```bash
npm install
```

## Usage

```bash
npm start -- /absolute/path/to/database-struct.json
```

Supported input shapes:

- `{ "tables": [ { "name": "users", "columns": [...], "rows": [...] } ] }`
- `{ "tables": { "users": { "rows": [...] } } }`
- `{ "users": { "rows": [...] }, "orders": { "data": [...] } }`

The CLI prints a JSON summary with table counts, row counts, inferred columns, and empty-row counts.

## Test

```bash
npm test
```
