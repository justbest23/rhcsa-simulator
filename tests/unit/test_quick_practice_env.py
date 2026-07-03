"""
Quick-practice environment lifecycle.

Quick practice must mutate the machine like exam/practice/adaptive modes do,
with the session-level teardown model: system changes are reverted ONCE at the
end of the session (finish, quit, or error) — never between tasks:

    prepare_session  ->  setup_task  ->  (validate)  ->  ...  ->  session_teardown
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

    monkeypatch.setattr(task_env, "prepare_session",
                        lambda tasks, *a, **k: seq.append(("prepare_session",)))
    monkeypatch.setattr(task_env, "setup_task",
                        lambda task, *a, **k: (seq.append(("setup_task", task.id)) or {"setup": True}))
    monkeypatch.setattr(task_env, "session_teardown",
                        lambda tasks, *a, **k: seq.append(("session_teardown",)))
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
    monkeypatch.setattr(H, "select_task_count", lambda *a, **k: 4)
    monkeypatch.setattr(builtins, "input", lambda *a, **k: "")
    return seq


def _names(seq):
    return [c[0] for c in seq]


def test_quick_practice_runs_session_lifecycle(calls):
    R.run_quick_practice("all")
    names = _names(calls)

    assert names[0] == "prepare_session", "clean env + package offer up front"
    assert "setup_task" in names, "the machine must be mutated per task"
    assert names.index("setup_task") < names.index("validate"), "setup before the candidate validates"
    assert names[-1] == "session_teardown", "revert happens once, at session end"


def test_no_per_task_teardown(calls):
    # System changes must persist across the session; only the end-of-session
    # teardown reverts them (per-task revert was removed by design).
    R.run_quick_practice("all")
    assert _names(calls).count("session_teardown") == 1
    assert "teardown_task" not in _names(calls)
    # Non-disk task: no disk re-provisioning either.
    assert "reset_after_task" not in _names(calls)


def test_disk_tasks_reprovision_between_tasks(calls, monkeypatch):
    class _DiskTask(_FakeTask):
        id = "disk_task_001"
        disk_slots = 1

    monkeypatch.setattr(TaskRegistry, "get_exam_tasks",
                        staticmethod(lambda n: [_DiskTask(), _FakeTask()]))
    R.run_quick_practice("all")
    names = _names(calls)
    # Disk wiped after the disk task (another task follows), before session end.
    assert "reset_after_task" in names
    assert names.index("reset_after_task") < names.index("session_teardown")


def test_session_teardown_runs_even_when_validation_raises(calls, monkeypatch):
    # A failure mid-session must not leave injected faults / preconditions behind.
    class _Boom:
        def validate_task(self, task):
            raise RuntimeError("boom")
    monkeypatch.setattr(V, "get_validator", lambda *a, **k: _Boom())

    with pytest.raises(RuntimeError):
        R.run_quick_practice("all")

    names = _names(calls)
    assert "setup_task" in names and "session_teardown" in names, "teardown must run on error"
