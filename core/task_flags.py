"""
Bad-task flagging ("marked for potential removal").

Some generated tasks just aren't good exam practice (the chroot practice
task being the canonical example). Flagging one hides it from every
selection path — quick practice, practice, adaptive, and exams — without
deleting its code or history. Flags live in a small JSON file so they
survive updates and can be reviewed/unflagged from Setup → Task Statistics.
"""

import json
import os
import time

from config import settings

FLAGS_PATH = os.path.join(str(settings.DATA_DIR), 'flagged_tasks.json')

# Tasks flagged out of the box. The chroot practice task is a poor simulation
# of real rd.break work (a full boot-rescue lab now covers that instead).
_SEED = {
    'boot_recovery_chroot_practice_001':
        'weak simulation of rd.break recovery; superseded by the Boot Rescue Lab',
}


def _load():
    """Return {task_id: {'reason': ..., 'flagged_at': ...}}, seeding the file
    on first use."""
    try:
        with open(FLAGS_PATH) as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        seeded = {tid: {'reason': reason,
                        'flagged_at': time.strftime('%Y-%m-%d')}
                  for tid, reason in _SEED.items()}
        _save(seeded)
        return seeded
    except Exception:
        pass
    return {}


def _save(data):
    os.makedirs(os.path.dirname(FLAGS_PATH), exist_ok=True)
    with open(FLAGS_PATH, 'w') as fh:
        json.dump(data, fh, indent=2)


def flagged_ids():
    """Set of task ids that must not be offered."""
    return set(_load())


def is_flagged(task_id):
    return task_id in _load()


def flag(task_id, reason=''):
    """Mark a task as bad. Idempotent; returns True if newly flagged."""
    data = _load()
    if task_id in data:
        return False
    data[task_id] = {'reason': reason or 'flagged by user',
                     'flagged_at': time.strftime('%Y-%m-%d')}
    _save(data)
    return True


def unflag(task_id):
    """Remove a flag. Returns True if it existed."""
    data = _load()
    if task_id not in data:
        return False
    del data[task_id]
    _save(data)
    return True


def all_flags():
    """The full flag table for review screens."""
    return _load()
