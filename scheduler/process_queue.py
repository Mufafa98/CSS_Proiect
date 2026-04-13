
from typing import Deque
from process import Process

class ProcessOnCore:
    process: Process
    time: int
    core: int

    def __init__(self, process: Process, time: int, core: int) -> None:
        self.process = process
        self.time = time
        self.core = core

    def __str__(self) -> str:
        return f"process_id: {self.process} time: {self.time}"

class ProcessQueue:
    def __init__(self, waiting: list[Process], system_process: Process, cores: list[int]):
        self.__waiting_sys = system_process
        self.__waiting = Deque(waiting)
        self.__runing = list[ProcessOnCore]()
        self.__done = list[Process]()

        self.__free_cores = list(cores)

    def __str__(self) -> str:
        waiting = [proc.id for proc in self.__waiting]
        running = [proc.process.id for proc in self.__runing]
        done = [proc.id for proc in self.__done]
        wait_sys = "" if self.__waiting_sys is None else f"{self.__waiting_sys.id}" 
        return f"ws [{wait_sys}] w {waiting} r {running} d {done}"

    def running(self) -> list[ProcessOnCore]:
        return self.__runing

    def pop_runable(self) -> Process | None:
        if self.__waiting_sys is not None and self.__waiting_sys.left_to_run != 0:
            process = self.__waiting_sys
            self.__waiting_sys = None
            return process
        
        counter = 0
        while counter != len(self.__waiting):
            process = self.__waiting.popleft()
            if process.left_to_run == 0:
                self.__waiting.append(process)
            else:
                return process
            counter += 1
        return None

    def schedule_conditions(self) -> bool:
        return len(self.__waiting) != 0 and len(self.__free_cores) != 0

    def run(self, process: Process):
        core = self.__free_cores.pop()
        self.__runing.append(ProcessOnCore(process, 0, core))

    def stop(self, process: ProcessOnCore):
        self.__runing.remove(process)
        self.__free_cores.append(process.core)
        
        if process.process.sys_proc:
            self.__waiting_sys = process.process
            return

        if process.process.is_done():
           self.__done.append(process.process)
        else:
            self.__waiting.append(process.process)

    def count_runing(self) -> int:
        return len(self.__runing)
