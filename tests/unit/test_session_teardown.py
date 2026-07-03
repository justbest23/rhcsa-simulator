"""
Session teardown / environment-persistence contract.

- Training sessions (quick/practice/adaptive) revert everything ONCE at session
  end via core.task_env.session_teardown.
- Exam mode deliberately performs NO automatic teardown — the environment stays
  in place after grading (and on early quit) so the candidate can review scores
  and file disputes against live state.
- The next session start (task_env.session_reset) restores anything a previous
  session left behind.
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


class TestSessionResetRestoresPreviousSession:
    def test_session_reset_replays_leftover_fault_records(self, monkeypatch):
        # Exams leave their environment in place; the NEXT session start must
        # restore those faults before cleaning.
        calls = []
        import tasks.troubleshooting as ts
        monkeypatch.setattr(ts, "restore_any_active_fault",
                            lambda: (calls.append("restore_faults") or (True, "ok")))
        from utils import helpers
        monkeypatch.setattr(helpers, "reset_practice_loops",
                            lambda *a, **k: calls.append("loops"))
        from core import lab_cleanup
        monkeypatch.setattr(lab_cleanup, "clean", lambda **k: calls.append("lab") or [])

        task_env.session_reset(verbose=False)
        assert calls[0] == "restore_faults", "restore previous session's faults FIRST"
        assert "loops" in calls and "lab" in calls


class TestExamKeepsEnvironment:
    def test_exam_has_no_auto_teardown(self):
        # The old auto-teardown API must be gone — cleanup is only via
        # session_reset (next session) or the menu's Reset Machine.
        assert not hasattr(exam_mod.ExamSession, "teardown")
        assert not hasattr(exam_mod.ExamSession, "_restore_exam_faults")

    def test_run_exam_mode_does_not_clean_on_early_quit(self, monkeypatch):
        # Ctrl-C at the "Press Enter" prompt must leave the environment as-is
        # (kept for review/disputes) — nothing may revert or reset here.
        touched = []
        monkeypatch.setattr(exam_mod, "_select_exam_task_count", lambda: 1)
        monkeypatch.setattr(exam_mod, "_select_reboot_simulation", lambda: False)
        monkeypatch.setattr(exam_mod.ExamSession, "start",
                            lambda self: setattr(self, "tasks", [object()]))
        monkeypatch.setattr(task_env, "session_reset",
                            lambda *a, **k: touched.append("session_reset"))
        monkeypatch.setattr(task_env, "session_teardown",
                            lambda *a, **k: touched.append("session_teardown"))

        def _interrupt(*a, **k):
            raise KeyboardInterrupt()
        monkeypatch.setattr("builtins.input", _interrupt)

        with pytest.raises(KeyboardInterrupt):
            exam_mod.run_exam_mode()
        assert touched == [], "exam exit must not clean the environment"
