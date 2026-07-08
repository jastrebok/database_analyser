#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { analyzeDatabaseStructure } = require('./analyser');

function loadDatabaseFile(filePath) {
  const absolutePath = path.resolve(process.cwd(), filePath);
  const content = fs.readFileSync(absolutePath, 'utf8');
  return JSON.parse(content);
}

function run(argv = process.argv.slice(2)) {
  const [filePath] = argv;

  if (!filePath) {
    throw new Error('Usage: node src/cli.js <path-to-database-struct.json>');
  }

  const data = loadDatabaseFile(filePath);
  return analyzeDatabaseStructure(data);
}

if (require.main === module) {
  try {
    const analysis = run();
    process.stdout.write(`${JSON.stringify(analysis, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  loadDatabaseFile,
  run,
};
