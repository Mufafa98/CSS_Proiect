from process.process import Process
class Input:
    def __init__(self, input_path: str):
        assert isinstance(input_path, str) and input_path, "input_path must be a non-empty string"
        from pathlib import Path
        path = Path(input_path)
        assert path.exists() and path.is_file(), f"input file not found: {input_path}"
        with open(input_path, encoding="utf-8") as f:
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

            field = parts[0].upper()

            if field in {"PROCESSORS", "CPUS"}:
                assert len(parts) >= 2, "PROCESSORS line missing value"
                self.number_of_cores = int(parts[1])
                assert self.number_of_cores >= 1
            elif field == "MEMORY":
                assert len(parts) >= 2, "MEMORY line missing value"
                self.memory_size = int(parts[1])
                assert self.memory_size >= 0
            elif field == "TIMESLICE":
                assert len(parts) >= 2
                self.user_slice = int(parts[1])
                assert self.user_slice > 0
            elif field == "SYS_PERIOD":
                assert len(parts) >= 2
                self.sys_slice = int(parts[1])
                assert self.sys_slice > 0
            elif field == "DISK_RATE":
                assert len(parts) >= 2
                self.disk_speed = int(parts[1])
                assert self.disk_speed > 0
            elif field == "PROCESS":
                # Expect at least: PROCESS <id> <mem> <release> <exec...>
                assert len(parts) >= 5, "PROCESS line must have at least memory, release and one execution value"
                mem = int(parts[2])
                release = int(parts[3])
                execution_sequence = list(map(int, parts[4:]))

                # Execution sequence should be odd-length (run, sys, run, sys, ..., run)
                if len(execution_sequence) % 2 == 0:
                    raise ValueError("Invalid execution sequence format")

                assert mem >= 0 and release >= 0
                process = Process(pid, execution_sequence, False, release_time=release, memory_required=mem)
                self.processes.append(process)
                pid += 1

    def get_processes(self) -> list[Process]:
        return self.processes

    def get_user_slice(self) -> int:
        return self.user_slice

    def get_sys_slice(self) -> int:
        return self.sys_slice



