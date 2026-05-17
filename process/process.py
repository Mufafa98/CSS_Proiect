from collections import deque
from execution_stage import ExecutionStage


class SysCallRequest:
    """
    Represents a pending system call queued inside the system process.
    Holds a reference to the user process that requested it, and how
    many ticks remain to execute it.
    """

    def __init__(self, requester: "Process", ticks: int) -> None:
        self.requester = requester   # the user process waiting for this sys call
        self.ticks = ticks           # remaining ticks for this sys call

    def __repr__(self) -> str:
        return f"SysCallRequest(from={self.requester.id}, ticks={self.ticks})"


class Process:

    def _check_invariants(self) -> None:
        """ Class invariants for Process. """

        # Common invariants
        assert self.id >= 0, "Process id must be non-negative."

        assert self.release_time >= 0, "Release time cannot be negative."

        assert self.memory_required >= 0, "Memory requirement cannot be negative."

        assert self.left_to_run >= 0, "left_to_run cannot be negative."

        # System process invariants
        if self.sys_proc:

            assert len(self._stages) == 0, "System process must not contain execution stages."

        # User process invariants
        else:

            assert len(self._stages) > 0, "User process must contain stages."

            assert 0 <= self._stage_index < len(self._stages), "Stage index out of bounds."

            current = self._stages[self._stage_index]

            # STATE CONSISTENCY
            assert 0 <= self.left_to_run <= current.run_ticks, "Process runtime inconsistent with current stage."


    # def __init__(self, id: int, execution_sequence: list[int], sys_proc: bool, release_time: int = 0, memory_required: int = 0) -> None:
    #     """
    #     Parameters
    #     ----------
    #     id                  : unique integer identifier
    #     execution_sequence  : flat list as described above
    #                           (must be empty for the system process)
    #     sys_proc            : True if this is the system process
    #     """
    #     if sys_proc and len(execution_sequence) != 0:
    #         raise ValueError(
    #             "The system process must be initialised with an empty execution sequence."
    #         )
    #
    #     self.id: int = id
    #     self.sys_proc: bool = sys_proc
    #     self.release_time: int = release_time
    #     self.memory_required: int = memory_required
    #     self.in_memory: bool = False
    #
    #     # User process setup
    #     if not sys_proc:
    #         self._stages: list[ExecutionStage] = self._parse_sequence(execution_sequence)
    #         self._stage_index: int = 0          # which ExecutionStage we are in
    #         self.left_to_run: int = self._stages[0].run_ticks  # ticks left in current run segment
    #     else:
    #         self._stages = []
    #         self._stage_index = 0
    #         self.left_to_run: int = 0

    def __init__(
            self,
            id: int,
            execution_sequence: list[int],
            sys_proc: bool,
            release_time: int = 0,
            memory_required: int = 0
    ) -> None:

        if sys_proc and len(execution_sequence) != 0:
            raise ValueError(
                "The system process must be initialised with an empty execution sequence."
            )

        self.id: int = id
        self.sys_proc: bool = sys_proc
        self.release_time: int = release_time
        self.memory_required: int = memory_required
        self.in_memory: bool = False

        # User process setup
        if not sys_proc:
            self._stages: list[ExecutionStage] = self._parse_sequence(execution_sequence)
            self._stage_index: int = 0
            self.left_to_run: int = self._stages[0].run_ticks
        else:
            self._stages = []
            self._stage_index = 0
            self.left_to_run = 0

        # Queue for system process
        self._sys_queue: deque[SysCallRequest] = deque()

        # CPU affinity history
        self._cpu_history: list[int] = []

        # CLASS INVARIANT CHECK
        self._check_invariants()


    # Private helpers 

    # @staticmethod
    # def _parse_sequence(seq: list[int]) -> list[ExecutionStage]:
    #     """
    #     Convert a flat list [r0, s0, r1, s1, …, rN] into ExecutionStage objects.
    #
    #     Example: [5, 2, 3, 4, 9, 4, 6]
    #       index 0 -> run=5, sys=2
    #       index 2 -> run=3, sys=4
    #       index 4 -> run=9, sys=4
    #       index 6 -> run=6, sys=None   <- last segment has no sys call
    #     """
    #     if len(seq) == 0:
    #         raise ValueError("execution_sequence cannot be empty for a user process.")
    #
    #     stages = []
    #     i = 0
    #     while i < len(seq):
    #         run_ticks = seq[i]
    #         sys_call_ticks = seq[i + 1] if i + 1 < len(seq) else None
    #         stages.append(ExecutionStage(run_ticks, sys_call_ticks))
    #         i += 2
    #     return stages

    @staticmethod
    def _parse_sequence(seq: list[int]) -> list[ExecutionStage]:
        """
        Convert a flat list [r0, s0, r1, s1, …, rN] into ExecutionStage objects.
        """

        if len(seq) == 0:
            raise ValueError("execution_sequence cannot be empty for a user process.")

        stages = []
        i = 0
        while i < len(seq):
            # LOOP INVARIANTS
            assert i % 2 == 0, \
                "Sequence index must always point to run_ticks."
            assert len(stages) == i // 2, \
                "Stage count inconsistent during parsing."

            run_ticks = seq[i]
            sys_call_ticks = seq[i + 1] if i + 1 < len(seq) else None
            stages.append(ExecutionStage(run_ticks, sys_call_ticks))
            i += 2

        # POSTCONDITIONS
        assert len(stages) > 0, \
            "Parsed stages cannot be empty."
        assert len(stages) == (len(seq) + 1) // 2, \
            "Incorrect number of parsed stages."

        return stages

    # def _current_stage(self) -> ExecutionStage:
    #     assert not self.sys_proc, "System process has no stages."
    #     assert self._stage_index < len(self._stages), "Stage index out of bounds."
    #     return self._stages[self._stage_index]

    def _current_stage(self) -> ExecutionStage:
        # PRECONDITIONS
        assert not self.sys_proc, "System process has no execution stages."
        assert 0 <= self._stage_index < len(self._stages), "Stage index out of bounds."
        stage = self._stages[self._stage_index]

        # POSTCONDITION
        assert isinstance(stage, ExecutionStage), "Current stage must be an ExecutionStage."

        return stage


    # Getters

    def get_id(self) -> int:
        return self.id

    def get_priority(self) -> int:
        """Returns 1 for system process (higher), 0 for user process."""
        return 1 if self.sys_proc else 0

    def get_type(self) -> str:
        return "system" if self.sys_proc else "user"

    def get_left_to_run(self) -> int:
        return self.left_to_run

    def get_cpu_history(self) -> list[int]:
        """Returns the full CPU history (most recent is last)."""
        return list(self._cpu_history)

    def get_last_cpu(self) -> int | None:
        """Returns the most recently used CPU id, or None if never ran."""
        return self._cpu_history[-1] if self._cpu_history else None

    def get_release_time(self) -> int:
        return self.release_time

    def get_memory_required(self) -> int:
        return self.memory_required

    def is_in_memory(self) -> bool:
        return self.in_memory


    # def load_into_memory(self) -> None:
    #     self.in_memory = True
    def load_into_memory(self) -> None:

        # PRECONDITION
        assert not self.in_memory, "Process already loaded into memory."

        self.in_memory = True

        # POSTCONDITION
        assert self.in_memory, "Process should be in memory after loading."

        self._check_invariants()


    # def evict_from_memory(self) -> None:
    #     self.in_memory = False

    def evict_from_memory(self) -> None:

        # PRECONDITION
        assert self.in_memory, "Cannot evict process that is not in memory."

        self.in_memory = False

        # POSTCONDITION
        assert not self.in_memory, "Process should not be in memory after eviction."

        self._check_invariants()

    # State queries

    def is_done(self) -> bool:
        """
        A user process is done when it has exhausted all stages and has
        no ticks left to run.
        A system process is never 'done' in this sense.
        """
        if self.sys_proc:
            return False
        last_stage = self._stage_index >= len(self._stages) - 1
        return last_stage and self.left_to_run == 0

    def is_waiting_for_sys_call(self) -> bool:
        """True when a user process has finished a run segment and is
        waiting for the system process to service its sys call."""
        if self.sys_proc:
            return False
        return self.left_to_run == 0 and not self.is_done()

    # Core execution methods

    # def tick(self) -> None:
    #     """
    #     Advance the process by one unit of time.
    #
    #     User process  -> decrements left_to_run for the current segment.
    #                      Also decrements the current stage's run_ticks so the
    #                      object stays consistent.
    #     System process -> decrements ticks on the front SysCallRequest.
    #                      When that request finishes, calls advance() on the
    #                      requesting process and moves to the next request.
    #     """
    #     if self.left_to_run == 0:
    #         # Nothing to do this tick (waiting for sys call or truly done)
    #         return
    #
    #     self.left_to_run -= 1
    #
    #     if self.sys_proc:
    #         # Decrement the active sys call request
    #         req = self._sys_queue[0]
    #         req.ticks -= 1
    #         if req.ticks == 0:
    #             # Sys call finished -> notify the user process
    #             req.requester.advance()
    #             self._sys_queue.popleft()
    #             # Load next request if there is one
    #             if self._sys_queue:
    #                 self.left_to_run = self._sys_queue[0].ticks
    #     else:
    #         # User process: mirror the decrement on the stage object
    #         self._stages[self._stage_index].run_ticks -= 1

    def tick(self) -> None:
        """
        Advance the process by one unit of time.
        """

        # CLASS INVARIANT
        self._check_invariants()

        # PRECONDITION
        assert self.left_to_run >= 0, "left_to_run cannot be negative."

        if self.left_to_run == 0:
            return

        self.left_to_run -= 1

        # POSTCONDITION
        assert self.left_to_run >= 0, "left_to_run became negative after tick."

        if self.sys_proc:

            # SYSTEM PROCESS PRECONDITION
            assert len(self._sys_queue) > 0, "System process running without pending syscalls."

            req = self._sys_queue[0]
            req.ticks -= 1

            assert req.ticks >= 0, "System call ticks became negative."

            if req.ticks == 0:

                # CLIENT-SERVER ASSERTION
                assert req.requester.is_waiting_for_sys_call(), "Requester should be waiting for syscall completion."

                req.requester.advance()
                self._sys_queue.popleft()
                if self._sys_queue:
                    self.left_to_run = self._sys_queue[0].ticks
                else:
                    self.left_to_run = 0

        else:
            # User process consistency
            self._stages[self._stage_index].run_ticks -= 1

            assert self._stages[self._stage_index].run_ticks >= 0, "Stage runtime became negative."

        # CLASS INVARIANT
        self._check_invariants()


    # def advance(self) -> None:
    #     """
    #     Called by the system process after finishing this process's sys call.
    #     Moves the user process to the next execution stage and loads its
    #     run_ticks into left_to_run so the scheduler can run it again.
    #     """
    #     assert not self.sys_proc, "advance() should not be called on the system process."
    #     self._stage_index += 1
    #     assert self._stage_index < len(self._stages), (
    #         f"advance() called but no more stages for process {self.id}"
    #     )
    #     self.left_to_run = self._stages[self._stage_index].run_ticks

    def advance(self) -> None:
        """
        Move user process to the next execution stage.
        """

        # PRECONDITIONS
        assert not self.sys_proc, "advance() cannot be called on system process."

        assert self.left_to_run == 0, "advance() called before current stage completed."

        self._stage_index += 1

        # POSTCONDITION
        assert self._stage_index < len(self._stages), f"No more stages available for process {self.id}."

        self.left_to_run = self._stages[self._stage_index].run_ticks

        # POSTCONDITION
        assert self.left_to_run > 0, "Next stage must contain positive runtime."

        self._check_invariants()


    # only reads, never advances
    def get_sys_slice(self) -> int | None:
        if self.sys_proc:
            return None
        if self.left_to_run != 0:
            return None

        current = self._current_stage()
        return current.sys_call_ticks  # None if last stage, duration otherwise

    # def add_sys_call(self, requester: "Process", ticks: int) -> None:
    #     """
    #     System process only.
    #     Enqueues a new sys call request.
    #     If the queue was empty, loads left_to_run immediately.
    #     """
    #     assert self.sys_proc, "add_sys_call() must only be called on the system process."
    #     req = SysCallRequest(requester, ticks)
    #     self._sys_queue.append(req)
    #     if self.left_to_run == 0:
    #         self.left_to_run = self._sys_queue[0].ticks

    def add_sys_call(self, requester: "Process", ticks: int) -> None:
        """
        System process only.
        Enqueues a new system call request.
        """

        # PRECONDITIONS
        assert self.sys_proc, "add_sys_call() only valid for system process."

        assert ticks > 0,  "System call ticks must be positive."

        assert not requester.sys_proc, "System process cannot request system calls."

        req = SysCallRequest(requester, ticks)

        self._sys_queue.append(req)

        if self.left_to_run == 0:
            self.left_to_run = self._sys_queue[0].ticks

        # POSTCONDITION
        assert len(self._sys_queue) > 0, "Syscall queue should not be empty after insertion."

        self._check_invariants()


    # def record_cpu(self, cpu_id: int) -> None:
    #     """
    #     Called by the scheduler when this process is dispatched to a CPU.
    #     Keeps a history of which CPUs the process has used (most recent last).
    #     """
    #     self._cpu_history.append(cpu_id)

    def record_cpu(self, cpu_id: int) -> None:
        """ Record CPU affinity history. """
        # PRECONDITION
        assert cpu_id >= 0, "CPU id must be non-negative."

        self._cpu_history.append(cpu_id)

        # POSTCONDITION
        assert self.get_last_cpu() == cpu_id, "CPU history was not updated correctly."

        self._check_invariants()



    # String representations

    def __str__(self) -> str:
        if not self.sys_proc:
            return (
                f"Process(id={self.id}, stage={self._stage_index}/{len(self._stages)-1}, "
                f"left={self.left_to_run})"
            )
        else:
            queue_repr = list(self._sys_queue)
            return f"SysProcess(id={self.id}, left={self.left_to_run}, queue={queue_repr})"

    def __repr__(self) -> str:
        return self.__str__()

