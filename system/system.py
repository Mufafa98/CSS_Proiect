import math
from typing import List, Optional
from output import Output
from process.process import Process
from input import Input


class System:
    """
        System layer for the scheduler simulation.
        Contains RAM state, transfer state, CPU core info, and the
        privileged system process (pid 0) here.
    """

    # class invariant, checked at the start and end of every public method:
    def _check_invariant(self) -> None:
    #   - available_ram is always between 0 and total_ram
        assert 0 <= self.available_ram <= self.total_ram, (
            f"RAM accounting violated: available={self.available_ram}, "
            f"total={self.total_ram}"
        )

        # if a transfer is active, the related fields must be properly set
        if self.is_transferring:
            assert self.loading_process is not None, (
                "is_transferring is True but loading_process is None"
            )
            assert self.transfer_ticks_left > 0, (
                "is_transferring is True but transfer_ticks_left <= 0"
            )
        else:
            # no active transfer means these fields should be cleared
            assert self.loading_process is None, (
                "is_transferring is False but loading_process is not None"
            )
            assert self.transfer_ticks_left == 0, (
                "is_transferring is False but transfer_ticks_left != 0"
            )

        # every process listed in ram_content must actually be in memory
        for p in self.ram_content:
            assert p.is_in_memory(), (
                f"P{p.get_id()} is in ram_content but is_in_memory() is False"
            )

        # the total memory used by in-RAM processes must not exceed the limit
        consumed: int = sum(p.get_memory_required() for p in self.ram_content)
        assert consumed <= self.total_ram, (
            f"RAM over-committed: consumed={consumed}, total={self.total_ram}"
        )

    def __init__(self, input: Input, output: Output) -> None:
        """
        Build the full runtime state from parsed input.

        Parameters
        ----------
        input : Input
            Parsed simulation input with process list and machine limits.
        output : Output
            Output writer used for memory/scheduling logs.

        Returns
        -------
        None
            Sets up all internal fields in place.
        """
        
        assert input.memory_size > 0, (
            f"memory_size must be positive, got {input.memory_size}"
        )
        assert input.disk_speed > 0, (
            f"disk_speed must be positive, got {input.disk_speed}"
        )
        assert input.number_of_cores >= 1, (
            f"number_of_cores must be >= 1, got {input.number_of_cores}"
        )

        # The privileged system process (pid 0, highest priority).
        self.sys_proc: Process = Process(0, [], True)

        # System resource limits (read from input).
        self.total_ram: int = input.memory_size
        self.available_ram: int = input.memory_size
        self.transfer_rate: int = input.disk_speed
        self._num_cores: int = input.number_of_cores

        # Processes currently loaded in RAM.
        self.ram_content: List[Process] = []

        # LRU eviction stack: list of process IDs ordered least- to
        # most-recently-used (index 0 = least recently used).
        self.lru_stack: List[int] = []

        # Disk-transfer state (only one transfer can be active at a time).
        self.is_transferring: bool = False
        self.transfer_ticks_left: int = 0
        self.loading_process: Optional[Process] = None

        # Set of process IDs currently executing on a CPU core.
        self._running_pids: set[int] = set()

        # Index all user processes by their ID.
        self.processes: dict[int, Process] = {
            p.id: p for p in input.get_processes()
        }

        self.output: Output = output

        
        assert self.total_ram == self.available_ram, (
            "After __init__, available_ram must equal total_ram"
        )
        assert self.ram_content == [], (
            "After __init__, ram_content must be empty"
        )
        assert not self.is_transferring, (
            "After __init__, no transfer should be active"
        )

        self._check_invariant()

    def get_processes(self) -> List[Process]:
        """
        Get all user processes known by the system.

        Returns
        -------
        List[Process]
            New list with all user process objects.
        """
        self._check_invariant()

        result = list(self.processes.values())

        # there must be at least one user process
        assert len(result) > 0, "get_processes must return at least one process"
        # pid 0 is reserved for the system process, user processes must have pid > 0
        assert all(p.get_id() > 0 for p in result), (
            "All user processes must have pid > 0"
        )

        self._check_invariant()
        return result

    def get_system_process(self) -> Process:
        """
        Get the system process (pid 0).

        Returns
        -------
        Process
            The singleton privileged process.
        """
        self._check_invariant()

        result = self.sys_proc

        # the system process always has pid 0
        assert result.get_id() == 0, (
            f"System process must have pid 0, got {result.get_id()}"
        )

        self._check_invariant()
        return result

    def cores(self) -> List[int]:
        """
        Get all core IDs available in this simulation.

        Returns
        -------
        List[int]
            Core IDs from 1 to num_cores.
        """
        self._check_invariant()

        result = list(range(1, self._num_cores + 1))

        # the list must contain exactly as many cores as specified in the input
        assert len(result) == self._num_cores, (
            f"cores() must return exactly {self._num_cores} entries"
        )
        assert all(1 <= c <= self._num_cores for c in result), (
            "All core IDs must be in [1, num_cores]"
        )

        self._check_invariant()
        return result

    def make_sys_call(self, process: Process, time: int) -> None:
        """
        Queue a system-call request for a user process.

        Parameters
        ----------
        process : Process
            User process that requested the syscall.
        time : int
            Number of ticks needed for that syscall.

        Returns
        -------
        None
            Adds the request to the system-process queue.
        """
        self._check_invariant()

        assert process.get_id() > 0, (
            f"make_sys_call: process must be a user process (pid > 0), "
            f"got pid={process.get_id()}"
        )
        assert process.get_id() in self.processes, (
            f"make_sys_call: unknown process pid={process.get_id()}"
        )
        assert time > 0, (
            f"make_sys_call: time must be > 0, got {time}"
        )

        self.sys_proc.add_sys_call(process, time)

        self._check_invariant()

    def notify_running(self, process: Process) -> None:
        """
        Mark a process as currently running on CPU.

        so that LRU eviction never removes a process
        that is actively running.

        Parameters
        ----------
        process : Process
            Process that just got dispatched.

        Returns
        -------
        None
            Adds process ID to the running set.
        """
        self._check_invariant()

        # we can't run a process we don't know about
        assert process.get_id() in self.processes, (
            f"notify_running: unknown process pid={process.get_id()}"
        )
        # a process must be in RAM before it can be scheduled on a core
        assert process.is_in_memory(), (
            f"notify_running: P{process.get_id()} must be in RAM before running"
        )

        self._running_pids.add(process.get_id())

        # make sure the process was actually recorded as running
        assert process.get_id() in self._running_pids, (
            f"notify_running: P{process.get_id()} not recorded as running"
        )

        self._check_invariant()

    def notify_stopped(self, process: Process) -> None:
        """
        Mark a process as no longer running on CPU.

        After this, the process can become an eviction candidate again.

        Parameters
        ----------
        process : Process
            Process that was just unscheduled.

        Returns
        -------
        None
            Removes process ID from the running set.
        """
        self._check_invariant()

        assert process.get_id() in self.processes, (
            f"notify_stopped: unknown process pid={process.get_id()}"
        )
        assert process.get_id() in self._running_pids, (
            f"notify_stopped: P{process.get_id()} was not marked as running"
        )

        self._running_pids.discard(process.get_id())

        # the process must no longer appear in the running set
        assert process.get_id() not in self._running_pids, (
            f"notify_stopped: P{process.get_id()} still marked as running"
        )

        self._check_invariant()

    def get_available_ram(self) -> int:
        """
        Get currently free RAM.

        Returns
        -------
        int
            Free RAM in the same unit as the input file.
        """
        self._check_invariant()

        result = self.available_ram

        # returned value must be within the valid range
        assert 0 <= result <= self.total_ram, (
            f"get_available_ram returned out-of-range value: {result}"
        )

        self._check_invariant()
        return result

    def load_in_memory(self, process: Process) -> bool:
        """
        Ensure a process is available in RAM.

        If already in memory, this returns True.
        If not, either start a transfer (if idle) or keep waiting.

        Parameters
        ----------
        process : Process
            User process the scheduler wants to run.

        Returns
        -------
        bool
            True if process is ready in RAM now, False otherwise.
        """
        self._check_invariant()

        assert process.get_id() in self.processes, (
            f"load_in_memory: unknown process pid={process.get_id()}"
        )
        # if the process is larger than all of RAM it can never be loaded
        assert process.get_memory_required() <= self.total_ram, (
            f"load_in_memory: P{process.get_id()} requires "
            f"{process.get_memory_required()} but total RAM is {self.total_ram}"
        )

        if process.is_in_memory():
            self._update_lru(process.get_id())

            # if we return True the process must actually be in memory
            assert process.is_in_memory(), (
                "load_in_memory returned True but process is not in memory"
            )

            self._check_invariant()
            return True

        if self.is_transferring:
            self._check_invariant()
            return False

        self._initiate_transfer(process)

        # after starting a transfer, is_transferring must be True
        assert self.is_transferring, (
            "load_in_memory: transfer should have started"
        )

        self._check_invariant()
        return False

    def _initiate_transfer(self, process: Process) -> None:
        """
        Start loading a process from disk into RAM.

        If RAM is insufficient, evict LRU candidates first
        (but never currently running processes).

        Parameters
        ----------
        process : Process
            Process that needs to be loaded.

        Returns
        -------
        None
            Sets transfer state and writes a start log line.

        Raises
        ------
        MemoryError
            If there is still not enough evictable RAM after all valid evictions.
        """
        # starting a transfer for a process that's already in memory makes no sense
        assert not process.is_in_memory(), (
            f"_initiate_transfer: P{process.get_id()} is already in memory"
        )
        # only one disk transfer can run at a time
        assert not self.is_transferring, (
            "_initiate_transfer: a transfer is already in progress"
        )
        # if the process is bigger than total RAM it will never fit
        assert process.get_memory_required() <= self.total_ram, (
            f"_initiate_transfer: P{process.get_id()} will never fit in RAM"
        )

        while self.available_ram < process.get_memory_required():
            evicted: Optional[Process] = self._evict_lru()
            if evicted is None:
                raise MemoryError(
                    f"Cannot free enough RAM to load P{process.get_id()} "
                    f"(needs={process.get_memory_required()}, "
                    f"available={self.available_ram}). "
                    f"All evictable processes are currently running on a CPU."
                )

        ticks: int = max(1, math.ceil(process.get_memory_required() / self.transfer_rate))
        self.transfer_ticks_left = ticks
        self.is_transferring = True
        self.loading_process = process

        assert self.is_transferring, (
            "_initiate_transfer: is_transferring must be True after call"
        )
        assert self.loading_process is process, (
            "_initiate_transfer: loading_process must be set to the given process"
        )
        assert self.transfer_ticks_left >= 1, (
            f"_initiate_transfer: transfer_ticks_left must be >= 1, "
            f"got {self.transfer_ticks_left}"
        )
        # there must be enough free RAM to actually receive the process
        assert self.available_ram >= process.get_memory_required(), (
            f"_initiate_transfer: not enough RAM was freed before starting "
            f"transfer (available={self.available_ram}, "
            f"needed={process.get_memory_required()})"
        )

    def _evict_lru(self) -> Optional[Process]:
        """
        Evict one LRU process from RAM, but only if it is not running.

        Scan from oldest to newest LRU entry and remove the first valid one.

        Returns
        -------
        Optional[Process]
            Evicted process object, or None if no legal victim exists.
        """
        # nothing to evict if RAM is already empty
        assert len(self.ram_content) > 0, (
            "_evict_lru called but ram_content is empty – nothing to evict"
        )

        available_before: int = self.available_ram
        ram_count_before: int = len(self.ram_content)

        for lru_index, pid in enumerate(self.lru_stack):
            if pid in self._running_pids:
                # process is on a core, leave it alone
                continue

            victim: Optional[Process] = self.processes.get(pid)
            if victim is None or not victim.is_in_memory():
                # stale LRU entry, clean it up and retry
                self.lru_stack.pop(lru_index)
                return self._evict_lru()

            self.lru_stack.pop(lru_index)
            victim.evict_from_memory()
            self.ram_content.remove(victim)
            self.available_ram += victim.get_memory_required()

            self.output.unload_from_memory(victim.get_id())

            # the evicted process must no longer report itself as in memory
            assert not victim.is_in_memory(), (
                f"_evict_lru: P{victim.get_id()} still reports is_in_memory() "
                f"after eviction"
            )
            assert victim not in self.ram_content, (
                f"_evict_lru: P{victim.get_id()} still in ram_content after eviction"
            )
            # available RAM must have gone up by exactly the evicted process's footprint
            assert self.available_ram == available_before + victim.get_memory_required(), (
                "_evict_lru: available_ram not correctly updated after eviction"
            )
            assert len(self.ram_content) == ram_count_before - 1, (
                "_evict_lru: ram_content size did not decrease by 1"
            )

            return victim

        # nothing was evicted, so available_ram must be unchanged
        assert self.available_ram == available_before, (
            "_evict_lru: available_ram changed even though nothing was evicted"
        )
        return None

    def _update_lru(self, process_id: int) -> None:
        """
        Move a process ID to the MRU end of the LRU stack.

        Parameters
        ----------
        process_id : int
            ID of the process that was just accessed.

        Returns
        -------
        None
            Updates LRU ordering in place.
        """
        # the system process (pid 0) never goes into the LRU stack
        assert process_id > 0, (
            f"_update_lru: process_id must be > 0, got {process_id}"
        )

        if process_id in self.lru_stack:
            self.lru_stack.remove(process_id)
        self.lru_stack.append(process_id)

        # the just-accessed process must now be at the MRU end (last in the list)
        assert self.lru_stack[-1] == process_id, (
            f"_update_lru: P{process_id} must be at the MRU end of lru_stack"
        )
        # there should be no duplicates in the LRU stack
        assert self.lru_stack.count(process_id) == 1, (
            f"_update_lru: P{process_id} appears more than once in lru_stack"
        )

    def step(self) -> None:
        """
        Advance system state by one tick.

        If a transfer is active, decrement the counter and,
        when it reaches zero, finalize load into RAM and log it.

        Returns
        -------
        None
            Mutates transfer and RAM state if needed.
        """
        self._check_invariant()

        if self.is_transferring and self.loading_process:
            ticks_before: int = self.transfer_ticks_left

            self.transfer_ticks_left -= 1

            # loop variant: the counter must strictly decrease by 1 on every tick
            assert self.transfer_ticks_left == ticks_before - 1, (
                "step: transfer_ticks_left did not decrease by exactly 1"
            )

            self.output.load_in_memory(self.loading_process.get_id())

            if self.transfer_ticks_left <= 0:
                loaded: Process = self.loading_process

                loaded.load_into_memory()
                self.ram_content.append(loaded)
                self._update_lru(loaded.get_id())
                self.available_ram -= loaded.get_memory_required()

                self.is_transferring = False
                self.loading_process = None
                self.transfer_ticks_left = 0

                # transfer is done, the process must now be in RAM
                assert loaded.is_in_memory(), (
                    f"step: P{loaded.get_id()} should be in memory after transfer"
                )
                assert loaded in self.ram_content, (
                    f"step: P{loaded.get_id()} must be in ram_content after transfer"
                )

                assert not self.is_transferring, (
                    "step: is_transferring must be False after transfer completes"
                )
                assert self.loading_process is None, (
                    "step: loading_process must be None after transfer completes"
                )
                assert self.transfer_ticks_left == 0, (
                    "step: transfer_ticks_left must be 0 after transfer completes"
                )

        self._check_invariant()