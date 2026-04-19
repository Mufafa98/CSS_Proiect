class Process:
    def __init__(self, pid, release, mem, bursts):
        self.pid = pid
        self.release = release
        self.mem = mem
        self.bursts = bursts

        self.idx = 0
        self.remaining = bursts[0] if bursts else 0

        self.state = "NEW"
        self.last_cpu = None

        self.start_time = None
        self.finish_time = None

        self.cpu_time = 0
        self.syscalls = 0
        self.swap_ins = 0

        self.in_memory = False


class CPU:
    def __init__(self, cid):
        self.cid = cid
        self.proc = None
        self.slice_left = 0