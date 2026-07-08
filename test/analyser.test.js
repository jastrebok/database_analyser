const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { analyzeDatabaseStructure } = require('../src/analyser');
const { run } = require('../src/cli');

test('analyzeDatabaseStructure handles explicit tables array', () => {
  const input = {
    tables: [
      {
        name: 'users',
        columns: ['id', 'email'],
        rows: [
          { id: 1, email: 'a@example.com' },
          { id: 2, email: '' },
        ],
      },
    ],
  };

  const result = analyzeDatabaseStructure(input);

  assert.equal(result.totalTables, 1);
  assert.equal(result.totalRows, 2);
  assert.deepEqual(result.tables[0].columns, ['id', 'email']);
  assert.equal(result.tables[0].emptyRows, 0);
});

test('analyzeDatabaseStructure supports map-like table objects and infers columns', () => {
  const input = {
    tables: {
      orders: {
        data: [
          { id: 10, total: 42 },
          { id: 11, total: 22 },
        ],
      },
    },
  };

  const result = analyzeDatabaseStructure(input);

  assert.equal(result.totalTables, 1);
  assert.equal(result.totalRows, 2);
  assert.equal(result.tables[0].name, 'orders');
  assert.deepEqual(result.tables[0].columns, ['id', 'total']);
});

test('run reads file and returns analysis', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'db-analyser-'));
  const inputPath = path.join(tempDir, 'db.json');

  fs.writeFileSync(
    inputPath,
    JSON.stringify({
      users: {
        rows: [{ id: 1, name: 'Ada' }],
      },
    }),
  );

  const result = run([inputPath]);

  assert.equal(result.totalTables, 1);
  assert.equal(result.tables[0].name, 'users');
  assert.equal(result.tables[0].rowCount, 1);
});
