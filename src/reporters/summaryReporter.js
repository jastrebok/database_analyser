function formatSummary(summary) {
  const tableNames = summary.tableNames.length > 0 ? summary.tableNames.join(', ') : 'none';

  return [
    `Tables: ${summary.tableCount}`,
    `Relationships: ${summary.relationshipCount}`,
    `Table names: ${tableNames}`
  ].join('\n');
}

module.exports = formatSummary;
