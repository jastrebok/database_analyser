const test = require('node:test');
const assert = require('node:assert/strict');

const { createAnalyser, formatSummary } = require('../src');

test('database analyser returns schema summary counts', () => {
  const analyser = createAnalyser();
  const summary = analyser.analyse({
    tables: [{ name: 'users' }, { name: 'orders' }],
    relationships: [{ from: 'orders', to: 'users' }]
  });

  assert.deepEqual(summary, {
    tableCount: 2,
    relationshipCount: 1,
    tableNames: ['users', 'orders']
  });
});

test('summary reporter renders a readable report', () => {
  const output = formatSummary({
    tableCount: 1,
    relationshipCount: 0,
    tableNames: ['users']
  });

  assert.equal(output, 'Tables: 1\nRelationships: 0\nTable names: users');
});
