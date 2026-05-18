
import os

LOG_OUTPUT_PATH = os.path.join("logs", "log.txt")

class Output:
    def __init__(self) -> None:
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_OUTPUT_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        self.log_file = open(LOG_OUTPUT_PATH, 'w', encoding='utf-8')

    def tick(self, time: int):
        assert isinstance(time, int) and time >= 0, "tick time must be non-negative int"
        self.write(f"[   Tick   ] time {time}")

    def scheduled(self, process_id: int, core_id: int):
        assert isinstance(process_id, int) and process_id >= 0
        assert isinstance(core_id, int) and core_id >= 0
        self.write(f"[ Schedule ] process {process_id} core {core_id}")

    def unscheduled(self, process_id: int, reason: str):
        assert isinstance(process_id, int) and process_id >= 0
        assert isinstance(reason, str)
        self.write(f"[Unschedule] process {process_id} reason {reason}")

    def load_in_memory(self, process_id: int):
        assert isinstance(process_id, int) and process_id >= 0
        self.write(f"[ LoadMem  ] process {process_id}")

    def unload_from_memory(self, process_id: int):
        assert isinstance(process_id, int) and process_id >= 0
        self.write(f"[UnloadMem ] process {process_id}")

    def close(self):
        self.log_file.close()
