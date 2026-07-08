const DatabaseAnalyser = require('./core/databaseAnalyser');
const formatSummary = require('./reporters/summaryReporter');

function createAnalyser() {
  return new DatabaseAnalyser();
}

if (require.main === module) {
  const analyser = createAnalyser();
  const summary = analyser.analyse({
    tables: [{ name: 'users' }, { name: 'orders' }],
    relationships: [{ from: 'orders', to: 'users' }]
  });

  console.log(formatSummary(summary));
}

module.exports = {
  createAnalyser,
  DatabaseAnalyser,
  formatSummary
};
