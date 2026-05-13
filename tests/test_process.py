import unittest
from process import Process

from process import ExecutionStage


class TestExecutionStage(unittest.TestCase):
    def test_valid_execution_stage(self):
        s = ExecutionStage(5, 2)
        self.assertEqual(s.run_ticks, 5)
        self.assertEqual(s.sys_call_ticks, 2)

    def test_last_stage_allows_none(self):
        s = ExecutionStage(4, None)
        self.assertIsNone(s.sys_call_ticks)

    def test_invalid_run_ticks_zero(self):
        with self.assertRaises(ValueError):
            ExecutionStage(0, 2)

    def test_invalid_run_ticks_negative(self):
        with self.assertRaises(ValueError):
            ExecutionStage(-1, 2)

    def test_invalid_sys_call_negative(self):
        with self.assertRaises(ValueError):
            ExecutionStage(5, -3)

    def test_repr(self):
        s = ExecutionStage(3, 1)
        self.assertIn("ExecutionStage", repr(s))

class TestProcessUser(unittest.TestCase):
    # -------------------------
    # INITIALIZATION / PARSING
    # -------------------------

    def test_process_parses_sequence_correctly(self):
        p = Process(1, [5, 2, 3, 4, 6], False)

        self.assertEqual(len(p._stages), 3)
        self.assertEqual(p._stages[0].run_ticks, 5)
        self.assertEqual(p._stages[0].sys_call_ticks, 2)
        self.assertEqual(p._stages[2].run_ticks, 6)
        self.assertIsNone(p._stages[2].sys_call_ticks)

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            Process(1, [], False)

    # -------------------------
    # TICK BEHAVIOR
    # -------------------------

    def test_tick_decrements_run(self):
        p = Process(1, [5, 2], False)
        initial = p.get_left_to_run()

        p.tick()

        self.assertEqual(p.get_left_to_run(), initial - 1)

    def test_tick_does_nothing_when_zero(self):
        p = Process(1, [1, 2], False)
        p.left_to_run = 0

        p.tick()
        self.assertEqual(p.get_left_to_run(), 0)

    def test_tick_after_done_does_not_go_negative(self):
        p = Process(1, [1], False)
        p.tick()

        p.tick()
        self.assertEqual(p.get_left_to_run(), 0)
    # -------------------------
    # ADVANCE LOGIC
    # -------------------------

    def test_advance_moves_to_next_stage(self):
        p = Process(1, [2, 3, 4], False)

        p.left_to_run = 0
        p.advance()

        self.assertEqual(p._stage_index, 1)
        self.assertEqual(p.get_left_to_run(), 4)

    def test_advance_when_no_more_stages_raises(self):
        p = Process(1, [2], False)
        p.left_to_run = 0

        with self.assertRaises(AssertionError):
            p.advance()

    # -------------------------
    # SYS CALL WAITING LOGIC
    # -------------------------

    def test_is_waiting_for_sys_call_true(self):
        p = Process(1, [2, 3, 4], False)

        p.left_to_run = 0

        self.assertTrue(p.is_waiting_for_sys_call())

    def test_is_done_true(self):
        p = Process(1, [1], False)
        p.left_to_run = 0
        p._stage_index = len(p._stages) - 1

        self.assertTrue(p.is_done())

    def test_is_done_false_if_not_finished(self):
        p = Process(1, [5, 2], False)

        self.assertFalse(p.is_done())

    # -------------------------
    # CPU HISTORY
    # -------------------------

    def test_cpu_history_tracking(self):
        p = Process(1, [5, 2], False)

        p.record_cpu(1)
        p.record_cpu(3)

        self.assertEqual(p.get_last_cpu(), 3)
        self.assertEqual(p.get_cpu_history(), [1, 3])

    def test_no_cpu_history(self):
        p = Process(1, [5, 2], False)

        self.assertIsNone(p.get_last_cpu())

    # -------------------------
    # MEMORY FLAGS
    # -------------------------

    def test_memory_load_and_evict(self):
        p = Process(1, [5, 2], False)

        self.assertFalse(p.is_in_memory())

        p.load_into_memory()
        self.assertTrue(p.is_in_memory())

        p.evict_from_memory()
        self.assertFalse(p.is_in_memory())

class TestProcessSystem(unittest.TestCase):
    # -------------------------
    # SYSTEM PROCESS INIT RULES
    # -------------------------

    def test_system_process_must_have_empty_sequence(self):
        with self.assertRaises(ValueError):
            Process(0, [1, 2], True)

    def test_system_process_valid_init(self):
        sys = Process(0, [], True)
        self.assertEqual(sys.get_type(), "system")

    # -------------------------
    # SYS CALL QUEUE
    # -------------------------

    def test_add_sys_call(self):
        sys = Process(0, [], True)
        user = Process(1, [5, 2], False)

        sys.add_sys_call(user, 3)

        self.assertEqual(len(sys._sys_queue), 1)
        self.assertEqual(sys.left_to_run, 3)

    def test_multiple_sys_calls_queueing(self):
        sys = Process(0, [], True)
        u1 = Process(1, [5, 2], False)
        u2 = Process(2, [3, 1], False)

        sys.add_sys_call(u1, 2)
        sys.add_sys_call(u2, 4)

        self.assertEqual(len(sys._sys_queue), 2)

    # -------------------------
    # SYS CALL EXECUTION
    # -------------------------

    def test_sys_call_tick_decrements(self):
        sys = Process(0, [], True)
        user = Process(1, [5, 2], False)

        sys.add_sys_call(user, 2)

        sys.tick()
        self.assertEqual(sys._sys_queue[0].ticks, 1)

    def test_sys_call_completion_removes_request(self):
        sys = Process(0, [], True)
        user = Process(1, [2, 3, 4], False)

        sys.add_sys_call(user, 1)

        sys.tick()

        self.assertEqual(len(sys._sys_queue), 0)

    def test_sys_call_exec_triggers_user_advance(self):
        sys = Process(0, [], True)
        user = Process(1, [2, 3, 4], False)

        sys.add_sys_call(user, 1)

        user.left_to_run = 0
        old_stage = user._stage_index

        sys.tick()

        self.assertEqual(user._stage_index, old_stage + 1)

    # -------------------------
    # EDGE CASES
    # -------------------------

    def test_tick_on_empty_sys_queue_raises(self):
        sys = Process(0, [], True)

        sys.left_to_run = 1  # force tick attempt

        with self.assertRaises(IndexError):
            sys.tick()

    def test_get_priority(self):
        sys = Process(0, [], True)
        user = Process(1, [5, 2], False)

        self.assertEqual(sys.get_priority(), 1)
        self.assertEqual(user.get_priority(), 0)

    # -------------------------
    # CPU HISTORY ALSO WORKS FOR SYS
    # -------------------------

    def test_sys_cpu_history(self):
        sys = Process(0, [], True)

        sys.record_cpu(1)
        sys.record_cpu(2)

        self.assertEqual(sys.get_last_cpu(), 2)


if __name__ == "__main__":
    unittest.main()