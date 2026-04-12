from process import Process

class System:
    def __init__(self, input: Input) -> None:
        self.processes = dict[int, Process]()
        counter = 0
        while True:
            execution = input.get_next_execution_sequence()
            if execution == None:
                return
            self.processes[counter] = Process(counter, execution, False)
            counter += 1

    def get_processes(self) -> list[Process]:
        return list(self.processes.values())

    def cores(self) -> list[int]:
        return [1]

class Input:
    def __init__(self):
        self.execution_sequence = [
                [5, 6, 5, 7, 8, 5, 8],
                [4],
                [5, 7, 5, 7, 7, 7, 5]
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