"""
Environment setup helpers for positive-configuration tasks.

Fault-injection (troubleshooting) tasks break the system so the candidate has
something to fix. Positive-configuration tasks ("enable crond", "install X",
"generate an SSH key") had no equivalent: if the system already satisfied the
goal — a default-on service, a leftover artifact from a previous session — the
task validated as PASS without the candidate doing any work.

These helpers let a positive task establish the *negative precondition* at exam
start (stop/disable a default-on service, move an existing key aside, …) so the
work is actually required, and restore the original state afterwards.

State is recorded in the same active-fault file the troubleshooting tasks use,
so an interrupted session is cleaned up by System Reset / startup recovery.
Each restore record carries a ``restore_type`` that ``_dispatch_restore`` knows
how to undo generically.
"""

import os
import shutil
import subprocess


# Never stop/disable these — doing so could lock the candidate out of the box.
CRITICAL_SERVICES = {'sshd', 'sshd.service', 'NetworkManager', 'NetworkManager.service'}


def _run(cmd, timeout=120):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # pragma: no cover - defensive
        class _R:
            returncode = 1
            stdout = ''
            stderr = str(e)
        return _R()


def _save(task_id, info):
    from tasks.troubleshooting import save_fault_state
    save_fault_state(task_id, info)


def restore_and_clear(task_id):
    """Generic teardown: replay the saved restore record for this task, then
    drop it. Used as the default BaseTask.teardown_environment()."""
    from tasks.troubleshooting import load_fault_state, clear_fault_state, _dispatch_restore
    st = load_fault_state(task_id)
    if not st:
        return True, ""
    msgs = []
    _dispatch_restore(task_id, st['restore_info'], msgs)
    clear_fault_state(task_id)
    return True, '; '.join(msgs)


# ── service / timer preconditions ─────────────────────────────────────────────

def _unit_state(unit):
    active = _run(['systemctl', 'is-active', unit]).stdout.strip() == 'active'
    enabled = _run(['systemctl', 'is-enabled', unit]).stdout.strip() == 'enabled'
    return active, enabled


def make_service_absent(task_id, service):
    """Stop and disable a service so an 'enable/start it' task requires work."""
    if service in CRITICAL_SERVICES:
        return False, f"skipped critical service {service}"
    if _run(['systemctl', 'cat', service]).returncode != 0:
        return False, f"{service} not installed (nothing to do)"
    active, enabled = _unit_state(service)
    if not active and not enabled:
        return False, f"{service} already stopped+disabled"
    _save(task_id, {'restore_type': 'unit', 'unit': service,
                    'was_active': active, 'was_enabled': enabled})
    _run(['systemctl', 'disable', service])
    _run(['systemctl', 'stop', service])
    return True, f"stopped+disabled {service} (was active={active}, enabled={enabled})"


def make_service_present(task_id, service):
    """Start and enable a service so a 'stop/disable it' task requires work."""
    if service in CRITICAL_SERVICES:
        return False, f"skipped critical service {service}"
    if _run(['systemctl', 'cat', service]).returncode != 0:
        return False, f"{service} not installed (nothing to do)"
    active, enabled = _unit_state(service)
    if active and enabled:
        return False, f"{service} already running+enabled"
    _save(task_id, {'restore_type': 'unit', 'unit': service,
                    'was_active': active, 'was_enabled': enabled})
    _run(['systemctl', 'enable', service])
    _run(['systemctl', 'start', service])
    return True, f"started+enabled {service} (was active={active}, enabled={enabled})"


def make_timer_absent(task_id, timer):
    """Stop and disable a timer so an 'enable it' task requires work."""
    unit = timer if timer.endswith('.timer') else f'{timer}.timer'
    if _run(['systemctl', 'cat', unit]).returncode != 0:
        return False, f"{unit} not present (nothing to do)"
    active, enabled = _unit_state(unit)
    if not active and not enabled:
        return False, f"{unit} already stopped+disabled"
    _save(task_id, {'restore_type': 'unit', 'unit': unit,
                    'was_active': active, 'was_enabled': enabled})
    _run(['systemctl', 'disable', unit])
    _run(['systemctl', 'stop', unit])
    return True, f"stopped+disabled {unit} (was active={active}, enabled={enabled})"


# ── filesystem preconditions ──────────────────────────────────────────────────

def backup_paths(task_id, paths):
    """Move existing files aside (restored on teardown) so a 'create X' task
    can't pass on a leftover from a previous session."""
    moved = []
    for p in paths:
        if os.path.lexists(p):
            bak = p + '.rhcsa-bak'
            try:
                if os.path.lexists(bak):
                    os.remove(bak)
                shutil.move(p, bak)
                moved.append(p)
            except OSError:
                pass
    if not moved:
        return False, "nothing to move aside"
    _save(task_id, {'restore_type': 'file_backup', 'paths': moved})
    return True, f"moved aside {moved}"


def remove_paths(task_id, paths):
    """Delete leftover artifacts (no restore needed — e.g. a /tmp output file)."""
    removed = []
    for p in paths:
        try:
            os.remove(p)
            removed.append(p)
        except (FileNotFoundError, IsADirectoryError, OSError):
            pass
    return True, (f"removed {removed}" if removed else "nothing to remove")


# ── package / flatpak preconditions (best-effort; may need network) ───────────

def ensure_package_installed(task_id, pkg):
    """Install a package so a 'remove it' task requires work. Best-effort."""
    if _run(['rpm', '-q', pkg], timeout=20).returncode == 0:
        return False, f"{pkg} already installed"
    r = _run(['dnf', '-y', 'install', pkg], timeout=180)
    if r.returncode != 0:
        return False, f"could not install {pkg} (no repo access?)"
    _save(task_id, {'restore_type': 'pkg_remove', 'pkg': pkg})
    return True, f"installed {pkg}"


def ensure_package_absent(task_id, pkg):
    """Remove a package so an 'install it' task requires work."""
    if _run(['rpm', '-q', pkg], timeout=20).returncode != 0:
        return False, f"{pkg} already absent"
    r = _run(['dnf', '-y', 'remove', pkg], timeout=180)
    if r.returncode != 0:
        return False, f"could not remove {pkg}"
    _save(task_id, {'restore_type': 'pkg_install', 'pkg': pkg})
    return True, f"removed {pkg}"


def ensure_flatpak_app_absent(task_id, app_id):
    """Uninstall a Flatpak app so an 'install it' task requires work."""
    if _run(['flatpak', 'info', app_id], timeout=20).returncode != 0:
        return False, f"{app_id} already absent"
    r = _run(['flatpak', 'uninstall', '-y', app_id], timeout=120)
    if r.returncode != 0:
        return False, f"could not uninstall {app_id}"
    _save(task_id, {'restore_type': 'flatpak_install', 'app_id': app_id})
    return True, f"uninstalled flatpak {app_id}"
