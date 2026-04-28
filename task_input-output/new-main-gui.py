import sys
from pathlib import Path
import json

# Ensure project root is on sys.path so imports like `process` resolve
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from flask import Flask, request, render_template_string

# local prototype modules (kept inside task_input-output)
from parser import parse_input
from simulator import simulate
from stats import build_stats_lines, build_stats_payload


INPUT_PATH = r"task_input-output\input.txt"
LOG_OUTPUT_PATH = r"task_input-output\simulation_log.txt"
STATS_OUTPUT_PATH = r"task_input-output\simulation_stats.txt"

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CPU Scheduler Simulator</title>
  <link rel="stylesheet" href="/static/style.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

<header class="header">
  <div class="header-left">
    <h1>Performance Dashboard</h1>
    <p>CPU scheduling simulation analysis and insights</p>
  </div>
  <form method="post" style="margin:0">
    <input type="hidden" name="input_text" id="export_input_hidden">
    <button class="btn-export" type="button" onclick="exportResults()">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
           viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Export Results
    </button>
  </form>
</header>

<div class="main">

  {% if message %}
    <div class="message {{ 'ok' if success else 'err' }}">{{ message }}</div>
  {% endif %}

  <form method="post" id="mainForm">
    <div class="input-panel">
      <div class="panel-bar">
        <span>Input Config</span>
        <span class="panel-dot"></span>
      </div>
      <textarea name="input_text" id="input_text" spellcheck="false">{{ input_text }}</textarea>
      <div class="panel-actions">
        <button class="btn-run"  type="submit" name="action" value="run">▶ Run Simulation</button>
        <button class="btn-save" type="submit" name="action" value="save">Save Input</button>
      </div>
    </div>

    {% if chart_data_json %}

    <!-- Stat cards -->
    <div class="stat-cards" id="statCards">

      <!-- CPU Utilization -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-title">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
                 viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            CPU Utilization
          </div>
          <span class="stat-trend trend-up">↗</span>
        </div>
        <div class="stat-value" id="valUtil">—</div>
        <div class="util-bar-track"><div class="util-bar-fill" id="utilBar" style="width:0%"></div></div>
        <span class="stat-badge" id="utilBadge">—</span>
      </div>

      <!-- Throughput -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-title">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
                 viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/></svg>
            Throughput
          </div>
          <span class="stat-trend trend-up">↗</span>
        </div>
        <div class="stat-value" id="valThroughput">—</div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px">processes / time unit</div>
      </div>

      <!-- Avg Turnaround -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-title">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
                 viewBox="0 0 24 24"><path d="M1 4v6h6"/><path d="M23 20v-6h-6"/>
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
            </svg>
            Avg Turnaround
          </div>
          <span class="stat-trend trend-flat">—</span>
        </div>
        <div class="stat-value" id="valTurnaround">—</div>
        <span class="stat-badge badge-yellow" id="turnBadge">—</span>
      </div>

      <!-- Avg CPU Time -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-title">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
                 viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            Avg CPU Time
          </div>
          <span class="stat-trend trend-flat">—</span>
        </div>
        <div class="stat-value" id="valCpuTime">—</div>
        <span class="stat-badge badge-yellow" id="cpuBadge">—</span>
      </div>

    </div>

    <!-- Charts -->
    <p class="section-label">Process breakdown</p>
    <div class="charts-row" id="chartsRow">

      <div class="chart-card">
        <h2>Process Performance Comparison</h2>
        <p>Turnaround and CPU time by process</p>
        <div class="chart-wrap"><canvas id="chartBar"></canvas></div>
      </div>

      <div class="chart-card">
        <h2>Average Metrics Distribution</h2>
        <p>Breakdown of average scheduling metrics</p>
        <div class="chart-wrap"><canvas id="chartPie"></canvas></div>
      </div>

    </div>
    {% endif %}
  </form>
</div>

{% if chart_data_json %}
<script>
  const cd = {{ chart_data_json | safe }};
  const pp = cd.per_process;
  const labels = pp.map(p => "P" + p.pid);

  Chart.defaults.color = '#888';
  Chart.defaults.font.family = "'IBM Plex Sans', sans-serif";
  Chart.defaults.font.size = 11;

  /* Stat card values  */
  const util = cd.utilization;
  const pct  = Math.round(util * 100);
  const avgTA  = pp.reduce((s, p) => s + p.turnaround, 0) / pp.length;
  const avgCPU = pp.reduce((s, p) => s + p.cpu_time,   0) / pp.length;
  const throughput = cd.throughput;

  document.getElementById('valUtil').textContent      = pct + '%';
  document.getElementById('utilBar').style.width      = pct + '%';
  document.getElementById('valThroughput').textContent = throughput.toFixed(2);
  document.getElementById('valTurnaround').textContent = avgTA.toFixed(2);
  document.getElementById('valCpuTime').textContent    = avgCPU.toFixed(2);

  /* Util badge */
  const utilBadge = document.getElementById('utilBadge');
  if (pct >= 80) { utilBadge.textContent = 'Excellent'; utilBadge.className = 'stat-badge badge-green'; }
  else if (pct >= 50) { utilBadge.textContent = 'Fair'; utilBadge.className = 'stat-badge badge-yellow'; }
  else { utilBadge.textContent = 'Low'; utilBadge.className = 'stat-badge badge-red'; }

  /* Turnaround badge */
  const tb = document.getElementById('turnBadge');
  tb.textContent = avgTA <= 10 ? 'Good' : avgTA <= 20 ? 'Fair' : 'High';
  tb.className   = 'stat-badge ' + (avgTA <= 10 ? 'badge-green' : avgTA <= 20 ? 'badge-yellow' : 'badge-red');

  /* CPU badge */
  const cb = document.getElementById('cpuBadge');
  cb.textContent = avgCPU <= 10 ? 'Good' : avgCPU <= 20 ? 'Fair' : 'High';
  cb.className   = 'stat-badge ' + (avgCPU <= 10 ? 'badge-green' : avgCPU <= 20 ? 'badge-yellow' : 'badge-red');

  /* Grouped bar chart */
  new Chart(document.getElementById('chartBar'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Turnaround',
          data: pp.map(p => p.turnaround),
          backgroundColor: '#facc15cc',
          borderColor: '#facc15',
          borderWidth: 1,
          borderRadius: 2,
        },
        {
          label: 'CPU Time',
          data: pp.map(p => p.cpu_time),
          backgroundColor: '#f87171cc',
          borderColor: '#f87171',
          borderWidth: 1,
          borderRadius: 2,
        },
        {
          label: 'Syscalls',
          data: pp.map(p => p.syscalls),
          backgroundColor: '#4ade80cc',
          borderColor: '#4ade80',
          borderWidth: 1,
          borderRadius: 2,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 700, easing: 'easeOutQuart' },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, boxWidth: 12, color: '#888' }
        },
        tooltip: {
          backgroundColor: '#1e1e1e',
          borderColor: '#2a2a2a',
          borderWidth: 1,
          titleColor: '#f0f0f0',
          bodyColor: '#888',
          padding: 10
        }
      },
      scales: {
        x: { grid: { color: '#2a2a2a' }, ticks: { color: '#888' } },
        y: { beginAtZero: true, grid: { color: '#2a2a2a', borderDash: [4,4] }, ticks: { color: '#888', precision: 0 } }
      }
    }
  });

  /* Pie chart */
  new Chart(document.getElementById('chartPie'), {
    type: 'pie',
    data: {
      labels: ['Turnaround', 'CPU Time', 'Syscalls'],
      datasets: [{
        data: [avgTA, avgCPU, pp.reduce((s,p) => s + p.syscalls, 0) / pp.length],
        backgroundColor: ['#facc1599', '#f8717199', '#4ade8099'],
        borderColor:     ['#facc15',   '#f87171',   '#4ade80'],
        borderWidth: 1,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800, easing: 'easeOutQuart' },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, boxWidth: 12, color: '#888' } },
        tooltip: {
          backgroundColor: '#1e1e1e',
          borderColor: '#2a2a2a',
          borderWidth: 1,
          titleColor: '#f0f0f0',
          bodyColor: '#888',
          padding: 10,
          callbacks: { label: ctx => ' ' + ctx.label + ': ' + ctx.parsed.toFixed(2) }
        }
      }
    }
  });

  /* Staggered reveal ── */
  requestAnimationFrame(() => {
    document.querySelectorAll('.stat-card, .chart-card').forEach(el => el.classList.add('visible'));
  });

  /* ── Export ── */
  function exportResults() {
    const rows = [['PID','Turnaround','CPU Time','Syscalls','Swaps']];
    pp.forEach(p => rows.push([p.pid, p.turnaround, p.cpu_time, p.syscalls, p.swaps]));
    rows.push([]);
    rows.push(['CPU Utilization', (cd.utilization * 100).toFixed(1) + '%']);
    const csv = rows.map(r => r.join(',')).join('\\n');
    const a = document.createElement('a');
    a.href = 'data:text/csv,' + encodeURIComponent(csv);
    a.download = 'simulation_results.csv';
    a.click();
  }
</script>
{% endif %}

</body>
</html>
"""


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


@app.route("/", methods=["GET", "POST"])
def index():
    input_text = ""
    chart_data_json = ""
    message = ""
    success = True

    try:
        input_text = read_file(INPUT_PATH)
    except Exception:
        input_text = ""

    if request.method == "POST":
        action = request.form.get("action", "")
        input_text = request.form.get("input_text", "")

        try:
            if action == "save":
                with open(INPUT_PATH, "w", encoding="utf-8") as f:
                    f.write(input_text.rstrip() + "\n")
                message = f"Saved input to {INPUT_PATH}"

            elif action == "run":
                params, processes = parse_input(input_text)
                processes, log, t = simulate(params, processes)
                stats_lines = build_stats_lines(processes, t, params["cpus"])
                stats_payload = build_stats_payload(processes, t, params["cpus"])

                # Add throughput to payload
                stats_payload["throughput"] = len(processes) / t if t > 0 else 0

                write_lines(LOG_OUTPUT_PATH, log)
                write_lines(STATS_OUTPUT_PATH, stats_lines)

                chart_data_json = json.dumps(stats_payload)
                message = f"Simulation complete. Saved {LOG_OUTPUT_PATH} and {STATS_OUTPUT_PATH}"

            else:
                message = "Unknown action"
                success = False
        except Exception as e:
            message = str(e)
            success = False

    return render_template_string(
        HTML_TEMPLATE,
        input_text=input_text,
        chart_data_json=chart_data_json,
        message=message,
        success=success,
    )


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()