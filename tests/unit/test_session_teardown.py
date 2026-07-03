"""
Session teardown on every exit path.

The machine must be returned to a clean state whenever a session ends — finished,
quit, or Ctrl-C — not just on a fully-graded exam. Covers core.task_env
.session_teardown (training modes) and ExamSession.teardown (exam mode).
"""

import pytest

from core import task_env
from core import exam as exam_mod


pytestmark = pytest.mark.unit


class _Task:
    def __init__(self, tid, fault=False, setup=False, sink=None):
        self.id = tid
        self.has_fault_injection = fault
        self.has_setup = setup
        self._sink = sink

    def restore_fault(self):
        self._sink.append(("restore_fault", self.id))
        return True, "restored"

    def teardown_environment(self):
        self._sink.append(("teardown_env", self.id))
        return True, "torn down"


class TestSessionTeardown:
    def test_reverses_setup_then_cleans_box(self, monkeypatch):
        sink = []
        monkeypatch.setattr(task_env, "session_reset",
                            lambda *a, **k: sink.append(("session_reset",)))
        tasks = [
            _Task("fault_1", fault=True, sink=sink),
            _Task("setup_1", setup=True, sink=sink),
            _Task("plain_1", sink=sink),  # nothing to reverse
        ]
        task_env.session_teardown(tasks, verbose=False)

        assert ("restore_fault", "fault_1") in sink
        assert ("teardown_env", "setup_1") in sink
        # Artifact cleanup / disk reset happens after per-task reversal.
        assert sink[-1] == ("session_reset",)
        # A plain task triggers neither restore nor teardown.
        assert not any(t[0] in ("restore_fault", "teardown_env") and t[1] == "plain_1"
                       for t in sink)

    def test_empty_and_none_are_safe(self, monkeypatch):
        sink = []
        monkeypatch.setattr(task_env, "session_reset",
                            lambda *a, **k: sink.append(("session_reset",)))
        task_env.session_teardown([], verbose=False)
        task_env.session_teardown(None, verbose=False)
        # Still cleans the box even with no tasks.
        assert sink == [("session_reset",), ("session_reset",)]

    def test_task_restore_errors_do_not_stop_cleanup(self, monkeypatch):
        sink = []
        monkeypatch.setattr(task_env, "session_reset",
                            lambda *a, **k: sink.append(("session_reset",)))

        class _Boom(_Task):
            def restore_fault(self):
                raise RuntimeError("restore blew up")

        task_env.session_teardown([_Boom("boom", fault=True, sink=sink)], verbose=False)
        # The box is still cleaned despite the per-task error.
        assert ("session_reset",) in sink


class TestExamTeardown:
    def test_idempotent(self, monkeypatch):
        calls = []
        monkeypatch.setattr(exam_mod.ExamSession, "_restore_exam_faults",
                            lambda self: calls.append("restore"))
        monkeypatch.setattr(task_env, "session_reset",
                            lambda *a, **k: calls.append("reset"))

        s = exam_mod.ExamSession(task_count=1)
        s.teardown()
        s.teardown()  # second call must be a no-op
        assert calls == ["restore", "reset"]

    def test_run_exam_mode_tears_down_on_early_quit(self, monkeypatch):
        # If the candidate Ctrl-C's the "Press Enter" prompt before validating,
        # the outer finally must still restore + clean.
        torn = []
        monkeypatch.setattr(exam_mod, "_select_exam_task_count", lambda: 1)
        monkeypatch.setattr(exam_mod, "_select_reboot_simulation", lambda: False)
        monkeypatch.setattr(exam_mod.ExamSession, "start",
                            lambda self: setattr(self, "tasks", [object()]))
        monkeypatch.setattr(exam_mod.ExamSession, "teardown",
                            lambda self: torn.append(True))

        def _interrupt(*a, **k):
            raise KeyboardInterrupt()
        monkeypatch.setattr("builtins.input", _interrupt)

        with pytest.raises(KeyboardInterrupt):
            exam_mod.run_exam_mode()
        assert torn == [True], "teardown must run even when the exam is aborted"
