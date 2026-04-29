"""
Scheduler runtime loop.

Responsibilities:
- Dispatch runnable processes to available cores.
- Enforce time slices and stop reasons.
- Coordinate system ticks and output logging.
"""

from __future__ import annotations

import time
from typing import List, Tuple

from input import Input
from output import Output
from system.system import System
from .process_queue import ProcessQueue


class Scheduler:
    """
    Round-robin style scheduler that cooperates with the System layer.

    It:
    - Tracks user and system time slices.
    - Fills CPU cores with runnable processes.
    - Advances execution, stops processes when needed,
      and triggers syscalls through the System.
    """

    def __init__(self, input: Input, system: System, output: Output) -> None:
        """
        Initialize scheduler configuration and queues.

        Parameters
        ----------
        input : Input
            Parsed input parameters (slices, processes, cores).
        system : System
            Runtime system state (memory, syscalls, disk transfer).
        output : Output
            Output logger for schedule/unschedule/tick events.
        """
        self.user_slice = input.get_user_slice()
        self.sys_slice = input.get_sys_slice()

        self.process_queue = ProcessQueue(
            system.get_processes(),
            system.get_system_process(),
            system.cores(),
        )
        self.system = system
        self.output = output
        self.current_tick = 0

    def step(self) -> None:
        """
        Execute one scheduling step.

        - Tick each running process.
        - Stop processes that exceed time slice, finish, or enter syscall wait.
        - Enqueue syscalls when needed.
        - Try to fill any freed cores.
        """
        if self.process_queue.count_runing() == 0 and self.process_queue.count_waiting() == 0:
            raise RuntimeError("Finished")

        to_stop: List[Tuple] = []

        for slot in self.process_queue.running():
            proc = slot.process
            proc.tick()
            slot.time += 1

            time_slice = self.sys_slice if proc.sys_proc else self.user_slice

            reached_time = slot.time >= time_slice
            stopped_exec = proc.left_to_run == 0

            if reached_time or stopped_exec:
                # Priority: finished > syscall > time
                if proc.is_done():
                    reason = "finished"
                elif proc.is_waiting_for_sys_call():
                    reason = "syscall"
                else:
                    reason = "time"
                to_stop.append((slot, reason))

        for slot, reason in to_stop:
            self.output.unscheduled(slot.process.id, reason)
            self.process_queue.stop(slot)
            sys_slice = slot.process.get_sys_slice()
            if sys_slice is not None:
                self.system.make_sys_call(slot.process, sys_slice)

        self.fill_cores()

    def fill_cores(self) -> None:
        """
        Fill all available cores with runnable processes.

        Stops when no cores are free or no processes are runnable.
        """
        while self.process_queue.schedule_conditions():
            process = self.process_queue.pop_runnable(self.system, self.current_tick)
            if process is None:
                return
            core = self.process_queue.run(process)
            self.output.scheduled(process.id, core)

    def run(self) -> None:
        """
        Run the full simulation loop until completion.

        Each cycle:
        - Advance System state (memory, transfers).
        - Emit tick output.
        - Sleep briefly to slow down the log.
        - Run one scheduling step and refill cores.
        """
        self.fill_cores()
        while True:
            self.system.step()
            self.output.tick(self.current_tick)
            time.sleep(0.5)
            self.current_tick += 1
            self.step()








