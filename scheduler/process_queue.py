from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional

from process.process import Process
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

        assert system_process is not None, "System process should not be None"
        assert waiting is not None and len(waiting) > 0, "There should be processes waiting to be scheduled"
        assert cores is not None and len(cores) > 0, "There should be cores to schedule processes on"

        
        assert len(set(cores)) == len(cores), "core IDs must be unique"
        for core in cores:
            assert core >= 0, "core IDs must be non-negative"

        for process in waiting:
            assert process is not None, "process must not be None"
            assert process.left_to_run >= 0, "process.left_to_run must be non-negative"
            assert process.get_release_time() >= 0, "release_time must be non-negative"
            assert process.left_to_run != 0, "Processes should have something to run"

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
        
        for slot in self.__running:
            assert slot.process is not None, "slot.process must exist"
            assert slot.time >= 0, "slot.time must be non-negative"
            assert slot.core >= 0, "slot.core must be non-negative"
            assert slot.process.left_to_run >= 0, "left_to_run must be non-negative"
            assert slot.core not in self.__free_cores, "running core must not be free"
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

        
        assert current_tick >= 0, "current_tick must be non-negative"
        assert system is not None, "system must exist"

        if self.__waiting_sys is not None and self.__waiting_sys.left_to_run != 0:
            process = self.__waiting_sys
            self.__waiting_sys = None
            
            assert process is not None, "process must be returned"
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
                
                assert process.left_to_run > 0, "runnable process must have work"
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

        
        assert process is not None, "process must exist"
        assert len(self.__free_cores) > 0, "must have at least one free core"
        assert process not in self.__done, "process must not be done"
        assert all(slot.process != process for slot in self.__running), "process must not be running"
        assert process.left_to_run > 0, "process should have something to run if passed to run()"

        most_recent = process.get_last_cpu()
        assert most_recent is None or most_recent >= 0, "last_cpu must be non-negative when set"

        if most_recent is not None and most_recent in self.__free_cores:
            core = most_recent
            self.__free_cores.remove(most_recent)
        else:
            core = self.__free_cores.pop()

        process.record_cpu(core)
        self.__running.append(ProcessOnCore(process, 0, core))

        
        assert core is not None and core >= 0, "core must be assigned and non-negative"
        assert core not in self.__free_cores, "assigned core must not be free"
        return core

    def stop(self, process: ProcessOnCore) -> None:
        """
        Stop a running process and return its core to the free pool.
        """
        
        assert process in self.__running, "process must be running to stop"
        assert process.process is not None, "process must exist"
        assert process.time >= 0, "process time must be non-negative"
        assert process.process.left_to_run >= 0, "left_to_run must be non-negative"
        assert process.core not in self.__free_cores, "core should not be both ocupied and free"

        self.__running.remove(process)
        self.__free_cores.appendleft(process.core)

        if process.process.sys_proc:
            self.__waiting_sys = process.process
            
            assert self.__waiting_sys is not None, "system process must be queued"
            return

        if process.process.is_done():
            self.__done.append(process.process)
            assert process.process.left_to_run == 0, "left to run should be 0 is done"
        else:
            self.__waiting.append(process.process)

        
        assert process.process not in self.__running, "process must be removed from running"
        assert process.core in self.__free_cores, "core must be marked as free"

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
    

    def count_done(self) -> int:
        """
        Return the number of done user processes.
        """
        return len(self.__done)