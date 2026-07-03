"""
Shared task-environment lifecycle for training sessions (practice + adaptive).

Exam mode already resets the box and prepares each task's preconditions
(reset practice disks + clean lab leftovers at start; inject_fault /
setup_environment per task; restore_fault / teardown_environment after). These
helpers expose that exact behavior so practice and adaptive modes get the same
real system changes and per-iteration reset — otherwise positive-config tasks
pass on default state and leftover artifacts from the previous task pollute the
next one.

Nothing new is invented here; it just calls the same functions exam.py uses.
"""

import logging
from utils import formatters as fmt

logger = logging.getLogger(__name__)


def session_reset(verbose=True):
    """Start-of-session reset: fresh practice disks + remove leftover artifacts.

    Mirrors ExamSession.start(): helpers.reset_practice_loops() followed by
    lab_cleanup.clean(). Safe to call when there are no loop devices or no
    leftovers — both operations no-op cleanly.
    """
    from utils import helpers
    try:
        helpers.reset_practice_loops()
    except Exception:
        pass
    done = []
    try:
        from core import lab_cleanup
        done = lab_cleanup.clean(dry_run=False)
    except Exception:
        done = []
    if verbose and done:
        print(fmt.dim(f"Cleaned {len(done)} leftover lab artifact(s) from a previous session."))
    return done


def setup_task(task, verbose=True):
    """Change the system for one task before the candidate works on it.

    Runs the task's own inject_fault() (break something to fix) and/or
    setup_environment() (establish a negative precondition so a positive-config
    task can't pass on default state) — the same calls exam.py makes. Returns a
    small state dict for teardown_task() to reverse.
    """
    state = {'fault': False, 'setup': False}

    if getattr(task, 'has_fault_injection', False):
        try:
            ok, msg = task.inject_fault()
            state['fault'] = ok
            if verbose:
                print(fmt.success(f"  Fault active: {msg}") if ok
                      else fmt.warning(f"  Fault injection failed: {msg} (descriptive mode only)"))
        except Exception as e:
            if verbose:
                print(fmt.warning(f"  Fault injection error: {e}"))

    if getattr(task, 'has_setup', False):
        try:
            ok, msg = task.setup_environment()
            state['setup'] = ok
            # A False result just means no precondition was needed; stay quiet.
            if verbose and ok:
                print(fmt.dim(f"  Precondition set: {msg}"))
        except Exception as e:
            if verbose:
                print(fmt.warning(f"  Setup error: {e}"))

    return state


def teardown_task(task, state, verbose=True):
    """Reverse setup_task(): restore_fault() + teardown_environment()."""
    if not state:
        return
    if state.get('fault'):
        try:
            ok, msg = task.restore_fault()
            if verbose:
                print(fmt.dim(f"  {msg}") if ok else fmt.error(f"  Restore error: {msg}"))
        except Exception:
            pass
    if state.get('setup'):
        try:
            task.teardown_environment()
        except Exception:
            pass


def reset_after_task(task):
    """Between iterations, wipe practice disks if the finished task consumed one,
    so the next disk task starts from clean, signature-free disks.

    Non-disk tasks skip this (nothing to reset), keeping the session snappy.
    """
    if getattr(task, 'disk_slots', 0) <= 0:
        return
    from utils import helpers
    try:
        helpers.reset_practice_loops()
    except Exception:
        pass


def session_teardown(tasks, verbose=True):
    """End-of-session cleanup — call this on EVERY exit path (finished, quit, or
    Ctrl-C) so returning to the menu leaves a clean box.

    It (1) reverses every task's injected fault / negative precondition, then
    (2) removes leftover lab artifacts and resets practice disks (same as the
    start-of-session reset). Both steps are idempotent and swallow errors: the
    per-task restore records are cleared as they replay, so calling this twice —
    e.g. once at normal end and again from an outer finally — is a harmless
    no-op. Safe to call even if setup never ran (empty/None tasks is fine).
    """
    if verbose:
        print(fmt.dim("Restoring the machine to a clean state..."))
    for task in tasks or []:
        if getattr(task, 'has_fault_injection', False):
            try:
                task.restore_fault()
            except Exception:
                pass
        if getattr(task, 'has_setup', False):
            try:
                task.teardown_environment()
            except Exception:
                pass
    # Remove candidate-created artifacts (files, mounts, swap, units, …) and
    # reset practice disks so the box is back to a clean, vanilla state.
    session_reset(verbose=False)
