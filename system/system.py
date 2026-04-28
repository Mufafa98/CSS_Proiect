from typing import List, Optional
from output import Output
from process import Process
from input import Input


class System:
    """
        System layer for the scheduler simulation.
        Contains RAM state, transfer state, CPU core info, and the
        privileged system process (pid 0) here.
    """

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

    def get_processes(self) -> List[Process]:
        """
        Get all user processes known by the system.

        Returns
        -------
        List[Process]
            New list with all user process objects.
        """
        return list(self.processes.values())

    def get_system_process(self) -> Process:
        """
        Get the system process (pid 0).

        Returns
        -------
        Process
            The singleton privileged process.
        """
        return self.sys_proc

    def cores(self) -> List[int]:
        """
        Get all core IDs available in this simulation.

        Returns
        -------
        List[int]
            Core IDs from 1 to num_cores.
        """
        return list(range(1, self._num_cores + 1))

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
        self.sys_proc.add_sys_call(process, time)

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
        self._running_pids.add(process.get_id())

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
        self._running_pids.discard(process.get_id())

    def get_available_ram(self) -> int:
        """
        Get currently free RAM.

        Returns
        -------
        int
            Free RAM in the same unit as the input file.
        """
        return self.available_ram


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
        if process.is_in_memory():
            # Process is already in RAM, refresh its LRU position and allow
            # the scheduler to dispatch it immediately.
            self._update_lru(process.get_id())
            return True

        # Process is not in RAM.
        if self.is_transferring:
            # Another disk transfer is already running; cannot start a second.
            return False

        # No transfer active, begin loading this process from disk.
        self._initiate_transfer(process)
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
        while self.available_ram < process.get_memory_required():
            evicted: Optional[Process] = self._evict_lru()
            if evicted is None:
                raise MemoryError(
                    f"Cannot free enough RAM to load P{process.get_id()} "
                    f"(needs={process.get_memory_required()}, "
                    f"available={self.available_ram}). "
                    f"All evictable processes are currently running on a CPU."
                )

        ticks: int = max(1, process.get_memory_required() // self.transfer_rate)
        self.transfer_ticks_left = ticks
        self.is_transferring = True
        self.loading_process = process


    def _evict_lru(self) -> Optional[Process]:
        """
        Evict one LRU process from RAM, but only if it is not running.

        Scan from oldest to newest LRU entry and remove the first valid one.

        Returns
        -------
        Optional[Process]
            Evicted process object, or None if no legal victim exists.
        """
        for lru_index, pid in enumerate(self.lru_stack):
            if pid in self._running_pids:
                # This process is on a CPU, evicting it would be illegal.
                continue

            victim: Optional[Process] = self.processes.get(pid)
            if victim is None or not victim.is_in_memory():
                # Stale LRU entry (process already evicted or unknown), clean up.
                self.lru_stack.pop(lru_index)
                return self._evict_lru()

            # Found a valid, non-running victim, evict it.
            self.lru_stack.pop(lru_index)
            victim.evict_from_memory()
            self.ram_content.remove(victim)
            self.available_ram += victim.get_memory_required()

            self.output.unload_from_memory(victim.get_id())
            return victim

        # All in-memory processes are currently running, nothing can be evicted.
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
        if process_id in self.lru_stack:
            self.lru_stack.remove(process_id)
        self.lru_stack.append(process_id)

   
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
        if self.is_transferring and self.loading_process:
            self.transfer_ticks_left -= 1
            self.output.load_in_memory(self.loading_process.get_id())
            if self.transfer_ticks_left <= 0:
                loaded: Process = self.loading_process

                loaded.load_into_memory()
                self.ram_content.append(loaded)
                self._update_lru(loaded.get_id())
                self.available_ram -= loaded.get_memory_required()

                self.is_transferring = False
                self.loading_process = None