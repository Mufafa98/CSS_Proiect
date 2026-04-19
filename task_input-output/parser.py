from models import Process

def parse_input(text):
    lines = text.split("\n")

    params = {}
    processes = []
    pid = 1

    for line in lines:
        line = line.split("#")[0].strip()
        if not line:
            continue

        parts = line.split()

        if parts[0] == "PROCESSORS":
            params["cpus"] = int(parts[1])
        elif parts[0] == "MEMORY":
            params["memory"] = int(parts[1])
        elif parts[0] == "TIMESLICE":
            params["timeslice"] = int(parts[1])
        elif parts[0] == "SYS_PERIOD":
            params["sys_period"] = int(parts[1])
        elif parts[0] == "DISK_RATE":
            params["disk_rate"] = int(parts[1])

        elif parts[0] == "PROCESS":
            release = int(parts[1])
            mem = int(parts[2])
            bursts = list(map(int, parts[3:]))

            if len(bursts) % 2 == 0:
                raise ValueError("Invalid burst format")

            processes.append(Process(pid, release, mem, bursts))
            pid += 1

    return params, processes