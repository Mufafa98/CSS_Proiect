def build_stats_lines(processes, total_time, cpus):
    lines = ["STATS"]
    total_cpu = 0

    for p in processes:
        turnaround = p.finish_time - p.release
        total_cpu += p.cpu_time

        lines.append(
            f"P{p.pid} turnaround={turnaround} cpu={p.cpu_time} syscalls={p.syscalls} swaps={p.swap_ins}"
        )

    util = total_cpu / (total_time * cpus)
    lines.append(f"CPU utilization={util:.2f}")
    return lines


def print_stats(processes, total_time, cpus):
    print()
    for line in build_stats_lines(processes, total_time, cpus):
        print(line)