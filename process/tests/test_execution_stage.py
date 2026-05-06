import pytest

from process import ExecutionStage


def test_valid_execution_stage():
    s = ExecutionStage(5, 2)
    assert s.run_ticks == 5
    assert s.sys_call_ticks == 2


def test_last_stage_allows_none():
    s = ExecutionStage(4, None)
    assert s.sys_call_ticks is None


def test_invalid_run_ticks_zero():
    with pytest.raises(ValueError):
        ExecutionStage(0, 2)


def test_invalid_run_ticks_negative():
    with pytest.raises(ValueError):
        ExecutionStage(-1, 2)


def test_invalid_sys_call_zero():
    with pytest.raises(ValueError):
        ExecutionStage(5, 0)


def test_invalid_sys_call_negative():
    with pytest.raises(ValueError):
        ExecutionStage(5, -3)


def test_repr():
    s = ExecutionStage(3, 1)
    assert "ExecutionStage" in repr(s)