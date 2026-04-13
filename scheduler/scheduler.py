
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
            return
        
        for process in self.process_queue.running():
            process.process.tick()
            print(f"Run {process} {self.process_queue}")
            process.time += 1

            if process.time >= self.user_slice or process.process.left_to_run == 0:
                self.process_queue.stop(process)
                sys_slice = process.process.get_sys_slice()
                if sys_slice is not None:
                    self.system.make_sys_call(process.process, sys_slice)
    
    def run(self):
        cycle = 0
        while True:
            time.sleep(0.35)
            print(f"cycle {cycle}")
            cycle += 1
            self.step()
            if not self.process_queue.schedule_conditions():
                continue
    
            process = self.process_queue.pop_runable()
            if process == None:
                continue

            self.process_queue.run(process)








