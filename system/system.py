from typing import List, Dict
from process import Process
from input import Input

class System:
    def __init__(self, input: Input) -> None:
        self.processes = {}
        #maximum priority
        self.sys_proc = Process(0, [], True) 
        
        #system limits
        self.total_ram = 100         
        self.available_ram = 100     
        self.transfer_rate = 1       
        self._num_cores = 3          
        
        #memory management
        self.ram_content: List[Process] = [] 
        self.lru_stack: List[int] = []  
        
        #transfer state
        self.is_transferring = False     
        self.transfer_ticks_left = 0    
        self.loading_process = None      

        processes_unmaped = input.get_processes()
        self.processes = dict[int, Process]()
        for process in processes_unmaped:
            self.processes[process.id] = process 

    
    def get_processes(self) -> List[Process]:
        return list(self.processes.values())

    def get_system_process(self) -> Process:
        return self.sys_proc

    def cores(self) -> List[int]:
        return list(range(1, self._num_cores + 1))

    def make_sys_call(self, process: Process, time: int):
        self.sys_proc.add_sys_call(process, time)

    def load_in_memory(self, process: Process) -> bool:
        if not process.is_in_memory():
            self._update_lru(process.get_id())
            return True

        if self.is_transferring:
            return False

        self._initiate_transfer(process)
        return False 


    def _initiate_transfer(self, process: Process):

        while self.available_ram < process.get_memory_required():
            self._evict_lru()

        self.transfer_ticks_left = max(1, process.get_memory_required() // self.transfer_rate)
        self.is_transferring = True
        self.loading_process = process

    def _evict_lru(self):
        if not self.lru_stack: return
        
        victim_id = self.lru_stack.pop(0) 
        victim = self.processes.get(victim_id)
        
        if victim:
            victim.evict_from_memory() 
            if victim in self.ram_content:
                self.ram_content.remove(victim)
            self.available_ram += victim.get_memory_required()

    def _update_lru(self, process_id: int):
        if process_id in self.lru_stack:
            self.lru_stack.remove(process_id)
        self.lru_stack.append(process_id)

    def step(self):
        
        if self.is_transferring and self.loading_process:
            self.transfer_ticks_left -= 1 

            if self.transfer_ticks_left <= 0:
                self.loading_process.load_into_memory()
                self.ram_content.append(self.loading_process)
                self._update_lru(self.loading_process.get_id())
                # Scădem memoria ocupată din totalul liber.
                self.available_ram -= self.loading_process.get_memory_required()
                self.is_transferring = False
                self.loading_process = None

    def get_available_ram(self) -> int:
        return self.available_ram
