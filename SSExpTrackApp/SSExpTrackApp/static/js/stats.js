let myChart = null;
let cached = { labels: [], data: [] };

const COLORS = [
  'rgba(255, 99, 132, 0.6)',
  'rgba(54, 162, 235, 0.6)',
  'rgba(255, 206, 86, 0.6)',
  'rgba(75, 192, 192, 0.6)',
  'rgba(153, 102, 255, 0.6)',
  'rgba(255, 159, 64, 0.6)'
];

function makeDataset(data, type) {
  const base = { label: 'Expenses per Category', data, borderWidth: 2 };
  if (type === 'line' || type === 'radar') return { ...base, fill: false, tension: 0.25 };
  return { ...base, backgroundColor: COLORS, borderColor: 'white' };
}

function renderChart(type) {
  const canvas = document.getElementById('myChart');

  // Destroy any existing chart on this canvas (covers charts created anywhere)
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  myChart = new Chart(canvas, {
    type,
    data: {
      labels: cached.labels,
      datasets: [makeDataset(cached.data, type)]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: 'Expenses per Category', font: { size: 18 } },
        legend: { position: 'top' }
      }
    }
  });
}

function loadDataAndRender() {
  fetch("expense-category-summary")
    .then(res => res.json())
    .then(results => {
      const category_data = results.expense_category_data || {};
      cached.labels = Object.keys(category_data);
      cached.data = Object.values(category_data);

      const selectedType = document.getElementById('chartType').value || 'doughnut';
      renderChart(selectedType);
    });
}

document.addEventListener('DOMContentLoaded', () => {
  loadDataAndRender();

  document.getElementById('chartType').addEventListener('change', (e) => {
    renderChart(e.target.value); // no refetch; reuse cached data
  });
});
