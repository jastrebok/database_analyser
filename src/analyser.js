function normalizeColumnName(column) {
  return typeof column === 'string' ? column : column && column.name;
}

function inferColumns(rows) {
  const names = new Set();

  for (const row of rows) {
    if (row && typeof row === 'object' && !Array.isArray(row)) {
      for (const key of Object.keys(row)) {
        names.add(key);
      }
    }
  }

  return [...names];
}

function getTables(input) {
  if (!input || typeof input !== 'object') {
    throw new Error('Database structure must be an object');
  }

  if (Array.isArray(input.tables)) {
    return input.tables;
  }

  if (input.tables && typeof input.tables === 'object') {
    return Object.entries(input.tables).map(([name, table]) => ({ name, ...table }));
  }

  return Object.entries(input).map(([name, table]) => ({ name, ...table }));
}

function analyzeDatabaseStructure(input) {
  const tables = getTables(input).map((table, index) => {
    const rows = Array.isArray(table.rows)
      ? table.rows
      : Array.isArray(table.data)
        ? table.data
        : [];

    const columns = Array.isArray(table.columns)
      ? table.columns.map(normalizeColumnName).filter(Boolean)
      : inferColumns(rows);

    return {
      name: table.name || `table_${index + 1}`,
      rowCount: rows.length,
      columnCount: columns.length,
      columns,
      emptyRows: rows.filter((row) => {
        if (!row || typeof row !== 'object' || Array.isArray(row)) {
          return false;
        }

        const values = Object.values(row);
        return (
          values.length > 0 &&
          values.every((value) => value === null || value === undefined || value === '')
        );
      }).length,
    };
  });

  return {
    totalTables: tables.length,
    totalRows: tables.reduce((sum, table) => sum + table.rowCount, 0),
    tables,
  };
}

module.exports = {
  analyzeDatabaseStructure,
  inferColumns,
};
