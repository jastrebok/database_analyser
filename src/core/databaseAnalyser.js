class DatabaseAnalyser {
  analyse(schema = {}) {
    const tables = Array.isArray(schema.tables) ? schema.tables : [];
    const relationships = Array.isArray(schema.relationships) ? schema.relationships : [];

    return {
      tableCount: tables.length,
      relationshipCount: relationships.length,
      tableNames: tables.map((table) => table.name).filter(Boolean)
    };
  }
}

module.exports = DatabaseAnalyser;
