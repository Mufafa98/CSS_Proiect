import pytest
from process import Process


# -------------------------
# INITIALIZATION / PARSING
# -------------------------

def test_process_parses_sequence_correctly():
    p = Process(1, [5, 2, 3, 4, 6], False)

    assert len(p._stages) == 3
    assert p._stages[0].run_ticks == 5
    assert p._stages[0].sys_call_ticks == 2
    assert p._stages[2].run_ticks == 6
    assert p._stages[2].sys_call_ticks is None


def test_empty_sequence_raises():
    with pytest.raises(ValueError):
        Process(1, [], False)


# -------------------------
# TICK BEHAVIOR
# -------------------------

def test_tick_decrements_run():
    p = Process(1, [5, 2], False)
    initial = p.get_left_to_run()

    p.tick()

    assert p.get_left_to_run() == initial - 1


def test_tick_does_nothing_when_zero():
    p = Process(1, [1, 2], False)
    p.left_to_run = 0

    p.tick()
    assert p.get_left_to_run() == 0


# -------------------------
# ADVANCE LOGIC
# -------------------------

def test_advance_moves_to_next_stage():
    p = Process(1, [2, 3, 4], False)

    p.left_to_run = 0
    p.advance()

    assert p._stage_index == 1
    assert p.get_left_to_run() == 4


def test_advance_when_no_more_stages_raises():
    p = Process(1, [2], False)
    p.left_to_run = 0

    with pytest.raises(AssertionError):
        p.advance()


# -------------------------
# SYS CALL WAITING LOGIC
# -------------------------

def test_is_waiting_for_sys_call_true(): ##evita already done
    p = Process(1, [2, 3, 4], False)

    p.left_to_run = 0

    assert p.is_waiting_for_sys_call()


def test_is_done_true():
    p = Process(1, [1], False)
    p.left_to_run = 0
    p._stage_index = len(p._stages) - 1

    assert p.is_done()


def test_is_done_false_if_not_finished():
    p = Process(1, [5, 2], False)

    assert not p.is_done()


# -------------------------
# CPU HISTORY
# -------------------------

def test_cpu_history_tracking():
    p = Process(1, [5, 2], False)

    p.record_cpu(1)
    p.record_cpu(3)

    assert p.get_last_cpu() == 3
    assert p.get_cpu_history() == [1, 3]


def test_no_cpu_history():
    p = Process(1, [5, 2], False)

    assert p.get_last_cpu() is None


# -------------------------
# MEMORY FLAGS
# -------------------------

def test_memory_load_and_evict():
    p = Process(1, [5, 2], False)

    assert not p.is_in_memory()

    p.load_into_memory()
    assert p.is_in_memory()

    p.evict_from_memory()
    assert not p.is_in_memory()