from flask import Flask, request, render_template_string

from parser import parse_input
from simulator import simulate
from stats import build_stats_lines


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
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f7fb; color: #1f2937; }
    h1 { margin: 0 0 16px 0; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .card { background: #ffffff; border: 1px solid #d1d5db; border-radius: 8px; padding: 14px; }
    label { display: block; margin-bottom: 6px; font-weight: 600; }
    textarea { width: 100%; min-height: 240px; resize: vertical; font-family: Consolas, monospace; font-size: 13px; }
    .out { min-height: 280px; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 10px; white-space: pre-wrap; overflow: auto; }
    .buttons { display: flex; gap: 10px; margin-top: 10px; }
    button { padding: 8px 14px; border: 0; border-radius: 6px; background: #2563eb; color: #fff; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .message { margin: 10px 0 16px; font-weight: 600; }
    .ok { color: #065f46; }
    .err { color: #991b1b; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>CPU Scheduler Simulator</h1>

  {% if message %}
    <div class="message {{ 'ok' if success else 'err' }}">{{ message }}</div>
  {% endif %}

  <form method="post">
    <div class="card">
      <label for="input_text">Input</label>
      <textarea id="input_text" name="input_text">{{ input_text }}</textarea>
      <div class="buttons">
        <button type="submit" name="action" value="save">Save input</button>
        <button type="submit" name="action" value="run">Run simulation</button>
      </div>
    </div>

    <div class="grid" style="margin-top: 16px;">
      <div class="card">
        <label>Simulation log</label>
        <div class="out">{{ log_output }}</div>
      </div>
      <div class="card">
        <label>Statistics</label>
        <div class="out">{{ stats_output }}</div>
      </div>
    </div>
  </form>
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
    log_output = ""
    stats_output = ""
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

                write_lines(LOG_OUTPUT_PATH, log)
                write_lines(STATS_OUTPUT_PATH, stats_lines)

                log_output = "\n".join(log)
                stats_output = "\n".join(stats_lines)
                message = (
                    f"Simulation complete. Saved {LOG_OUTPUT_PATH} and {STATS_OUTPUT_PATH}"
                )

            else:
                message = "Unknown action"
                success = False
        except Exception as e:
            message = str(e)
            success = False

    return render_template_string(
        HTML_TEMPLATE,
        input_text=input_text,
        log_output=log_output,
        stats_output=stats_output,
        message=message,
        success=success,
    )


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
