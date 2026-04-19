from mock import Input, System
from .process_queue import ProcessQueue 
import time

class Scheduler:
    def __init__(self, input: Input, system: System) -> None:
        self.user_slice = input.get_user_slice()
        self.sys_slice = input.get_sys_slice()

        self.process_queue = ProcessQueue(system.get_processes(), system.get_system_process(), system.cores())
        self.system = system

    def step(self):
        if self.process_queue.count_runing() == 0:
            print(f"Nothing to run {self.process_queue}")
            exit(0)

        to_stop = []

        for process in self.process_queue.running():
            process.process.tick()
            print(f"Run on core {process.core} {process} {self.process_queue}")
            process.time += 1

            time_slice = self.user_slice if not process.process.sys_proc else self.sys_slice
            if process.time >= time_slice or process.process.left_to_run == 0:
                reason = "time" if process.time >= time_slice else "finished"
                to_stop.append((process, reason))

        for (process, reason) in to_stop:
            print(f"Stop proc {process.process.id} reason: {reason}")
            self.process_queue.stop(process)
            sys_slice = process.process.get_sys_slice()
            if sys_slice is not None:
                self.system.make_sys_call(process.process, sys_slice)

        self.fill_cores()
   
    def fill_cores(self):
        while True:
            if not self.process_queue.schedule_conditions():
                return

            process = self.process_queue.pop_runable(self.system)
            if process == None:
                return

            self.process_queue.run(process)


    def run(self):
        cycle = 0
        self.fill_cores()
        while True:
            time.sleep(0.35)
            print(f"cycle {cycle}")
            cycle += 1
            self.step()
            self.fill_cores()








