from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from scheduler.scheduler import Scheduler
from scheduler.process_queue import ProcessQueue


class DummyProcess:
    def __init__(
        self,
        pid: int,
        left_to_run: int = 1,
        sys_proc: bool = False,
        release_time: int = 0,
        syscall_after_tick: bool = False,
        syscall_slice: int | None = None,
    ) -> None:
        self.id = pid
        self.left_to_run = left_to_run
        self.sys_proc = sys_proc
        self._release_time = release_time
        self._syscall_after_tick = syscall_after_tick
        self._syscall_slice = syscall_slice
        self._last_cpu = None

    def tick(self) -> None:
        if self.left_to_run > 0:
            self.left_to_run -= 1

    def is_done(self) -> bool:
        return self.left_to_run == 0

    def is_waiting_for_sys_call(self) -> bool:
        return self._syscall_after_tick and self.left_to_run > 0

    def get_sys_slice(self):
        return self._syscall_slice

    def get_release_time(self) -> int:
        return self._release_time

    def get_last_cpu(self):
        return self._last_cpu

    def record_cpu(self, core: int) -> None:
        self._last_cpu = core

class DummyInput:
    def __init__(self, user_slice=2, sys_slice=1) -> None:
        self._user_slice = user_slice
        self._sys_slice = sys_slice

    def get_user_slice(self):
        return self._user_slice

    def get_sys_slice(self):
        return self._sys_slice

def make_system(processes, system_proc=None, cores=(0, 1)):
    system = MagicMock()
    system.get_processes.return_value = processes
    system.get_system_process.return_value = system_proc
    system.cores.return_value = list(cores)
    system.load_in_memory.return_value = True
    return system

def make_output():
    return MagicMock()


class TestScheduler(unittest.TestCase):
    def test_scheduler_step_time_slice_unschedule(self):
        """Unschedules a process when time slice is reached."""
        p1 = DummyProcess(1, left_to_run=5)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=1, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()
        scheduler.step()

        output.unscheduled.assert_called_once_with(p1.id, "time")

    def test_scheduler_step_finished_unschedule(self):
        """Unschedules a process when it finishes."""
        p1 = DummyProcess(1, left_to_run=1)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=5, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()
        scheduler.step()

        output.unscheduled.assert_called_once_with(p1.id, "finished")

    def test_fill_cores_schedules_processes(self):
        """Schedules runnable processes across available cores."""
        p1 = DummyProcess(1, left_to_run=1)
        p2 = DummyProcess(2, left_to_run=1)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1, p2], sys_p, cores=[0, 1])
        output = make_output()
        inp = DummyInput(user_slice=2, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()

        self.assertEqual(output.scheduled.call_count, 2)

    def test_scheduler_step_syscall_unschedule_and_enqueue_syscall(self):
        """Unschedules and enqueues syscall when a syscall is pending."""
        p1 = DummyProcess(1, left_to_run=3, syscall_after_tick=True, syscall_slice=2)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=1, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()
        scheduler.step()

        output.unscheduled.assert_called_once_with(p1.id, "syscall")
        system.make_sys_call.assert_called_once_with(p1, 2)

    def test_scheduler_round_robin_order(self):
        """Schedules user processes in round-robin order via scheduler.step."""
        p1 = DummyProcess(1, left_to_run=5)
        p2 = DummyProcess(2, left_to_run=5)
        p3 = DummyProcess(3, left_to_run=5)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1, p2, p3], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=1, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()

        for _ in range(3):
            scheduler.step()

        scheduled_ids = [c.args[0] for c in output.scheduled.call_args_list]
        self.assertEqual(scheduled_ids, [1, 2, 3, 1])

    def test_scheduler_respects_user_and_system_time_slices(self):
        """User and system processes are preempted at their respective time slices."""
        p_user = DummyProcess(1, left_to_run=5)
        p_sys = DummyProcess(0, left_to_run=5, sys_proc=True)

        system = make_system([p_user], p_sys, cores=[0, 1])
        output = make_output()
        inp = DummyInput(user_slice=2, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()

        scheduler.step()
        self.assertEqual(len(output.unscheduled.call_args_list), 1)
        self.assertEqual(output.unscheduled.call_args_list[0].args, (p_sys.id, "time"))

        scheduler.step()
        self.assertEqual(len(output.unscheduled.call_args_list), 2)
        self.assertEqual(output.unscheduled.call_args_list[1].args, (p_user.id, "time"))

    def test_scheduler_step_raises_on_empty_system(self):
        """Raises when stepping with no runnable or waiting processes."""
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)
        system = make_system([], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=1, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        with self.assertRaises(RuntimeError):
            scheduler.step()

    def test_scheduler_step_with_invalid_slice_type_raises(self):
        """Raises TypeError when time slices are not integers."""
        class BadInput:
            def get_user_slice(self):
                return None
            def get_sys_slice(self):
                return None

        p1 = DummyProcess(1, left_to_run=2)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        output = make_output()

        scheduler = Scheduler(BadInput(), system, output)
        scheduler.fill_cores()

        with self.assertRaises(TypeError):
            scheduler.step()

    def test_scheduler_stop_reason_priority_finished_over_time(self):
        """Finished reason takes priority over time-slice expiration."""
        p1 = DummyProcess(1, left_to_run=1)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        output = make_output()
        inp = DummyInput(user_slice=1, sys_slice=1)

        scheduler = Scheduler(inp, system, output)
        scheduler.fill_cores()
        scheduler.step()

        output.unscheduled.assert_called_once_with(p1.id, "finished")


class TestProcessQueue(unittest.TestCase):
    def test_process_queue_system_process_priority(self):
        """System process is chosen before user processes."""
        p1 = DummyProcess(1, left_to_run=1)
        sys_p = DummyProcess(0, left_to_run=2, sys_proc=True)

        system = make_system([p1], sys_p, [0])
        q = ProcessQueue(
            system.get_processes(), 
            system.get_system_process(), 
            system.cores()
        )

        runnable = q.pop_runnable(system, current_tick=0)
        self.assertIs(runnable, sys_p)

    def test_process_queue_pop_runnable_respects_release_time(self):
        """Skips processes until their release time."""
        p1 = DummyProcess(1, left_to_run=1, release_time=5)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, [0])
        q = ProcessQueue(
            system.get_processes(), 
            system.get_system_process(), 
            system.cores()
        )

        self.assertIsNone(q.pop_runnable(system, current_tick=0))
        self.assertIs(q.pop_runnable(system, current_tick=5), p1)

    def test_process_queue_stop_moves_done_and_waiting(self):
        """Moves processes to done or waiting on stop."""
        p2 = DummyProcess(2, left_to_run=2)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p2], sys_p, cores=[0])
        q = ProcessQueue(
            system.get_processes(), 
            system.get_system_process(), 
            system.cores()
        )

        # Not done -> goes back to waiting
        runnable = q.pop_runnable(system, current_tick=0)
        q.run(runnable)
        slot = q.running()[0]
        slot.process.tick()
        q.stop(slot)

        self.assertEqual(q.count_waiting(), 1)
        self.assertEqual(q.count_running(), 0)

        # Done -> goes to done list

        runnable = q.pop_runnable(system, current_tick=1)
        q.run(runnable)
        slot = q.running()[0]
        slot.process.tick()
        q.stop(slot)

        self.assertEqual(q.count_waiting(), 0)
        self.assertEqual(q.count_running(), 0)
        self.assertEqual(q.count_done(), 1)

    def test_process_queue_affinity_reschedules_on_same_core(self):
        """Reschedules a process on its last core when available."""
        p1 = DummyProcess(1, left_to_run=2)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0, 1])
        q = ProcessQueue(
            system.get_processes(),
            system.get_system_process(),
            system.cores()
        )

        runnable = q.pop_runnable(system, current_tick=0)
        first_core = q.run(runnable)
        slot = q.running()[0]
        q.stop(slot)

        # If affinity were ignored, pop() would choose the rightmost free core.
        fallback_core = q._ProcessQueue__free_cores[-1]
        self.assertNotEqual(fallback_core, first_core)

        runnable2 = q.pop_runnable(system, current_tick=1)
        second_core = q.run(runnable2)

        self.assertEqual(second_core, first_core)
        self.assertNotEqual(second_core, fallback_core)

    def test_process_queue_requires_loaded_in_memory(self):
        """Only runs a process after it is loaded in memory."""
        p1 = DummyProcess(1, left_to_run=1)
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)

        system = make_system([p1], sys_p, cores=[0])
        q = ProcessQueue(
            system.get_processes(),
            system.get_system_process(),
            system.cores()
        )

        system.load_in_memory.return_value = False
        self.assertIsNone(q.pop_runnable(system, current_tick=0))
        self.assertEqual(q.count_waiting(), 1)

        system.load_in_memory.return_value = True
        self.assertIs(q.pop_runnable(system, current_tick=0), p1)

    def test_process_queue_init_with_none_waiting_raises(self):
        """Rejects non-iterable waiting list."""
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)
        with self.assertRaises(TypeError):
            ProcessQueue(None, sys_p, [0])

    def test_process_queue_init_with_none_cores_raises(self):
        """Rejects non-iterable cores list."""
        sys_p = DummyProcess(0, left_to_run=0, sys_proc=True)
        with self.assertRaises(TypeError):
            ProcessQueue([], sys_p, None)



if __name__ == "__main__":
    unittest.main()