from collections import deque
from utils import log_event
from memory import MemoryManager
from process import Process

def simulate(params, processes):

    time = 0
    class CPU:
        def __init__(self, cid: int) -> None:
            self.cid = cid
            self.proc = None
            self.slice_left = 0

    cpus = [CPU(i + 1) for i in range(params["cpus"])]

    ready = deque()
    blocked = []
    disk = []

    memory = MemoryManager(params["memory"])

    log = []

    processes = sorted(processes, key=lambda p: p.release)

    def load_process(p):
        if p.in_memory:
            memory.access(p)
            return True

        # A process larger than total RAM can never run.
        if p.mem > memory.limit:
            raise ValueError(
                f"Process P{p.pid} requires {p.mem} memory, exceeds RAM limit {memory.limit}."
            )

        # Evict least-recently-used processes until this one fits.
        while not memory.can_fit(p):
            victim = memory.evict_lru()
            if victim is None:
                return False
            log_event(log, time, f"P{victim.pid} evicted")

        loaded = memory.load(p)
        if loaded:
            p.swap_ins += 1
        return loaded

    while True:

        # release
        for p in processes:
            if p.state == "NEW" and p.release <= time:
                p.state = "READY"
                ready.append(p)
                log_event(log, time, f"P{p.pid} released")

        # syscall unblock
        for item in blocked[:]:
            p, t_ready = item
            if time >= t_ready:
                blocked.remove(item)
                p.state = "READY"
                ready.append(p)
                log_event(log, time, f"P{p.pid} syscall done")

        # scheduling
        for cpu in cpus:
            if cpu.proc is None and ready:
                p = ready.popleft()

                if not load_process(p):
                    ready.append(p)
                    continue

                cpu.proc = p
                cpu.slice_left = params["timeslice"]
                p.state = "RUNNING"
                p.last_cpu = cpu.cid

                if p.start_time is None:
                    p.start_time = time

                log_event(log, time, f"P{p.pid} scheduled CPU{cpu.cid}")

        # execution
        for cpu in cpus:
            p = cpu.proc
            if not p:
                continue

            p.remaining -= 1
            cpu.slice_left -= 1
            p.cpu_time += 1

            # burst end
            if p.remaining == 0:
                p.idx += 1

                if p.idx >= len(p.bursts):
                    p.state = "DONE"
                    p.finish_time = time
                    cpu.proc = None
                    log_event(log, time, f"P{p.pid} finished")
                    continue

                syscall = p.bursts[p.idx]
                p.idx += 1

                p.remaining = p.bursts[p.idx] if p.idx < len(p.bursts) else 0
                p.syscalls += 1

                p.state = "BLOCKED"
                blocked.append((p, time + syscall))

                cpu.proc = None
                log_event(log, time, f"P{p.pid} syscall")
                continue

            # timeslice
            if cpu.slice_left == 0:
                p.state = "READY"
                ready.append(p)
                cpu.proc = None
                log_event(log, time, f"P{p.pid} preempted")

        # stop
        if all(p.state == "DONE" for p in processes):
            break

        time += 1

    return processes, log, time