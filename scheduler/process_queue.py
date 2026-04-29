from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional

from process import Process
from system.system import System


@dataclass
class ProcessOnCore:
    """
    Runtime slot that pairs a process with its current core and time on core.
    """
    process: Process
    time: int
    core: int

    def __str__(self) -> str:
        return f"{self.process} time: {self.time}"


class ProcessQueue:
    """
    Queue manager for scheduling.

    It tracks:
    - waiting user processes
    - waiting system process (pid 0)
    - running processes on cores
    - completed processes
    - free core IDs
    """

    def __init__(self, waiting: list[Process], system_process: Process, cores: list[int]) -> None:
        self.__waiting_sys: Optional[Process] = system_process
        self.__waiting: Deque[Process] = deque(waiting)
        self.__running: List[ProcessOnCore] = []
        self.__done: List[Process] = []

        self.__free_cores: Deque[int] = deque(cores)

    def __str__(self) -> str:
        waiting = [proc.id for proc in self.__waiting]
        running = [proc.process.id for proc in self.__running]
        done = [proc.id for proc in self.__done]
        wait_sys = "" if self.__waiting_sys is None else f"{self.__waiting_sys.id}"
        return f"ws [{wait_sys}] w {waiting} r {running} d {done}"

    def running(self) -> list[ProcessOnCore]:
        """
        Return the list of currently running processes (process + core + time).
        """
        return self.__running

    def pop_runnable(self, system: System, current_tick: int) -> Optional[Process]:
        """
        Pop the next runnable process.

        - System process (pid 0) has priority if it has work.
        - User processes are rotated until a runnable one is found.
        - A user process is runnable only if current_tick >= release_time.

        Returns
        -------
        Process | None
            Runnable process or None if none can be scheduled.
        """
        if self.__waiting_sys is not None and self.__waiting_sys.left_to_run != 0:
            process = self.__waiting_sys
            self.__waiting_sys = None
            return process

        counter = 0
        while counter != len(self.__waiting):
            process = self.__waiting.popleft()

            # Release-time gate
            if current_tick < process.get_release_time():
                self.__waiting.append(process)
            elif process.left_to_run == 0 or not system.load_in_memory(process):
                self.__waiting.append(process)
            else:
                return process

            counter += 1

        return None

    def schedule_conditions(self) -> bool:
        """
        Check if scheduling can occur (waiting process and free cores).
        """
        return len(self.__waiting) != 0 and len(self.__free_cores) != 0

    def run(self, process: Process) -> int:
        """
        Assign a process to a free core (honoring core affinity when possible).

        Returns
        -------
        int
            Core ID where the process was scheduled.
        """
        most_recent = process.get_last_cpu()

        if most_recent is not None and most_recent in self.__free_cores:
            core = most_recent
            self.__free_cores.remove(most_recent)
        else:
            core = self.__free_cores.pop()

        process.record_cpu(core)
        self.__running.append(ProcessOnCore(process, 0, core))
        return core

    def stop(self, process: ProcessOnCore) -> None:
        """
        Stop a running process and return its core to the free pool.
        """
        self.__running.remove(process)
        self.__free_cores.appendleft(process.core)

        if process.process.sys_proc:
            self.__waiting_sys = process.process
            return

        if process.process.is_done():
            self.__done.append(process.process)
        else:
            self.__waiting.append(process.process)

    def count_running(self) -> int:
        """
        Return the number of running processes (preferred name).
        """
        return len(self.__running)

    def count_waiting(self) -> int:
        """
        Return the number of waiting user processes.
        """
        return len(self.__waiting)
