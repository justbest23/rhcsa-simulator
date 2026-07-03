"""
Post-setup sanity check (core.task_sanity).

A task must not already be passing right after setup and before the candidate
does anything — a pass at t=0 means the fault/precondition no-op'd (or it passes
on default state). These tests drive the check with a fake validator so no real
system state is touched.
"""

import pytest

from core import task_sanity


pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, passed, error_message=None):
        self.passed = passed
        self.error_message = error_message


class _Validator:
    """Stand-in for the ValidationEngine keyed on task id."""
    def __init__(self, verdicts):
        self._verdicts = verdicts  # task_id -> _Result | Exception

    def validate_task(self, task):
        v = self._verdicts[task.id]
        if isinstance(v, Exception):
            raise v
        return v


class _Task:
    def __init__(self, tid, category="services", has_setup=False, has_fault_injection=False):
        self.id = tid
        self.category = category
        self.has_setup = has_setup
        self.has_fault_injection = has_fault_injection


class TestCheckTask:
    def test_not_passing_at_start_is_fine(self):
        # The normal, healthy case: setup broke something, task fails until fixed.
        t = _Task("ok_001", has_fault_injection=True)
        v = _Validator({"ok_001": _Result(passed=False)})
        assert task_sanity.check_task(t, v) is None

    def test_already_passing_with_setup_is_flagged_as_noop(self):
        t = _Task("httpd_fault_001", has_fault_injection=True)
        v = _Validator({"httpd_fault_001": _Result(passed=True)})
        w = task_sanity.check_task(t, v)
        assert w is not None
        assert "httpd_fault_001" in w
        assert "no-op" in w.lower()

    def test_already_passing_without_setup_is_flagged_as_default_state(self):
        t = _Task("selinux_enforcing_001", has_setup=False, has_fault_injection=False)
        v = _Validator({"selinux_enforcing_001": _Result(passed=True)})
        w = task_sanity.check_task(t, v)
        assert w is not None
        assert "default" in w.lower()

    def test_validation_error_is_not_flagged(self):
        # If validate() couldn't produce a trustworthy verdict, don't cry wolf.
        t = _Task("weird_001", has_setup=True)
        v = _Validator({"weird_001": _Result(passed=True, error_message="Validation error: boom")})
        assert task_sanity.check_task(t, v) is None

    def test_validator_exception_is_swallowed(self):
        t = _Task("boom_001")
        v = _Validator({"boom_001": RuntimeError("kaboom")})
        assert task_sanity.check_task(t, v) is None


class TestCheckTasks:
    def test_returns_and_counts_only_suspicious(self, monkeypatch):
        tasks = [
            _Task("free_pass_001", has_fault_injection=True),
            _Task("healthy_001", has_fault_injection=True),
        ]
        v = _Validator({
            "free_pass_001": _Result(passed=True),
            "healthy_001": _Result(passed=False),
        })
        monkeypatch.setattr(task_sanity, "get_validator", lambda: v, raising=False)
        # get_validator is imported inside check_tasks from core.validator; patch there
        import core.validator as CV
        monkeypatch.setattr(CV, "get_validator", lambda: v)

        warnings = task_sanity.check_tasks(tasks, verbose_console=False)
        assert len(warnings) == 1
        assert "free_pass_001" in warnings[0]
