from parser import parse_input
from simulator import simulate
from stats import print_stats, build_stats_lines


LOG_OUTPUT_PATH = r"task_input-output\simulation_log.txt"
STATS_OUTPUT_PATH = r"task_input-output\simulation_stats.txt"

if __name__ == "__main__":

    with open(r"task_input-output\input.txt") as f:
        text = f.read()

    params, processes = parse_input(text)

    processes, log, t = simulate(params, processes)

    with open(LOG_OUTPUT_PATH, "w") as f:
        for line in log:
            f.write(line + "\n")

    stats_lines = build_stats_lines(processes, t, params["cpus"])
    with open(STATS_OUTPUT_PATH, "w") as f:
        for line in stats_lines:
            f.write(line + "\n")

    for line in log:
        print(line)

    print_stats(processes, t, params["cpus"])
    print(f"\nSaved log to {LOG_OUTPUT_PATH}")
    print(f"Saved stats to {STATS_OUTPUT_PATH}")