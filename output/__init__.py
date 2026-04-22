
import os

LOG_OUTPUT_PATH = os.path.join("logs", "log.txt")

class Output:
    def __init__(self) -> None:
        self.log_file = open(LOG_OUTPUT_PATH, 'w')

    def write(self, string: str):
        self.log_file.write(f"{string}\n")
        self.log_file.flush()

    def tick(self, time: int):
        self.write(f"[   Tick   ] time {time}")

    def scheduled(self, process_id: int, core_id: int):
        self.write(f"[ Schedule ] process {process_id} core {core_id}")

    def unscheduled(self, process_id: int, reason: str):
        self.write(f"[Unschedule] process {process_id} reason {reason}")

    def start_load_in_memory(self, process_id: int):
        pass

    def end_load_in_memory(self, process_id: int):
        pass

    def unload_from_memory(self, process_id: int):
        pass

    def close(self):
        self.log_file.close()
