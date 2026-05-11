import sys
import unittest
import tempfile
from pathlib import Path

# Ensure project root is on sys.path so packages are importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input import Input
import output
from ui.parsing import parse_input, parse_log, build_memory_timeline, InputConfig, Interval

class TestUIParsing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_tmp(self, name: str, content: str) -> Path:
        p = self.tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_parse_input_success(self):
        content = """
MEMORY 100
DISK_RATE 10

PROCESS 1 50 0 5 2 3
PROCESS 2 30 1 4 3
"""
        p = self._write_tmp("input.txt", content)
        cfg = parse_input(p)
        
        self.assertIsInstance(cfg, InputConfig)
        self.assertEqual(cfg.memory_total, 100)
        self.assertEqual(cfg.disk_rate, 10)
        self.assertEqual(cfg.process_mem[1], 50)
        self.assertEqual(cfg.process_release[2], 1)
        self.assertEqual(cfg.process_seq[1], [5, 2, 3])

    def test_parse_input_missing_fields(self):
        p = self._write_tmp("input.txt", "PROCESS 1 50 0 5 2 3\n")
        with self.assertRaises(ValueError):
            parse_input(p)

    def test_parse_input_malformed_process(self):
        content = """
MEMORY 100
DISK_RATE 5
PROCESS 1 50
"""
        p = self._write_tmp("input.txt", content)
        with self.assertRaises(ValueError):
            parse_input(p)

    def test_parse_log_basic(self):
        # create a simple log with tick, schedule, unschedule, load/unload
        log = """
[Tick] time 0
[Schedule] process 1 core 0
[Tick] time 1
[Unschedule] process 1 reason finished
[Tick] time 2
[LoadMem] process 2
[Tick] time 3
[UnloadMem] process 2
"""
        p = self._write_tmp("log2.txt", log)
        intervals, cores, final_time, loadmem, unloadmem = parse_log(p)
        
        self.assertTrue(any(i.pid == 1 for i in intervals))
        self.assertIn(0, cores)
        self.assertGreaterEqual(final_time, 4)
        # loadmem at tick current_time+1: LoadMem at time 2 -> entry at 3
        self.assertEqual(len(loadmem), final_time)
        self.assertTrue(any(2 in lst for lst in loadmem))
        self.assertTrue(any(2 in lst for lst in unloadmem))

    def test_parse_log_running_left_unknown(self):
        # process scheduled but never unscheduled -> unknown end
        log = """
[Tick] time 0
[Schedule] process 5 core 1
"""
        p = self._write_tmp("log2.txt", log)
        intervals, cores, final_time, loadmem, unloadmem = parse_log(p)
        self.assertTrue(any(i.pid == 5 and i.end_reason == "unknown" for i in intervals))

    def test_build_memory_timeline_disk_rate_and_limits(self):
        # single tick, one pid, disk_rate limited
        loadmem = [[1], []]
        unloadmem = [[], []]
        final_time = 2
        memory_total = 10
        disk_rate = 3
        process_mem = {1: 8}
        
        timeline = build_memory_timeline(loadmem, unloadmem, final_time, memory_total, disk_rate, process_mem)
        
        # after first tick, pid 1 should have received min(disk_rate, memory_total)
        self.assertEqual(timeline[0], [(1, 3)])
        
        # if disk_rate is 0 or memory_total <=0, nothing loads
        t2 = build_memory_timeline(loadmem, unloadmem, final_time, 0, 3, process_mem)
        self.assertEqual(t2[0], [])
        
        t3 = build_memory_timeline(loadmem, unloadmem, final_time, 10, 0, process_mem)
        self.assertEqual(t3[0], [])


class TestInputParsing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_tmp(self, name: str, content: str) -> Path:
        p = self.tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_input_parses_fields_and_processes(self):
        content = """
# comment line
PROCESSORS 4
MEMORY 100
TIMESLICE 5
SYS_PERIOD 2
DISK_RATE 10

PROCESS 1 50 0 5 2 3 # inline comment
PROCESS 2 30 1 4
"""
        p = self._write_tmp("input.txt", content)
        cfg = Input(p)

        self.assertEqual(cfg.number_of_cores, 4)
        self.assertEqual(cfg.memory_size, 100)
        self.assertEqual(cfg.user_slice, 5)
        self.assertEqual(cfg.sys_slice, 2)
        self.assertEqual(cfg.disk_speed, 10)
        self.assertEqual(len(cfg.get_processes()), 2)

    def test_input_allows_no_processes(self):
        content = """
PROCESSORS 2
MEMORY 256
TIMESLICE 4
SYS_PERIOD 1
DISK_RATE 8
"""
        p = self._write_tmp("input.txt", content)
        cfg = Input(p)

        self.assertEqual(cfg.get_processes(), [])

    def test_input_rejects_even_execution_sequence(self):
        content = """
PROCESSORS 1
MEMORY 100
TIMESLICE 5
SYS_PERIOD 1
DISK_RATE 10
PROCESS 1 50 0 5 2
"""
        p = self._write_tmp("input.txt", content)
        with self.assertRaises(ValueError):
            Input(p)

    def test_input_malformed_process_line_raises(self):
        content = """
PROCESSORS 1
MEMORY 100
TIMESLICE 5
SYS_PERIOD 1
DISK_RATE 10
PROCESS 1 50
"""
        p = self._write_tmp("input.txt", content)
        with self.assertRaises(IndexError):
            Input(p)

    def test_input_non_numeric_field_raises(self):
        content = """
PROCESSORS X
MEMORY 100
TIMESLICE 5
SYS_PERIOD 1
DISK_RATE 10
PROCESS 1 50 0 3
"""
        p = self._write_tmp("input.txt", content)
        with self.assertRaises(ValueError):
            Input(p)

    def test_input_missing_timeslice_or_sys_period_access_raises(self):
        content = """
PROCESSORS 1
MEMORY 100
DISK_RATE 10
PROCESS 1 50 0 3
"""
        p = self._write_tmp("input.txt", content)
        cfg = Input(p)

        with self.assertRaises(AttributeError):
            cfg.get_user_slice()

        with self.assertRaises(AttributeError):
            cfg.get_sys_slice()


class TestOutputLogging(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.original_path = output.LOG_OUTPUT_PATH
        output.LOG_OUTPUT_PATH = str(self.tmp_path / "log.txt")
        self.out = output.Output()

    def tearDown(self):
        try:
            self.out.close()
        except Exception:
            pass
        output.LOG_OUTPUT_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_output_writes_expected_lines(self):
        self.out.tick(0)
        self.out.scheduled(1, 2)
        self.out.unscheduled(1, "finished")
        self.out.load_in_memory(3)
        self.out.unload_from_memory(3)
        self.out.close()

        lines = (self.tmp_path / "log.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            lines,
            [
                "[   Tick   ] time 0",
                "[ Schedule ] process 1 core 2",
                "[Unschedule] process 1 reason finished",
                "[ LoadMem  ] process 3",
                "[UnloadMem ] process 3",
            ],
        )

    def test_output_rejects_negative_tick(self):
        with self.assertRaises(ValueError):
            self.out.tick(-1)

    def test_output_rejects_negative_schedule_ids(self):
        with self.assertRaises(ValueError):
            self.out.scheduled(-1, 0)
        with self.assertRaises(ValueError):
            self.out.scheduled(1, -1)

    def test_output_rejects_negative_unschedule_pid(self):
        with self.assertRaises(ValueError):
            self.out.unscheduled(-1, "test")

    def test_output_rejects_negative_memory_pid(self):
        with self.assertRaises(ValueError):
            self.out.load_in_memory(-1)
        with self.assertRaises(ValueError):
            self.out.unload_from_memory(-2)

    def test_output_rejects_invalid_unschedule_reason(self):
        with self.assertRaises(ValueError):
            self.out.unscheduled(1, "invalid-reason")

    def test_output_accepts_valid_unschedule_reasons(self):
        # should not raise
        self.out.unscheduled(1, "finished")
        self.out.unscheduled(2, "sys-call")
        self.out.unscheduled(3, "time")


if __name__ == "__main__":
    unittest.main(verbosity=2)