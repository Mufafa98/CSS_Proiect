# class ExecutionStage:
#     """
#     Represents one stage of a user process:
#       - run_ticks: how many ticks this segment runs for
#       - sys_call_ticks: how many ticks the subsequent system call takes
#                         (None if this is the last segment — no sys call after it)
#     """
#
#     def __init__(self, run_ticks: int, sys_call_ticks: int | None) -> None:
#         if run_ticks <= 0:
#             raise ValueError(f"run_ticks must be positive, got {run_ticks}")
#         if sys_call_ticks is not None and sys_call_ticks <= 0:
#             raise ValueError(f"sys_call_ticks must be positive or None, got {sys_call_ticks}")
#
#         self.run_ticks = run_ticks
#         self.sys_call_ticks = sys_call_ticks
#
#     def __repr__(self) -> str:
#         return f"ExecutionStage(run={self.run_ticks}, sys_call={self.sys_call_ticks})"

class ExecutionStage:

    def __init__(self, run_ticks: int, sys_call_ticks: int | None) -> None:

        # PRECONDITIONS
        assert isinstance(run_ticks, int), "run_ticks must be integer."
        assert run_ticks > 0, "run_ticks must be positive."
        assert sys_call_ticks is None or sys_call_ticks > 0, "sys_call_ticks must be positive or None."

        self.run_ticks = run_ticks
        self.sys_call_ticks = sys_call_ticks

        # POSTCONDITIONS
        assert self.run_ticks > 0
        assert self.sys_call_ticks is None or self.sys_call_ticks > 0

    def __repr__(self) -> str:
        return f"ExecutionStage(run={self.run_ticks}, sys_call={self.sys_call_ticks})"