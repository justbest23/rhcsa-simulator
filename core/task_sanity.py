"""
Post-setup sanity check — "is this task actually a task?"

After a task's environment is prepared (fault injected, negative precondition
established, lab leftovers cleaned) but BEFORE the candidate has done anything,
the task must **not** already be passing. If `validate()` passes at t=0 then one
of these is true and the candidate would get a free pass:

  * the setup silently no-op'd — e.g. an httpd SELinux fault where httpd isn't
    installed, so `chcon`/`systemctl` did nothing and there's no symptom to fix;
  * a positive-config task is satisfied by default/pre-existing state and has no
    setup to make it real work;
  * a leftover artifact from a previous session wasn't cleaned.

This check is deliberately generic — it drives each task's OWN read-only
`validate()` (via the exception-safe ValidationEngine) and just asserts the task
is not already green. That makes it work for every task type without knowing
anything task-specific, and it runs in EVERY mode: exam calls check_tasks() after
its setup phase, and quick/practice/adaptive get it for free because they all
prepare tasks through core.task_env.setup_task(), which calls check_task() here.

It is advisory: it logs (and optionally prints) a warning so a broken scenario is
visible, but never aborts the session — a task whose fault didn't take is still
presented, just descriptively.
"""

import logging

from utils import formatters as fmt

logger = logging.getLogger(__name__)


def _already_satisfied(task, validator):
    """True if the task validates as passed right now, False if not, None if the
    check couldn't run (validate errored / returned nothing)."""
    try:
        result = validator.validate_task(task)
    except Exception as e:  # validate_task is exception-safe, but be defensive
        logger.debug("sanity: validate raised for %s: %s", getattr(task, 'id', '?'), e)
        return None
    if result is None or getattr(result, 'error_message', None):
        # A validation error means we can't trust the verdict — don't flag.
        return None
    return bool(getattr(result, 'passed', False))


def check_task(task, validator=None):
    """Return a warning string if `task` is already satisfied before any work is
    done (suspicious), else None.

    Pass a validator to reuse one across many tasks; otherwise the shared engine
    is used.
    """
    if validator is None:
        from core.validator import get_validator
        validator = get_validator()

    satisfied = _already_satisfied(task, validator)
    if not satisfied:
        return None

    tid = getattr(task, 'id', '?')
    category = getattr(task, 'category', '?')
    has_prep = getattr(task, 'has_fault_injection', False) or getattr(task, 'has_setup', False)
    if has_prep:
        reason = ("its fault/precondition setup did not change the machine "
                  "(silent no-op — is the required package/service present?)")
    else:
        reason = ("it passes on default/pre-existing state and has no setup to "
                  "require real work")
    return f"{tid} ({category}): already satisfied before you start — {reason}"


def check_tasks(tasks, verbose_console=True):
    """Run the post-setup sanity check over `tasks`. Logs every suspicious task
    and returns the list of warning strings.

    verbose_console=True prints each warning (training modes, where revealing a
    gimme task is harmless). Exam mode passes verbose_console=False so it can show
    only a non-spoiling aggregate instead of naming which tasks need no work.
    """
    from core.validator import get_validator
    validator = get_validator()

    warnings = []
    for task in tasks:
        try:
            w = check_task(task, validator)
        except Exception as e:
            logger.debug("sanity: check_task failed for %s: %s",
                         getattr(task, 'id', '?'), e)
            continue
        if w:
            warnings.append(w)
            logger.warning("SANITY: %s", w)
            if verbose_console:
                print(fmt.warning(f"  ⚠ {w}"))
    return warnings
