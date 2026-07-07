"""
Remote tasks — performed ON the linked second lab machine, like the real
exam's second node.

The candidate SSHes (or consoles) into the lab machine themselves and does
the work there; the simulator injects/validates over its own key-based SSH
link (core/lab_machine.py). These tasks are only offered when a lab machine
is linked, and each records a remote restore script so session teardown /
Reset Machine can put the lab machine back (best-effort if it is down).

They register into their natural categories (networking, users_groups,
time_services), so exams mix local and remote work exactly like the real
two-node exam.
"""

import random

from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult


def _lab_host():
    from core import lab_machine
    return lab_machine.get_host()


def _read_values(script):
    from core import lab_machine
    return lab_machine.read_values(script)


def _save_restore(task_id, script, label):
    from tasks.troubleshooting import save_fault_state
    save_fault_state(task_id, {'remote_restore_script': script, 'label': label})


def _replay_restore(task_id):
    from tasks.troubleshooting import load_fault_state, clear_fault_state
    from core import lab_machine
    state = load_fault_state(task_id)
    info = state.get('restore_info', {}) if state else {}
    script = info.get('remote_restore_script')
    if script:
        lab_machine.run(script, timeout=60)
    clear_fault_state(task_id)
    return True, "restored remote state"


def _unreachable_result(task, reason=''):
    check = ValidationCheck(
        'lab_machine_reachable', False, 0,
        f"Cannot reach the lab machine over SSH — finish the task and make "
        f"sure the machine is up. {reason}".strip(), max_points=task.points)
    return ValidationResult(task.id, False, 0, task.points, [check])


@TaskRegistry.register("networking")
class RemoteHostnameTask(BaseTask):
    """Set the static hostname on the lab machine."""

    has_fault_injection = True
    requires_lab_machine = True

    def __init__(self):
        super().__init__(
            id="remote_hostname_001",
            category="networking",
            difficulty="exam",
            points=8
        )
        self.tags = ['remote', 'hostname']
        self.exam_tips = [
            "hostnamectl set-hostname <name> sets the static hostname persistently",
            "Verify with: hostnamectl status (or hostnamectl --static)",
            "Real exams run across two nodes — read WHERE each task applies",
        ]
        self.requires_persistence = True
        self.hostname = None

    def generate(self, **params):
        host = _lab_host() or '<lab machine>'
        self.hostname = params.get(
            'hostname', f'node{random.randint(2, 9)}.lab.example.com')
        self.description = (
            f"On the lab machine ({host}): set the static hostname to "
            f"'{self.hostname}'. The change must persist across reboots."
        )
        self.hints = [
            f"SSH to the lab machine first: ssh root@{host}",
            "hostnamectl set-hostname sets the static hostname",
            "Verify with: hostnamectl --static",
        ]
        return self

    def inject_fault(self):
        ok, values, out = _read_values(
            'echo "STATIC=$(hostnamectl --static 2>/dev/null)"')
        if not ok:
            return False, f"lab machine unreachable — skipping ({out[-200:]})"
        orig = values.get('STATIC', '') or 'localhost.localdomain'
        _save_restore(self.id, f"hostnamectl set-hostname '{orig}'",
                      f"hostname ({orig})")
        return True, "recorded original hostname"

    def restore_fault(self):
        return _replay_restore(self.id)

    def validate(self):
        ok, values, out = _read_values(
            'echo "STATIC=$(hostnamectl --static 2>/dev/null)"')
        if not ok:
            return _unreachable_result(self)
        checks = []
        total = 0
        actual = values.get('STATIC', '')
        if actual == self.hostname:
            checks.append(ValidationCheck('hostname_set', True, 8,
                          f"Static hostname is '{self.hostname}'"))
            total += 8
        else:
            checks.append(ValidationCheck('hostname_set', False, 0,
                          f"Static hostname is '{actual or 'unset'}' "
                          f"(expected '{self.hostname}')", max_points=8))
        return ValidationResult(self.id, total >= self.points * 0.8,
                                total, self.points, checks)


@TaskRegistry.register("users_groups")
class RemoteUserTask(BaseTask):
    """Create a user with a specific UID and supplementary group on the lab
    machine, with a password set."""

    has_fault_injection = True
    requires_lab_machine = True

    def __init__(self):
        super().__init__(
            id="remote_user_001",
            category="users_groups",
            difficulty="exam",
            points=10
        )
        self.tags = ['remote', 'users']
        self.exam_tips = [
            "useradd -u <uid> -G <group> creates a user with a UID and a "
            "supplementary group in one step",
            "Set the password with passwd <user> (or echo 'u:p' | chpasswd)",
            "Verify with: id <user>",
        ]
        self.requires_persistence = True
        self.username = None
        self.uid = None
        self.group = None

    def generate(self, **params):
        host = _lab_host() or '<lab machine>'
        self.username = params.get('username', f'rmuser{random.randint(10, 99)}')
        self.uid = params.get('uid', random.randint(3000, 3999))
        self.group = params.get('group', 'wheel')
        self.description = (
            f"On the lab machine ({host}): create user '{self.username}' with "
            f"UID {self.uid} and supplementary group '{self.group}', and set "
            f"any password for the account."
        )
        self.hints = [
            f"SSH to the lab machine first: ssh root@{host}",
            "useradd -u sets the UID, -G adds a supplementary group",
            f"Verify with: id {self.username}",
        ]
        return self

    def inject_fault(self):
        ok, _, out = _read_values('echo "UP=yes"')
        if not ok:
            return False, f"lab machine unreachable — skipping ({out[-200:]})"
        _save_restore(self.id,
                      f"userdel -r '{self.username}' 2>/dev/null; true",
                      f"practice user ({self.username})")
        return True, "recorded cleanup for the practice user"

    def restore_fault(self):
        return _replay_restore(self.id)

    def validate(self):
        u = self.username
        script = (
            f'echo "UID=$(id -u {u} 2>/dev/null)"\n'
            f'echo "GROUPS=$(id -nG {u} 2>/dev/null)"\n'
            f'echo "HASH=$(awk -F: \'$1=="{u}"{{print $2}}\' /etc/shadow)"\n'
        )
        ok, values, out = _read_values(script)
        if not ok:
            return _unreachable_result(self)
        checks = []
        total = 0

        if values.get('UID') == str(self.uid):
            checks.append(ValidationCheck('uid', True, 4,
                          f"User exists with UID {self.uid}"))
            total += 4
        elif values.get('UID'):
            checks.append(ValidationCheck('uid', False, 0,
                          f"User exists but UID is {values['UID']} "
                          f"(expected {self.uid})", max_points=4))
        else:
            checks.append(ValidationCheck('uid', False, 0,
                          f"User '{u}' does not exist", max_points=4))

        if self.group in values.get('GROUPS', '').split():
            checks.append(ValidationCheck('group', True, 3,
                          f"'{self.group}' is a supplementary group"))
            total += 3
        else:
            checks.append(ValidationCheck('group', False, 0,
                          f"User is not in group '{self.group}'", max_points=3))

        pw_hash = values.get('HASH', '')
        if pw_hash.startswith('$'):
            checks.append(ValidationCheck('password', True, 3, "Password is set"))
            total += 3
        else:
            checks.append(ValidationCheck('password', False, 0,
                          "No password set for the account", max_points=3))

        return ValidationResult(self.id, total >= self.points * 0.7,
                                total, self.points, checks)


@TaskRegistry.register("time_services")
class RemoteTimezoneTask(BaseTask):
    """Set the system timezone on the lab machine."""

    has_fault_injection = True
    requires_lab_machine = True

    # Rarely a default anywhere, so the candidate always has real work to do.
    _ZONES = ['America/Phoenix', 'Australia/Adelaide', 'Europe/Vienna',
              'Asia/Kolkata']

    def __init__(self):
        super().__init__(
            id="remote_timezone_001",
            category="time_services",
            difficulty="exam",
            points=8
        )
        self.tags = ['remote', 'timezone']
        self.exam_tips = [
            "timedatectl set-timezone <zone> sets the timezone persistently",
            "List zones with: timedatectl list-timezones | grep <region>",
            "Verify with: timedatectl (check the 'Time zone' line)",
        ]
        self.requires_persistence = True
        self.timezone = None

    def generate(self, **params):
        host = _lab_host() or '<lab machine>'
        self.timezone = params.get('timezone', random.choice(self._ZONES))
        self.description = (
            f"On the lab machine ({host}): set the system timezone to "
            f"'{self.timezone}'."
        )
        self.hints = [
            f"SSH to the lab machine first: ssh root@{host}",
            "timedatectl set-timezone changes the timezone",
            "Find the exact zone name: timedatectl list-timezones",
        ]
        return self

    def inject_fault(self):
        ok, values, out = _read_values(
            'echo "TZ=$(timedatectl show -p Timezone --value 2>/dev/null)"')
        if not ok:
            return False, f"lab machine unreachable — skipping ({out[-200:]})"
        orig = values.get('TZ', '') or 'UTC'
        _save_restore(self.id, f"timedatectl set-timezone '{orig}'",
                      f"timezone ({orig})")
        return True, "recorded original timezone"

    def restore_fault(self):
        return _replay_restore(self.id)

    def validate(self):
        ok, values, out = _read_values(
            'echo "TZ=$(timedatectl show -p Timezone --value 2>/dev/null)"')
        if not ok:
            return _unreachable_result(self)
        checks = []
        total = 0
        actual = values.get('TZ', '')
        if actual == self.timezone:
            checks.append(ValidationCheck('timezone', True, 8,
                          f"Timezone is {self.timezone}"))
            total += 8
        else:
            checks.append(ValidationCheck('timezone', False, 0,
                          f"Timezone is '{actual or 'unknown'}' "
                          f"(expected '{self.timezone}')", max_points=8))
        return ValidationResult(self.id, total >= self.points * 0.8,
                                total, self.points, checks)
