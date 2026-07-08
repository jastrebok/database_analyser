const summary = document.getElementById('summary');
const schemaTabs = document.getElementById('schema-tabs');
const tableTabs = document.getElementById('table-tabs');
const tableView = document.getElementById('table-view');

let activeSchemaIndex = 0;
const activeTableBySchema = new Map();
let currentChart = null;
let currentReport = null;

async function loadReport() {
  const response = await fetch('/api/report');
  if (response.status === 202) {
    return null;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Failed to load report: ${response.status}`);
  }
  const payload = await response.json();
  return payload.report || payload;
}

function getSchemas(report) {
  if (Array.isArray(report.schemas) && report.schemas.length) {
    return report.schemas.map((schema) => ({
      name: schema.name || 'default',
      tables: Array.isArray(schema.tables) ? schema.tables : [],
    }));
  }

  const grouped = new Map();
  for (const table of Array.isArray(report.tables) ? report.tables : []) {
    const schemaName = table.schema_name || 'default';
    if (!grouped.has(schemaName)) {
      grouped.set(schemaName, []);
    }
    grouped.get(schemaName).push(table);
  }

  return Array.from(grouped.entries()).map(([name, tables]) => ({ name, tables }));
}

function formatCount(count) {
  return new Intl.NumberFormat().format(count);
}

function renderSummary(report) {
  const schemas = getSchemas(report);
  const tables = schemas.flatMap((schema) => schema.tables);
  const objects = Array.isArray(report.objects) ? report.objects : [];
  const tableCount = tables.length;
  const distinctValueCount = tables.reduce((total, table) => total + (Array.isArray(table.distinct_values) ? table.distinct_values.length : 0), 0);
  const objectCount = objects.filter((item) => item.object_type === 'table').length;
  summary.innerHTML = `
    <div class="summary-card">
      <span class="summary-label">Source</span>
      <strong>${report.path.split('/').pop()}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Schema objects</span>
      <strong>${objectCount}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Tables with rows</span>
      <strong>${tableCount}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Distinct values tracked</span>
      <strong>${formatCount(distinctValueCount)}</strong>
    </div>
  `;
}

function getActiveSchema(schemas) {
  return schemas[activeSchemaIndex] || schemas[0] || { name: 'default', tables: [] };
}

function getActiveTable(schema) {
  const index = activeTableBySchema.get(schema.name) ?? 0;
  return schema.tables[index] || schema.tables[0] || null;
}

function renderSchemaTabs(schemas) {
  schemaTabs.innerHTML = '';
  schemas.forEach((schema, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `tab-button ${index === activeSchemaIndex ? 'active' : ''}`;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', String(index === activeSchemaIndex));
    button.setAttribute('aria-controls', 'table-tabs');
    button.textContent = schema.name;
    button.addEventListener('click', () => {
      activeSchemaIndex = index;
      renderReport();
    });
    schemaTabs.appendChild(button);
  });
}

function renderTableTabs(schema) {
  tableTabs.innerHTML = '';
  schema.tables.forEach((table, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `tab-button ${index === (activeTableBySchema.get(schema.name) ?? 0) ? 'active' : ''}`;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', String(index === (activeTableBySchema.get(schema.name) ?? 0)));
    button.setAttribute('aria-controls', 'table-view');
    button.textContent = table.name;
    button.addEventListener('click', () => {
      activeTableBySchema.set(schema.name, index);
      renderReport();
    });
    tableTabs.appendChild(button);
  });
}

function renderTableView(table) {
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }

  if (!table) {
    tableView.innerHTML = '<div class="empty-state">No tables found in this schema.</div>';
    return;
  }

  const distinctValues = Array.isArray(table.distinct_values) ? table.distinct_values : [];
  const chartValues = (Array.isArray(table.top_values) && table.top_values.length ? table.top_values : distinctValues).slice(0, 8);
  const distinctChips = distinctValues.length
    ? distinctValues.map((entry) => `<span class="value-chip">${entry.value} · ${formatCount(entry.count)}</span>`).join('')
    : '<span class="value-chip value-chip-empty">No distinct values collected</span>';

  tableView.innerHTML = `
    <article class="table-card table-card-wide">
      <header class="table-card-head">
        <div>
          <p class="table-name">${table.name}</p>
          <p class="table-meta">schema: ${table.schema_name || 'default'} · ${formatCount(table.row_count)} rows · focus column: ${table.focus_column || 'n/a'}</p>
        </div>
        <div class="table-badge">${formatCount(distinctValues.length)} distinct values</div>
      </header>
      <div class="table-layout table-layout-wide">
        <div class="table-summary">
          <div class="section-subhead">Distinct values</div>
          <div class="value-grid">${distinctChips}</div>
        </div>
        <div class="chart-wrap chart-wrap-large">
          <canvas id="chart-canvas" aria-label="Radar chart for ${table.name}"></canvas>
        </div>
      </div>
    </article>
  `;

  const labels = chartValues.map((entry) => entry.value);
  const values = chartValues.map((entry) => entry.count);
  if (labels.length && window.Chart) {
    const canvas = document.getElementById('chart-canvas');
    currentChart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels,
        datasets: [{
          label: table.name,
          data: values,
          borderColor: '#ffb347',
          backgroundColor: 'rgba(255, 179, 71, 0.22)',
          pointBackgroundColor: '#ffe3bf',
          pointBorderColor: '#ffb347',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            grid: { color: 'rgba(255,255,255,0.12)' },
            angleLines: { color: 'rgba(255,255,255,0.12)' },
            pointLabels: { color: '#f5f7fb', font: { size: 12 } },
            ticks: { backdropColor: 'transparent', color: '#9aa6bd' },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }
}

function renderReport() {
  const schemas = getSchemas(currentReport);
  if (!schemas.length) {
    schemaTabs.innerHTML = '';
    tableTabs.innerHTML = '';
    tableView.innerHTML = '<div class="empty-state">No schemas found in this report.</div>';
    return;
  }

  activeSchemaIndex = Math.min(activeSchemaIndex, schemas.length - 1);
  const activeSchema = getActiveSchema(schemas);
  if (!activeSchema.tables.length) {
    activeTableBySchema.set(activeSchema.name, 0);
  } else if (!activeTableBySchema.has(activeSchema.name)) {
    activeTableBySchema.set(activeSchema.name, 0);
  } else {
    activeTableBySchema.set(activeSchema.name, Math.min(activeTableBySchema.get(activeSchema.name), activeSchema.tables.length - 1));
  }

  renderSchemaTabs(schemas);
  renderTableTabs(activeSchema);
  renderTableView(getActiveTable(activeSchema));
}

async function boot() {
  try {
    summary.innerHTML = '<div class="summary-card">Loading report...</div>';
    let report = null;
    while (!report) {
      report = await loadReport();
      if (!report) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
    currentReport = report;
    renderSummary(report);
    renderReport();
  } catch (error) {
    summary.innerHTML = `<div class="summary-card error">${error.message}</div>`;
  }
}

boot();