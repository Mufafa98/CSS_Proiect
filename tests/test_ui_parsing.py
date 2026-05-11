import sys
import pytest
from pathlib import Path

# Ensure project root is on sys.path so `ui` package is importable when running
# the test file directly or under different CWDs.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.parsing import parse_input, parse_log, build_memory_timeline, InputConfig, Interval


def write_tmp(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    print(f"[test_ui_parsing] wrote temporary file: {p}")
    return p


def test_parse_input_success(tmp_path: Path):
    content = """
MEMORY 100
DISK_RATE 10

PROCESS 1 50 0 5 2 3
PROCESS 2 30 1 4 3
"""
    p = write_tmp(tmp_path, "input.txt", content)
    cfg = parse_input(p)
    print(f"[test_ui_parsing] parsed input config: memory={cfg.memory_total}, disk_rate={cfg.disk_rate}, processes={sorted(cfg.process_mem)}")
    assert isinstance(cfg, InputConfig)
    assert cfg.memory_total == 100
    assert cfg.disk_rate == 10
    assert cfg.process_mem[1] == 50
    assert cfg.process_release[2] == 1
    assert cfg.process_seq[1] == [5, 2, 3]


def test_parse_input_missing_fields(tmp_path: Path):
    p = write_tmp(tmp_path, "input.txt", "PROCESS 1 50 0 5 2 3\n")
    with pytest.raises(ValueError):
        parse_input(p)


def test_parse_input_malformed_process(tmp_path: Path):
    content = """
MEMORY 100
DISK_RATE 5
PROCESS 1 50
"""
    p = write_tmp(tmp_path, "input.txt", content)
    with pytest.raises(ValueError):
        parse_input(p)


def test_parse_log_basic(tmp_path: Path):
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
    p = write_tmp(tmp_path, "log2.txt", log)
    intervals, cores, final_time, loadmem, unloadmem = parse_log(p)
    print(f"[test_ui_parsing] log summary: intervals={len(intervals)}, cores={cores}, final_time={final_time}")
    assert any(i.pid == 1 for i in intervals)
    assert 0 in cores
    assert final_time >= 4
    # loadmem at tick current_time+1: LoadMem at time 2 -> entry at 3
    assert len(loadmem) == final_time
    assert any(2 in lst for lst in loadmem)
    assert any(2 in lst for lst in unloadmem)


def test_parse_log_running_left_unknown(tmp_path: Path):
    # process scheduled but never unscheduled -> unknown end
    log = """
[Tick] time 0
[Schedule] process 5 core 1
"""
    p = write_tmp(tmp_path, "log2.txt", log)
    intervals, cores, final_time, loadmem, unloadmem = parse_log(p)
    assert any(i.pid == 5 and i.end_reason == "unknown" for i in intervals)


def test_build_memory_timeline_disk_rate_and_limits():
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
    assert timeline[0] == [(1, 3)]
    # if disk_rate is 0 or memory_total <=0, nothing loads
    t2 = build_memory_timeline(loadmem, unloadmem, final_time, 0, 3, process_mem)
    assert t2[0] == []
    t3 = build_memory_timeline(loadmem, unloadmem, final_time, 10, 0, process_mem)
    assert t3[0] == []


if __name__ == "__main__":
    print("[test_ui_parsing] running directly with pytest -s")
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
