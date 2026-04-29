from process import Process

class Input:
    def __init__(self, input_path: str):
        with open(input_path) as f:
            text = f.read()
    
        lines = text.split("\n")

        pid = 1
        self.processes = list[Process]()
        # Last Returned Process

        for line in lines:
            line = line.split("#")[0].strip()
            if not line:
                continue

            parts = line.split()

            field = parts[0]

            if field == "PROCESSORS":
                self.number_of_cores = int(parts[1])
            elif field == "MEMORY":
                self.memory_size = int(parts[1]) 
            elif field == "TIMESLICE":
                self.user_slice = int(parts[1])
            elif field == "SYS_PERIOD":
                self.sys_slice = int(parts[1])
            elif field == "DISK_RATE":
                self.disk_speed = int(parts[1])
            elif parts[0] == "PROCESS":
                mem = int(parts[2])
                release = int(parts[3])
                execution_sequence = list(map(int, parts[4:]))

                if len(execution_sequence) % 2 == 0:
                    raise ValueError("Invalid execution sequence format")
                process = Process(pid, execution_sequence, False, release_time=release, memory_required=mem)
                self.processes.append(process)
                pid += 1

    def get_processes(self) -> list[Process]:
        return self.processes

    def get_user_slice(self) -> int:
        return self.user_slice

    def get_sys_slice(self) -> int:
        return self.sys_slice



