import sys
import unittest
import tempfile
from pathlib import Path

# Ensure project root is on sys.path so `ui` package is importable when running
# the test file directly or under different CWDs.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
        print(f"[test_ui_parsing] wrote temporary file: {p}")
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
        print(f"[test_ui_parsing] parsed input config: memory={cfg.memory_total}, disk_rate={cfg.disk_rate}, processes={sorted(cfg.process_mem)}")
        
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
        print(f"[test_ui_parsing] log summary: intervals={len(intervals)}, cores={cores}, final_time={final_time}")
        
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
        print(f"[test_ui_parsing] memory timeline tick0: {timeline[0]}")
        
        # after first tick, pid 1 should have received min(disk_rate, memory_total)
        self.assertEqual(timeline[0], [(1, 3)])
        
        # if disk_rate is 0 or memory_total <=0, nothing loads
        t2 = build_memory_timeline(loadmem, unloadmem, final_time, 0, 3, process_mem)
        self.assertEqual(t2[0], [])
        
        t3 = build_memory_timeline(loadmem, unloadmem, final_time, 10, 0, process_mem)
        self.assertEqual(t3[0], [])


if __name__ == "__main__":
    print("[test_ui_parsing] running directly with unittest")
    unittest.main(verbosity=2)