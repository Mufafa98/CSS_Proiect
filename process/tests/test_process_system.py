import pytest
from process import Process


# -------------------------
# SYSTEM PROCESS INIT RULES
# -------------------------

def test_system_process_must_have_empty_sequence():
    with pytest.raises(ValueError):
        Process(0, [1, 2], True)


def test_system_process_valid_init():
    sys = Process(0, [], True)
    assert sys.get_type() == "system"


# -------------------------
# SYS CALL QUEUE
# -------------------------

def test_add_sys_call():
    sys = Process(0, [], True)
    user = Process(1, [5, 2], False)

    sys.add_sys_call(user, 3)

    assert len(sys._sys_queue) == 1
    assert sys.left_to_run == 3


def test_multiple_sys_calls_queueing():
    sys = Process(0, [], True)
    u1 = Process(1, [5, 2], False)
    u2 = Process(2, [3, 1], False)

    sys.add_sys_call(u1, 2)
    sys.add_sys_call(u2, 4)

    assert len(sys._sys_queue) == 2


# -------------------------
# SYS CALL EXECUTION
# -------------------------

def test_sys_call_tick_decrements():
    sys = Process(0, [], True)
    user = Process(1, [5, 2], False)

    sys.add_sys_call(user, 2)

    sys.tick()
    assert sys._sys_queue[0].ticks == 1


def test_sys_call_completion_removes_request():
    sys = Process(0, [], True)
    user = Process(1, [2, 3, 4], False)

    sys.add_sys_call(user, 1)

    sys.tick()

    assert len(sys._sys_queue) == 0


def test_sys_call_exec_triggers_user_advance():
    sys = Process(0, [], True)
    user = Process(1, [2, 3, 4], False)

    sys.add_sys_call(user, 1)

    user.left_to_run = 0
    old_stage = user._stage_index

    sys.tick()

    assert user._stage_index == old_stage + 1


# -------------------------
# EDGE CASES
# -------------------------

def test_tick_on_empty_sys_queue_raises():
    sys = Process(0, [], True)

    sys.left_to_run = 1  # force tick attempt

    with pytest.raises(IndexError):
        sys.tick()


def test_get_priority():
    sys = Process(0, [], True)
    user = Process(1, [5, 2], False)

    assert sys.get_priority() == 1
    assert user.get_priority() == 0


# -------------------------
# CPU HISTORY ALSO WORKS FOR SYS
# -------------------------

def test_sys_cpu_history():
    sys = Process(0, [], True)

    sys.record_cpu(1)
    sys.record_cpu(2)

    assert sys.get_last_cpu() == 2