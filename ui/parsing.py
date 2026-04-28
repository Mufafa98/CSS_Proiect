from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SCHEDULE_RE = re.compile(r'^\[\s*Schedule\s*\]\s*process\s+(\d+)\s+core\s+(\d+)', re.IGNORECASE)
UNSCHEDULE_RE = re.compile(
    r'^\[\s*Unschedule\s*\]\s*process\s+(\d+)(?:\s+reason\s+(\w+))?',
    re.IGNORECASE,
)
TICK_RE = re.compile(r'^\[\s*Tick\s*\]\s*time\s+(\d+)', re.IGNORECASE)
LOADMEM_RE = re.compile(r'^\[\s*LoadMem\s*\]\s*process\s+(\d+)', re.IGNORECASE)
UNLOADMEM_RE = re.compile(r'^\[\s*UnloadMem\s*\]\s*process\s+(\d+)', re.IGNORECASE)


@dataclass(frozen=True)
class Interval:
    pid: int
    core: int
    start: int
    end: int
    end_reason: str | None = None


@dataclass(frozen=True)
class InputConfig:
    memory_total: int
    disk_rate: int
    process_mem: dict[int, int]
    process_seq: dict[int, list[int]]


def parse_log(path: str | Path) -> tuple[list[Interval], list[int], int, list[list[int]], list[list[int]]]:
    intervals: list[Interval] = []
    running: dict[int, tuple[int, int]] = {}
    cores: set[int] = set()
    current_time = -1
    max_tick = -1
    max_load_tick = -1
    max_unload_tick = -1
    loadmem_by_tick: dict[int, list[int]] = {}
    unloadmem_by_tick: dict[int, list[int]] = {}

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            m = TICK_RE.match(line)
            if m:
                current_time = int(m.group(1))
                max_tick = max(max_tick, current_time)
                continue

            m = LOADMEM_RE.match(line)
            if m:
                pid = int(m.group(1))
                tick = current_time + 1
                loadmem_by_tick.setdefault(tick, []).append(pid)
                max_load_tick = max(max_load_tick, tick)
                continue

            m = UNLOADMEM_RE.match(line)
            if m:
                pid = int(m.group(1))
                tick = current_time + 1
                unloadmem_by_tick.setdefault(tick, []).append(pid)
                max_unload_tick = max(max_unload_tick, tick)
                continue

            m = SCHEDULE_RE.match(line)
            if m:
                pid = int(m.group(1))
                core = int(m.group(2))
                start = current_time + 1

                if pid in running:
                    old_core, old_start = running.pop(pid)
                    end = current_time + 1
                    intervals.append(Interval(pid, old_core, old_start, end, "preempted"))
                    cores.add(old_core)

                running[pid] = (core, start)
                cores.add(core)
                continue

            m = UNSCHEDULE_RE.match(line)
            if m:
                pid = int(m.group(1))
                reason = (m.group(2) or "unknown").lower()
                if pid in running:
                    core, start = running.pop(pid)
                    end = current_time + 1
                    intervals.append(Interval(pid, core, start, end, reason))
                    cores.add(core)
                continue

    max_time = max(max_tick, max_load_tick, max_unload_tick)
    final_time = max_time + 1 if max_time >= 0 else 0

    for pid, (core, start) in list(running.items()):
        end = max(final_time, start + 1)
        intervals.append(Interval(pid, core, start, end, "unknown"))
        cores.add(core)
        final_time = max(final_time, end)

    if final_time == 0 and intervals:
        final_time = max(i.end for i in intervals)

    loadmem_list: list[list[int]] = [[] for _ in range(final_time)]
    for tick, pids in loadmem_by_tick.items():
        if 0 <= tick < final_time:
            loadmem_list[tick] = pids

    unloadmem_list: list[list[int]] = [[] for _ in range(final_time)]
    for tick, pids in unloadmem_by_tick.items():
        if 0 <= tick < final_time:
            unloadmem_list[tick] = pids

    intervals.sort(key=lambda i: (i.core, i.start, i.pid))
    return intervals, sorted(cores), final_time, loadmem_list, unloadmem_list


def parse_input(path: str | Path) -> InputConfig:
    path = Path(path)
    memory_total: int | None = None
    disk_rate: int | None = None
    process_mem: dict[int, int] = {}
    process_seq: dict[int, list[int]] = {}

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            key = parts[0].upper()
            if key == "MEMORY" and len(parts) >= 2:
                memory_total = int(parts[1])
            elif key == "DISK_RATE" and len(parts) >= 2:
                disk_rate = int(parts[1])
            elif key == "PROCESS" and len(parts) >= 3:
                pid = int(parts[1])
                mem = int(parts[2])
                process_mem[pid] = mem
                seq = [int(x) for x in parts[3:]] if len(parts) > 3 else []
                process_seq[pid] = seq

    if memory_total is None or disk_rate is None:
        raise ValueError("Missing MEMORY or DISK_RATE in input file")

    return InputConfig(
        memory_total=memory_total,
        disk_rate=disk_rate,
        process_mem=process_mem,
        process_seq=process_seq,
    )


def build_memory_timeline(
    loadmem_by_tick: list[list[int]],
    unloadmem_by_tick: list[list[int]],
    final_time: int,
    memory_total: int,
    disk_rate: int,
    process_mem: dict[int, int] | None = None,
) -> list[list[tuple[int, int]]]:
    process_mem = process_mem or {}
    loaded: dict[int, int] = {}
    load_order: list[int] = []

    memory_by_tick: list[list[tuple[int, int]]] = []
    free = max(memory_total, 0)

    for t in range(final_time):
        # Apply unloads first to free memory for this tick.
        if t < len(unloadmem_by_tick):
            for pid in unloadmem_by_tick[t]:
                if pid in loaded:
                    freed = loaded.pop(pid)
                    free = min(memory_total, free + freed)
                    if pid in load_order:
                        load_order.remove(pid)

        if t < len(loadmem_by_tick):
            for pid in loadmem_by_tick[t]:
                if pid not in loaded:
                    loaded[pid] = 0
                    load_order.append(pid)

                if disk_rate <= 0 or free <= 0:
                    continue

                if pid in process_mem:
                    remaining = max(process_mem[pid] - loaded[pid], 0)
                    if remaining <= 0:
                        continue
                    delta = min(disk_rate, free, remaining)
                else:
                    delta = min(disk_rate, free)

                if delta <= 0:
                    continue

                loaded[pid] += delta
                free -= delta

        segments = [(pid, loaded[pid]) for pid in load_order if loaded.get(pid, 0) > 0]
        memory_by_tick.append(segments)

    return memory_by_tick