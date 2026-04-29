from __future__ import annotations

from pathlib import Path
from process import Process


def _read_text(source: str | Path) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")

    path = Path(source)
    if "\n" not in source and path.exists():
        return path.read_text(encoding="utf-8")
    return source


def parse_input(source: str | Path) -> tuple[dict[str, int], list[ProcessRecord]]:
    text = _read_text(source)

    params: dict[str, int] = {}
    processes: list[ProcessRecord] = []

    pid = 1
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        key = parts[0].upper()

        if key in {"PROCESSORS", "CPUS"} and len(parts) >= 2:
            params["cpus"] = int(parts[1])
        elif key == "MEMORY" and len(parts) >= 2:
            params["memory"] = int(parts[1])
        elif key == "TIMESLICE" and len(parts) >= 2:
            params["timeslice"] = int(parts[1])
        elif key == "SYS_PERIOD" and len(parts) >= 2:
            params["sys_slice"] = int(parts[1])
        elif key == "DISK_RATE" and len(parts) >= 2:
            params["disk_rate"] = int(parts[1])
        if key == "PROCESS" and len(parts) >= 4:
            release = int(parts[1])
            memory = int(parts[2])
            execution_sequence = [int(value) for value in parts[3:]]

            proc = Process(pid, execution_sequence, False, release, memory)

            # Compatibility aliases expected by the prototype simulator
            flat_exec_seq: list[int] = []
            for stage in getattr(proc, "_stages", []):
                flat_exec_seq.append(stage.run_ticks)
                if stage.sys_call_ticks is not None:
                    flat_exec_seq.append(stage.sys_call_ticks)

            proc.exec_seq = flat_exec_seq
            proc.pid = proc.id
            proc.release = proc.release_time
            proc.mem = proc.memory_required
            proc.state = "NEW"
            proc.swap_ins = 0
            proc.start_time = None
            proc.last_cpu = None
            proc.remaining = flat_exec_seq[0] if flat_exec_seq else 0
            proc.idx = 0
            proc.cpu_time = 0
            proc.syscalls = 0
            proc.finish_time = None

            processes.append(proc)
            pid += 1

    required = ("cpus", "memory", "timeslice", "sys_slice", "disk_rate")
    missing = [name for name in required if name not in params]
    if missing:
        raise ValueError(f"Missing input parameter(s): {', '.join(missing)}")

    processes.sort(key=lambda process: (process.release, process.pid))
    return params, processes
