"""
Quick-practice must mutate the machine like exam/practice/adaptive modes do.

Regression guard: run_quick_practice() once generated + validated tasks without
injecting faults or establishing negative preconditions, so troubleshooting
tasks had nothing to fix and positive-config tasks passed with no work done. It
must now drive the same core.task_env lifecycle:

    session_reset  ->  setup_task  ->  (validate)  ->  teardown_task  ->  reset_after_task
"""

import builtins
import pytest

import rhcsa_simulator as R
from core import task_env
from tasks.registry import TaskRegistry
from core import validator as V
from core import results_db as RDB
from utils import formatters as fmt
from utils import helpers as H


pytestmark = pytest.mark.unit


class _FakeTask:
    id = "fake_task_001"
    category = "services"
    difficulty = "exam"
    points = 10
    description = "Start and enable a service"
    hints = ["systemctl enable --now svc"]
    exam_domain = 3
    exam_tips = ["a tip"]
    has_fault_injection = False
    has_setup = True
    disk_slots = 0


class _FakeResult:
    passed = True
    score = 10
    max_score = 10
    checks = []


class _FakeValidator:
    def __init__(self, calls):
        self._calls = calls

    def validate_task(self, task):
        self._calls.append(("validate", task.id))
        return _FakeResult()


class _FakeDB:
    def save_practice_attempt(self, **kw):
        pass


@pytest.fixture
def calls(monkeypatch):
    seq = []

    monkeypatch.setattr(task_env, "session_reset", lambda *a, **k: seq.append(("session_reset",)))
    monkeypatch.setattr(task_env, "setup_task",
                        lambda task, *a, **k: (seq.append(("setup_task", task.id)) or {"setup": True}))
    monkeypatch.setattr(task_env, "teardown_task",
                        lambda task, st, *a, **k: seq.append(("teardown_task", task.id)))
    monkeypatch.setattr(task_env, "reset_after_task",
                        lambda task, *a, **k: seq.append(("reset_after_task", task.id)))

    monkeypatch.setattr(TaskRegistry, "initialize", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(TaskRegistry, "get_exam_tasks", staticmethod(lambda n: [_FakeTask()]))
    monkeypatch.setattr(TaskRegistry, "get_practice_tasks",
                        staticmethod(lambda *a, **k: [_FakeTask()]))
    monkeypatch.setattr(V, "get_validator", lambda *a, **k: _FakeValidator(seq))
    monkeypatch.setattr(RDB, "get_results_db", lambda *a, **k: _FakeDB())
    monkeypatch.setattr(fmt, "clear_screen", lambda *a, **k: None)
    monkeypatch.setattr(H, "confirm_action", lambda *a, **k: True)
    monkeypatch.setattr(builtins, "input", lambda *a, **k: "")
    return seq


def _names(seq):
    return [c[0] for c in seq]


def test_quick_practice_runs_full_env_lifecycle(calls):
    R.run_quick_practice("all")
    names = _names(calls)

    assert names[0] == "session_reset", "clean env must be prepared up front"
    assert "setup_task" in names, "the machine must be mutated per task"
    assert names.index("setup_task") < names.index("validate"), "setup before the candidate validates"
    assert names.index("validate") < names.index("teardown_task"), "restore after validation"
    assert "reset_after_task" in names


def test_teardown_runs_even_when_validation_raises(calls, monkeypatch):
    # A failure mid-task must not leave injected faults / preconditions behind.
    class _Boom:
        def validate_task(self, task):
            raise RuntimeError("boom")
    monkeypatch.setattr(V, "get_validator", lambda *a, **k: _Boom())

    with pytest.raises(RuntimeError):
        R.run_quick_practice("all")

    names = _names(calls)
    assert "setup_task" in names and "teardown_task" in names, "teardown must run on error"
