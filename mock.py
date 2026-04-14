from typing import Deque
from process import Process
class System:
    def __init__(self, input: Input) -> None:
        self.processes = dict[int, Process]()
        self.sys_proc = Process(0, [], True)
        counter = 1
        while True:
            execution = input.get_next_execution_sequence()
            if execution == None:
                return
            self.processes[counter] = Process(counter, execution, False)
            counter += 1

    def get_processes(self) -> list[Process]:
        return list(self.processes.values())

    def get_system_process(self) -> Process:
        return self.sys_proc

    def cores(self) -> list[int]:
        return [1, 2, 3]

    def make_sys_call(self, process: Process, time: int):
        self.sys_proc.add_sys_call(process, time)


class Input:
    def __init__(self):
        self.execution_sequence = [
                [3, 2, 3],
                [3],
                [3, 2, 3]
                ]
        self.sequence_returned = -1

    def get_user_slice(self) -> int:
        return 3

    def get_sys_slice(self) -> int:
        return 5

    def get_next_execution_sequence(self) -> list[int] | None:
        if self.sequence_returned == len(self.execution_sequence) - 1:
            return None
        self.sequence_returned += 1
        return self.execution_sequence[self.sequence_returned]
