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


@dataclass(frozen=True)
class Interval:
    pid: int
    core: int
    start: int
    end: int
    end_reason: str | None = None


def parse_log(path: str | Path) -> tuple[list[Interval], list[int], int]:
    intervals: list[Interval] = []
    running: dict[int, tuple[int, int]] = {}
    cores: set[int] = set()
    current_time = -1
    max_tick = -1

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

    final_time = max_tick + 1 if max_tick >= 0 else 0

    for pid, (core, start) in list(running.items()):
        end = max(final_time, start + 1)
        intervals.append(Interval(pid, core, start, end, "unknown"))
        cores.add(core)
        final_time = max(final_time, end)

    if final_time == 0 and intervals:
        final_time = max(i.end for i in intervals)

    intervals.sort(key=lambda i: (i.core, i.start, i.pid))
    return intervals, sorted(cores), final_time