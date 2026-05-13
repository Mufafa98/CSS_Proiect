import math
import unittest
from unittest.mock import MagicMock
from system.system import System

# Helpers
def make_input(memory_size=1000, disk_speed=100, number_of_cores=2, processes=None):
    """Return a mock that looks like an Input object."""
    inp = MagicMock()
    inp.memory_size = memory_size
    inp.disk_speed = disk_speed
    inp.number_of_cores = number_of_cores
    inp.get_processes.return_value = processes if processes is not None else []
    return inp

def make_output():
    """Return a mock that looks like an Output object."""
    out = MagicMock()
    return out

def make_process(pid, memory=100, in_memory=False):
    """Return a mock Process with the minimum interface System relies on."""
    p = MagicMock()
    p.get_id.return_value = pid
    p.id = pid
    p.is_in_memory.return_value = in_memory
    p.get_memory_required.return_value = memory
    p.load_into_memory = MagicMock()
    p.evict_from_memory = MagicMock()
    return p

def make_system(memory_size=1000, disk_speed=100, number_of_cores=2, processes=None):
    """Convenience: build a System with mock Input / Output."""
    inp = make_input(memory_size, disk_speed, number_of_cores, processes)
    out = make_output()
    return System(inp, out), out


class TestInit(unittest.TestCase):
    def test_fields_set_from_input(self):
        inp = make_input(memory_size=512, disk_speed=50, number_of_cores=4)
        out = make_output()
        s = System(inp, out)

        self.assertEqual(s.total_ram, 512)
        self.assertEqual(s.available_ram, 512)
        self.assertEqual(s.transfer_rate, 50)
        self.assertEqual(s._num_cores, 4)
        self.assertFalse(s.is_transferring)
        self.assertEqual(s.transfer_ticks_left, 0)
        self.assertIsNone(s.loading_process)
        self.assertEqual(s.ram_content, [])
        self.assertEqual(s.lru_stack, [])
        # Test if sys proc has id 0 and no running procs
        self.assertEqual(s.sys_proc.get_id(), 0)
        self.assertEqual(len(s._running_pids), 0)

    def test_processes_dict_built_from_input(self):
        p1 = make_process(1)
        p2 = make_process(2)
        s, _ = make_system(processes=[p1, p2])
        self.assertIn(1, s.processes)
        self.assertIn(2, s.processes)

class TestMakeSysCall(unittest.TestCase):
    def test_delegates_to_sys_proc(self):
        s, _ = make_system()
        proc = make_process(1)
        s.sys_proc = MagicMock()
        s.make_sys_call(proc, 5)
        s.sys_proc.add_sys_call.assert_called_once_with(proc, 5)

    def test_negative_syscall_raises(self):
        s, _ = make_system()
        proc = make_process(1)
        with self.assertRaises(ValueError):
            s.make_sys_call(proc, -1)


class TestNotifyRunningStopped(unittest.TestCase):
    def test_adds_pid(self):
        s, _ = make_system()
        p = make_process(1)
        s.notify_running(p)
        self.assertIn(1, s._running_pids)


        p2 = make_process(2)
        p3 = make_process(3)
        s.notify_running(p2)
        s.notify_running(p3)
        self.assertIn(2, s._running_pids)
        self.assertIn(3, s._running_pids)

        before_len = len(s._running_pids)
        s.notify_running(p2)
        self.assertEqual(before_len, len(s._running_pids))

    def test_removes_pid(self):
        s, _ = make_system()
        s._running_pids.update({1, 2, 3})
        s.notify_stopped(make_process(2))
        self.assertIn(1, s._running_pids)
        self.assertIn(3, s._running_pids)
        self.assertNotIn(2, s._running_pids)


class TestLoadInMemory(unittest.TestCase):
    def test_in_memory_returns_true_and_refreshes_lru(self):
        s, _ = make_system()
        p = make_process(1, in_memory=True)
        s.lru_stack = [1]
        result = s.load_in_memory(p)
        self.assertTrue(result)
        self.assertEqual(s.lru_stack[-1], 1)

    def test_transfer_active_returns_false(self):
        s, _ = make_system()
        p = make_process(1, in_memory=False)
        s.is_transferring = True
        result = s.load_in_memory(p)
        self.assertFalse(result)

    def test_no_transfer_starts_one_and_returns_false(self):
        s, _ = make_system(memory_size=500, disk_speed=100)
        p = make_process(1, memory=100, in_memory=False)
        s.processes[1] = p
        result = s.load_in_memory(p)
        self.assertFalse(result)
        self.assertTrue(s.is_transferring)
        self.assertIs(s.loading_process, p)


class TestInitiateTransfer(unittest.TestCase):
    def test_ticks_is_ceil_of_memory_over_rate(self):
        s, _ = make_system(memory_size=500, disk_speed=30)
        p = make_process(1, memory=100)
        s._initiate_transfer(p)
        expected = max(1, math.ceil(100 / 30))
        self.assertEqual(s.transfer_ticks_left, expected)

    def test_memory_error_when_all_running(self):
        s, _ = make_system(memory_size=200, disk_speed=100)
        s.available_ram = 50

        victim = make_process(10, memory=100, in_memory=True)
        s.processes[10] = victim
        s.ram_content = [victim]
        s.lru_stack = [10]
        s._running_pids = {10}

        p = make_process(1, memory=100)
        with self.assertRaises(MemoryError):
            s._initiate_transfer(p)

    def test_evicts_when_not_enough_ram(self):
        """If available_ram < required, _evict_lru must be called.
        (insufficient resources - insufficient RAM is a distinct case)
        """
        s, _ = make_system(memory_size=200, disk_speed=100)
        # Only 50 units free, process needs 100 -> must evict
        s.available_ram = 50

        victim = make_process(10, memory=100, in_memory=True)
        victim.evict_from_memory = MagicMock(side_effect=lambda: setattr(victim, '_in_memory', False))
        s.processes[10] = victim
        s.ram_content = [victim]
        s.lru_stack = [10]
        # victim is not running
        s._running_pids = set()

        p = make_process(1, memory=100)
        s._initiate_transfer(p)

        victim.evict_from_memory.assert_called_once()

class TestEvictLru(unittest.TestCase):
    def _setup_system_with_victims(self, victims, running_pids=None):
        s, out = make_system(memory_size=10000, disk_speed=100)
        s._running_pids = set(running_pids or [])
        s.lru_stack = []
        s.ram_content = []
        for pid, mem in victims:
            p = make_process(pid, memory=mem, in_memory=True)
            s.processes[pid] = p
            s.ram_content.append(p)
            s.lru_stack.append(pid)
        s.available_ram = 0
        return s, out

    def test_evicts_oldest_non_running_process_updates_state(self):
        s, out = self._setup_system_with_victims([(1, 100), (2, 200)])
        victim = s.processes[1]
        evicted = s._evict_lru()

        self.assertEqual(evicted.get_id(), 1)
        self.assertNotIn(1, s.lru_stack)
        self.assertNotIn(victim, s.ram_content)
        self.assertEqual(s.available_ram, 100)
        out.unload_from_memory.assert_called_once_with(1)

    def test_skips_running_process(self):
        s, _ = self._setup_system_with_victims([(1, 100), (2, 200)], running_pids=[1])
        evicted = s._evict_lru()
        self.assertEqual(evicted.get_id(), 2)

    def test_stale_lru_entry_is_cleaned_up(self):
        s, _ = make_system()
        victim = make_process(2, memory=100, in_memory=True)
        s.processes[2] = victim
        s.ram_content = [victim]
        s.lru_stack = [999, 2]
        s.available_ram = 0
        s._running_pids = set()

        evicted = s._evict_lru()
        self.assertEqual(evicted.get_id(), 2)
        self.assertNotIn(999, s.lru_stack)

    def test_returns_none_when_all_running(self):
        s, _ = self._setup_system_with_victims([(1, 100), (2, 200)], running_pids=[1, 2])
        result = s._evict_lru()
        self.assertIsNone(result)


class TestUpdateLru(unittest.TestCase):
    def test_appends_new_pid(self):
        s, _ = make_system()
        s._update_lru(5)
        self.assertEqual(s.lru_stack, [5])

    def test_moves_existing_pid_to_end(self):
        s, _ = make_system()
        s.lru_stack = [1, 2, 3]
        s._update_lru(1)
        self.assertEqual(s.lru_stack, [2, 3, 1])


class TestStep(unittest.TestCase):
    def test_step_decrements_ticks_and_calls_output(self):
        s, out = make_system()
        p = make_process(1, memory=100)
        s.is_transferring = True
        s.loading_process = p
        s.transfer_ticks_left = 2

        s.step()

        self.assertEqual(s.transfer_ticks_left, 1)
        out.load_in_memory.assert_called_once_with(1)

    def test_step_finalises_load_when_ticks_reach_zero(self):
        s, _ = make_system(memory_size=500, disk_speed=100)
        p = make_process(1, memory=100)
        s.is_transferring = True
        s.loading_process = p
        s.transfer_ticks_left = 1
        initial_ram = s.available_ram

        s.step()

        self.assertFalse(s.is_transferring)
        self.assertIsNone(s.loading_process)
        p.load_into_memory.assert_called_once()
        self.assertIn(p, s.ram_content)
        self.assertIn(1, s.lru_stack)
        self.assertEqual(s.available_ram, initial_ram - 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)