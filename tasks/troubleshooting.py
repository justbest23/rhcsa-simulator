"""
Troubleshooting tasks for RHCSA Simulator.

Each task injects a real fault onto the system, lets the user diagnose
and fix it, then restores the system regardless of outcome.

inject_fault()   — breaks the system (called before showing the task)
restore_fault()  — restores original state (called after validate or skip)

Active faults are recorded in FAULT_STATE_FILE so system_reset() can
always restore even if the simulator crashes mid-task.
"""

import json
import logging
import os
import random
import subprocess

from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe

logger = logging.getLogger(__name__)

FAULT_STATE_FILE = '/var/lib/rhcsa-simulator/active_fault.json'


# ── Fault-state bookkeeping ───────────────────────────────────────────────────

def save_fault_state(task_id: str, restore_info: dict):
    os.makedirs(os.path.dirname(FAULT_STATE_FILE), exist_ok=True)
    with open(FAULT_STATE_FILE, 'w') as f:
        json.dump({'task_id': task_id, 'restore_info': restore_info}, f)


def load_fault_state() -> dict | None:
    try:
        with open(FAULT_STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def clear_fault_state():
    try:
        os.remove(FAULT_STATE_FILE)
    except FileNotFoundError:
        pass


def restore_any_active_fault():
    """Called at startup and during system_reset to restore a stale fault."""
    state = load_fault_state()
    if not state:
        return False, "No active fault"
    task_id = state.get('task_id', '')
    info = state.get('restore_info', {})
    msgs = []

    # Dispatch to the right restorer
    if task_id.startswith('fault_selinux_context'):
        _restore_selinux_context(info, msgs)
    elif task_id.startswith('fault_selinux_boolean'):
        _restore_selinux_boolean(info, msgs)
    elif task_id.startswith('fault_firewall'):
        _restore_firewall(info, msgs)
    elif task_id.startswith('fault_sshd_config'):
        _restore_sshd_config(info, msgs)
    elif task_id.startswith('fault_service'):
        _restore_service(info, msgs)
    elif task_id.startswith('fault_sudoers'):
        _restore_sudoers_full(info, msgs)
    elif task_id.startswith('fault_fstab'):
        _restore_fstab(info, msgs)
    else:
        msgs.append(f"Unknown fault type: {task_id}")

    clear_fault_state()
    return True, '\n'.join(msgs)


# ── Shared restore helpers ────────────────────────────────────────────────────

def _run(cmd, timeout=15):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _restore_selinux_context(info, msgs):
    path = info.get('path')
    if path:
        r = _run(['restorecon', '-Rv', path])
        msgs.append(f"restorecon {path}: {'ok' if r.returncode == 0 else r.stderr.strip()}")


def _restore_selinux_boolean(info, msgs):
    name = info.get('boolean')
    original = info.get('original_value', 'on')
    if name:
        r = _run(['setsebool', '-P', name, original])
        msgs.append(f"setsebool -P {name} {original}: {'ok' if r.returncode == 0 else r.stderr.strip()}")


def _restore_firewall(info, msgs):
    zone = info.get('zone', 'public')
    svc = info.get('service')
    port = info.get('port')
    if svc:
        _run(['firewall-cmd', f'--zone={zone}', f'--add-service={svc}'])
        _run(['firewall-cmd', f'--zone={zone}', f'--add-service={svc}', '--permanent'])
        msgs.append(f"Restored firewall service {svc} in zone {zone}")
    if port:
        _run(['firewall-cmd', f'--zone={zone}', f'--add-port={port}'])
        _run(['firewall-cmd', f'--zone={zone}', f'--add-port={port}', '--permanent'])
        msgs.append(f"Restored firewall port {port} in zone {zone}")


def _restore_sshd_config(info, msgs):
    marker = info.get('marker', '')
    if marker:
        with open('/etc/ssh/sshd_config', 'r') as f:
            lines = f.readlines()
        cleaned = [l for l in lines if marker not in l]
        with open('/etc/ssh/sshd_config', 'w') as f:
            f.writelines(cleaned)
        msgs.append("Removed injected sshd_config line")
    # Restart sshd only if it's not already running
    r = _run(['systemctl', 'is-active', '--quiet', 'sshd'])
    if r.returncode != 0:
        _run(['systemctl', 'start', 'sshd'])
        msgs.append("Restarted sshd")


def _restore_service(info, msgs):
    name = info.get('service')
    was_active = info.get('was_active', True)
    was_enabled = info.get('was_enabled', True)
    if name:
        if was_active:
            _run(['systemctl', 'start', name])
        if was_enabled:
            _run(['systemctl', 'enable', name])
        msgs.append(f"Restored {name} service state")


def _restore_sudoers(info, msgs):
    path = info.get('path')
    original_perms = info.get('original_perms', '0440')
    if path and os.path.exists(path):
        os.chmod(path, int(original_perms, 8))
        msgs.append(f"Restored {path} permissions to {original_perms}")


_SUDOERS_PRACTICE_USER = 'sudopractice'
_SUDOERS_PRACTICE_FILE = '/etc/sudoers.d/sudopractice'


def _restore_sudoers_full(info, msgs):
    """Full crash-recovery restore: remove the practice sudoers file and user."""
    path = info.get('path', _SUDOERS_PRACTICE_FILE)
    user = info.get('user', _SUDOERS_PRACTICE_USER)
    if os.path.exists(path):
        os.remove(path)
        msgs.append(f"Removed {path}")
    r = _run(['id', user])
    if r.returncode == 0:
        _run(['userdel', user])
        msgs.append(f"Removed practice user {user}")


def _restore_fstab(info, msgs):
    marker = info.get('marker', '')
    if marker:
        with open('/etc/fstab', 'r') as f:
            lines = f.readlines()
        cleaned = [l for l in lines if marker not in l]
        with open('/etc/fstab', 'w') as f:
            f.writelines(cleaned)
        msgs.append("Removed injected fstab line")


# ── Base class ────────────────────────────────────────────────────────────────

class TroubleshootingTask(BaseTask):
    """
    Base for tasks that actually inject a fault before the user works on it.
    Subclasses must implement inject_fault() and restore_fault().
    """
    has_fault_injection = True

    def __init__(self, id, category, difficulty, points):
        super().__init__(id=id, category=category, difficulty=difficulty, points=points)

    def inject_fault(self) -> tuple:
        """Break the system. Returns (success: bool, message: str)."""
        return True, "No fault configured"

    def restore_fault(self) -> tuple:
        """Restore original state. Returns (success: bool, message: str)."""
        return True, "Nothing to restore"


# ── SELinux: wrong file context on web root ───────────────────────────────────

@TaskRegistry.register("troubleshooting")
class SELinuxHttpdContextFaultTask(TroubleshootingTask):

    def __init__(self):
        super().__init__(
            id="fault_selinux_context_httpd_001",
            category="troubleshooting",
            difficulty="exam",
            points=14
        )
        self.web_root = '/var/www/html'
        self.exam_domain = 7
        self.tags = ['selinux', 'httpd', 'context', 'restorecon', 'fault-injection']
        self.exam_tips = [
            "restorecon -Rv /path is the fastest fix when contexts are wrong",
            "chcon is temporary — restorecon or semanage fcontext for persistence",
            "ausearch -m AVC -ts recent | audit2why is your first diagnostic command",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Apache Serving 403 Forbidden\n"
            "=" * 50 + "\n\n"
            "Symptom: httpd is running but returns 403 Forbidden for all requests.\n"
            "The web content exists in /var/www/html but cannot be served.\n\n"
            "Tasks:\n"
            "  1. Identify why httpd cannot read /var/www/html\n"
            "  2. Fix the SELinux issue\n"
            "  3. Verify httpd can serve content (curl http://localhost)\n"
            "  4. Ensure the fix survives a relabel (restorecon)"
        )
        self.hints = [
            "Check SELinux denials: ausearch -m AVC -ts recent | audit2why",
            "Inspect the context: ls -lZ /var/www/html",
            "The correct context type is httpd_sys_content_t",
            "Fix: restorecon -Rv /var/www/html",
        ]
        return self

    def inject_fault(self):
        # Create a test file so there's actually content to serve
        os.makedirs(self.web_root, exist_ok=True)
        test_file = f'{self.web_root}/index.html'
        if not os.path.exists(test_file):
            with open(test_file, 'w') as f:
                f.write('<html><body>RHCSA test</body></html>\n')

        # Set wrong SELinux type — etc_t blocks httpd from reading
        r = _run(['chcon', '-R', '-t', 'etc_t', self.web_root])
        if r.returncode != 0:
            return False, f"chcon failed: {r.stderr.strip()}"

        # Also ensure httpd is running so the symptom is visible
        _run(['systemctl', 'start', 'httpd'])

        save_fault_state(self.id, {'path': self.web_root})
        return True, f"Set wrong SELinux context (etc_t) on {self.web_root}"

    def restore_fault(self):
        msgs = []
        _restore_selinux_context({'path': self.web_root}, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: context is correct (6 pts)
        r = execute_safe(['ls', '-Zd', self.web_root])
        if r.success and 'httpd_sys_content_t' in r.stdout:
            checks.append(ValidationCheck("selinux_context", True, 6, message=f"{self.web_root} has correct SELinux type"))
            score += 6
        else:
            ctx = r.stdout.strip() if r.success else 'unknown'
            checks.append(ValidationCheck("selinux_context", False, 0, max_points=6,
                                          message=f"Wrong SELinux context: {ctx}"))

        # Check 2: restorecon would be a no-op (policy matches reality) (4 pts)
        r = execute_safe(['restorecon', '-Rvn', self.web_root])
        if r.success and not r.stdout.strip():
            checks.append(ValidationCheck("context_persistent", True, 4, message="Context matches policy (persistent)"))
            score += 4
        else:
            checks.append(ValidationCheck("context_persistent", False, 0, max_points=4,
                                          message="Context doesn't match policy — won't survive relabel"))

        # Check 3: httpd running (2 pts)
        r = execute_safe(['systemctl', 'is-active', 'httpd'])
        if r.success and 'active' in r.stdout:
            checks.append(ValidationCheck("httpd_running", True, 2, message="httpd is running"))
            score += 2
        else:
            checks.append(ValidationCheck("httpd_running", False, 0, max_points=2, message="httpd is not running"))

        # Check 4: curl returns 200 (2 pts)
        r = execute_safe(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost'])
        if r.success and r.stdout.strip() == '200':
            checks.append(ValidationCheck("httpd_serving", True, 2, message="httpd returning HTTP 200"))
            score += 2
        else:
            checks.append(ValidationCheck("httpd_serving", False, 0, max_points=2,
                                          message=f"httpd not serving correctly (got {r.stdout.strip()})"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── SELinux: boolean off for httpd network connect ────────────────────────────

@TaskRegistry.register("troubleshooting")
class SELinuxHttpdBooleanFaultTask(TroubleshootingTask):

    def __init__(self):
        super().__init__(
            id="fault_selinux_boolean_httpd_001",
            category="troubleshooting",
            difficulty="exam",
            points=12
        )
        self.boolean_name = 'httpd_can_network_connect'
        self.exam_domain = 7
        self.tags = ['selinux', 'boolean', 'httpd', 'fault-injection', 'exam-seen']
        self.exam_tips = [
            "getsebool -a | grep httpd lists all httpd-related booleans",
            "Always use -P flag with setsebool to make changes persistent",
            "audit2why tells you WHICH boolean to enable from an AVC denial",
        ]
        self._original_value = 'on'

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Apache Cannot Connect to Backend\n"
            "=" * 50 + "\n\n"
            "Symptom: httpd is running but cannot make outgoing network connections\n"
            "to a backend service (proxy, database, API). Requests time out.\n\n"
            "Tasks:\n"
            "  1. Identify the SELinux denial using audit logs\n"
            "  2. Determine the correct boolean to enable\n"
            "  3. Enable the boolean persistently across reboots"
        )
        self.hints = [
            "Check denials: ausearch -m AVC -ts recent | audit2why",
            "List relevant booleans: getsebool -a | grep httpd",
            f"Fix: setsebool -P {self.boolean_name} on",
            "Verify: getsebool httpd_can_network_connect",
        ]
        return self

    def inject_fault(self):
        # Save current value first
        r = _run(['getsebool', self.boolean_name])
        if r.returncode == 0 and '->' in r.stdout:
            val = r.stdout.split('->')[-1].strip().split()[0]
            self._original_value = val

        r = _run(['setsebool', '-P', self.boolean_name, 'off'])
        if r.returncode != 0:
            return False, f"setsebool failed: {r.stderr.strip()}"

        # Trigger an actual denial so audit logs have something real
        _run(['curl', '-s', '--max-time', '2', 'http://localhost:8080'], timeout=5)

        save_fault_state(self.id, {
            'boolean': self.boolean_name,
            'original_value': self._original_value,
        })
        return True, f"Set {self.boolean_name}=off (was {self._original_value})"

    def restore_fault(self):
        msgs = []
        _restore_selinux_boolean({'boolean': self.boolean_name, 'original_value': self._original_value}, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: boolean is on (7 pts)
        r = execute_safe(['getsebool', self.boolean_name])
        if r.success and '-> on' in r.stdout:
            checks.append(ValidationCheck("boolean_enabled", True, 7,
                                          message=f"{self.boolean_name} is on"))
            score += 7
        else:
            val = r.stdout.strip() if r.success else 'unknown'
            checks.append(ValidationCheck("boolean_enabled", False, 0, max_points=7,
                                          message=f"{self.boolean_name} is off or unknown: {val}"))

        # Check 2: persistent (survives reboot) — check the permanent store (5 pts)
        r = execute_safe(['semanage', 'boolean', '-l'])
        if r.success:
            for line in r.stdout.splitlines():
                if self.boolean_name in line and '(on' in line:
                    checks.append(ValidationCheck("boolean_persistent", True, 5,
                                                  message="Boolean change is persistent"))
                    score += 5
                    break
            else:
                checks.append(ValidationCheck("boolean_persistent", False, 0, max_points=5,
                                              message="Boolean is on now but NOT set persistently (-P flag required)"))
        else:
            checks.append(ValidationCheck("boolean_persistent", False, 0, max_points=5,
                                          message="Could not verify persistence (semanage not available)"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── Firewall: http port blocked ───────────────────────────────────────────────

@TaskRegistry.register("troubleshooting")
class FirewallHttpBlockedFaultTask(TroubleshootingTask):

    def __init__(self):
        super().__init__(
            id="fault_firewall_http_001",
            category="troubleshooting",
            difficulty="exam",
            points=10
        )
        self.zone = 'public'
        self.service = 'http'
        self.exam_domain = 7
        self.tags = ['firewalld', 'http', 'fault-injection']
        self.exam_tips = [
            "Always add --permanent AND reload, or use both flags together",
            "firewall-cmd --list-all shows everything currently active in a zone",
            "Without --permanent, the rule disappears after next reload or reboot",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Web Server Unreachable from Network\n"
            "=" * 50 + "\n\n"
            "Symptom: httpd is running and serving locally (curl localhost works),\n"
            "but the web server is not reachable from external clients on port 80.\n\n"
            "Tasks:\n"
            "  1. Identify why external HTTP traffic is blocked\n"
            "  2. Open port 80 / the http service in the firewall\n"
            "  3. Make the rule permanent so it survives reboots"
        )
        self.hints = [
            "Check active rules: firewall-cmd --list-all",
            "Add service: firewall-cmd --zone=public --add-service=http --permanent",
            "Reload to activate: firewall-cmd --reload",
            "Verify: firewall-cmd --query-service=http",
        ]
        return self

    def inject_fault(self):
        # Only remove if currently present (avoid injecting into already-broken state)
        r = _run(['firewall-cmd', '--zone=public', '--query-service=http'])
        was_present = r.returncode == 0

        _run(['firewall-cmd', '--zone=public', '--remove-service=http'])
        _run(['firewall-cmd', '--zone=public', '--remove-service=http', '--permanent'])

        save_fault_state(self.id, {
            'zone': self.zone,
            'service': self.service,
            'was_present': was_present,
        })
        return True, "Removed http service from public zone (runtime + permanent)"

    def restore_fault(self):
        msgs = []
        _restore_firewall({'zone': self.zone, 'service': self.service}, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: service active in runtime (4 pts)
        r = execute_safe(['firewall-cmd', '--zone=public', '--query-service=http'])
        if r.success and r.stdout.strip() == 'yes':
            checks.append(ValidationCheck("fw_runtime", True, 4, message="http service active in runtime firewall"))
            score += 4
        else:
            checks.append(ValidationCheck("fw_runtime", False, 0, max_points=4,
                                          message="http service not in runtime firewall rules"))

        # Check 2: service permanent (4 pts)
        r = execute_safe(['firewall-cmd', '--zone=public', '--query-service=http', '--permanent'])
        if r.success and r.stdout.strip() == 'yes':
            checks.append(ValidationCheck("fw_permanent", True, 4, message="http service in permanent config"))
            score += 4
        else:
            checks.append(ValidationCheck("fw_permanent", False, 0, max_points=4,
                                          message="http service NOT in permanent config — won't survive reboot"))

        # Check 3: httpd listening (2 pts)
        r = execute_safe(['ss', '-tlnp'])
        if r.success and (':80 ' in r.stdout or ':80\n' in r.stdout):
            checks.append(ValidationCheck("httpd_listening", True, 2, message="httpd listening on port 80"))
            score += 2
        else:
            checks.append(ValidationCheck("httpd_listening", False, 0, max_points=2,
                                          message="httpd not listening on port 80"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── SSHD: bad config line preventing restart ──────────────────────────────────

@TaskRegistry.register("troubleshooting")
class SshdBadConfigFaultTask(TroubleshootingTask):
    MARKER = '# RHCSA-FAULT-INJECT'

    def __init__(self):
        super().__init__(
            id="fault_sshd_config_001",
            category="troubleshooting",
            difficulty="exam",
            points=10
        )
        self.exam_domain = 7
        self.tags = ['ssh', 'sshd_config', 'fault-injection']
        self.exam_tips = [
            "sshd -t validates config without restarting — always run this first",
            "journalctl -xeu sshd shows the exact line that failed to parse",
            "Never restart sshd without validating config — you'll lock yourself out",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: sshd Will Not Restart\n"
            "=" * 50 + "\n\n"
            "Symptom: Attempting to restart sshd fails with a config parse error.\n"
            "Current sessions still work, but sshd cannot be reloaded or restarted.\n\n"
            "Tasks:\n"
            "  1. Identify the bad configuration line\n"
            "  2. Remove or fix the offending entry in /etc/ssh/sshd_config\n"
            "  3. Verify the config is valid with sshd -t\n"
            "  4. Successfully restart sshd"
        )
        self.hints = [
            "Test config without restarting: sshd -t",
            "Check what failed: journalctl -xeu sshd --no-pager | tail -20",
            "Look for unusual lines in /etc/ssh/sshd_config",
            "After fixing, restart: systemctl restart sshd",
        ]
        return self

    def inject_fault(self):
        bad_line = f'InvalidDirective ExamBreaker {self.MARKER}\n'
        with open('/etc/ssh/sshd_config', 'a') as f:
            f.write(bad_line)

        save_fault_state(self.id, {'marker': self.MARKER})
        return True, f"Appended invalid directive to /etc/ssh/sshd_config"

    def restore_fault(self):
        msgs = []
        _restore_sshd_config({'marker': self.MARKER}, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: config parses cleanly (5 pts)
        r = execute_safe(['sshd', '-t'])
        if r.success:
            checks.append(ValidationCheck("sshd_config_valid", True, 5, message="sshd config validates without errors"))
            score += 5
        else:
            checks.append(ValidationCheck("sshd_config_valid", False, 0, max_points=5,
                                          message=f"sshd -t still fails: {r.stderr.strip()[:100]}"))

        # Check 2: bad line removed (3 pts)
        r = execute_safe(['grep', '-c', 'InvalidDirective', '/etc/ssh/sshd_config'])
        if r.success and r.stdout.strip() == '0':
            checks.append(ValidationCheck("bad_line_removed", True, 3, message="Invalid directive removed from sshd_config"))
            score += 3
        else:
            checks.append(ValidationCheck("bad_line_removed", False, 0, max_points=3,
                                          message="InvalidDirective line still present in sshd_config"))

        # Check 3: sshd running (2 pts)
        r = execute_safe(['systemctl', 'is-active', 'sshd'])
        if r.success and 'active' in r.stdout:
            checks.append(ValidationCheck("sshd_running", True, 2, message="sshd is running"))
            score += 2
        else:
            checks.append(ValidationCheck("sshd_running", False, 0, max_points=2, message="sshd is not running"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── Service: httpd stopped and disabled ──────────────────────────────────────

@TaskRegistry.register("troubleshooting")
class HttpdDisabledFaultTask(TroubleshootingTask):

    def __init__(self):
        super().__init__(
            id="fault_service_httpd_001",
            category="troubleshooting",
            difficulty="exam",
            points=8
        )
        self.service = 'httpd'
        self.exam_domain = 4
        self.tags = ['services', 'httpd', 'systemd', 'fault-injection']
        self.exam_tips = [
            "systemctl enable --now does both start and enable in one command",
            "Always check 'systemctl status' first — it often says exactly why it failed",
        ]
        self._was_active = False
        self._was_enabled = False

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Web Service Not Running at Boot\n"
            "=" * 50 + "\n\n"
            "Symptom: After a reboot, httpd is not running. The service was\n"
            "previously configured but is now stopped and disabled.\n\n"
            "Tasks:\n"
            "  1. Start the httpd service\n"
            "  2. Enable it to start automatically at boot\n"
            "  3. Verify both states"
        )
        self.hints = [
            "Check service state: systemctl status httpd",
            "Start + enable: systemctl enable --now httpd",
            "Verify: systemctl is-active httpd && systemctl is-enabled httpd",
        ]
        return self

    def inject_fault(self):
        r = _run(['systemctl', 'is-active', self.service])
        self._was_active = r.returncode == 0
        r = _run(['systemctl', 'is-enabled', self.service])
        self._was_enabled = 'enabled' in r.stdout

        _run(['systemctl', 'stop', self.service])
        _run(['systemctl', 'disable', self.service])

        save_fault_state(self.id, {
            'service': self.service,
            'was_active': self._was_active,
            'was_enabled': self._was_enabled,
        })
        return True, f"Stopped and disabled {self.service}"

    def restore_fault(self):
        msgs = []
        _restore_service({
            'service': self.service,
            'was_active': self._was_active,
            'was_enabled': self._was_enabled,
        }, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        r = execute_safe(['systemctl', 'is-active', self.service])
        if r.success and 'active' in r.stdout:
            checks.append(ValidationCheck("service_active", True, 4, message=f"{self.service} is running"))
            score += 4
        else:
            checks.append(ValidationCheck("service_active", False, 0, max_points=4,
                                          message=f"{self.service} is not running"))

        r = execute_safe(['systemctl', 'is-enabled', self.service])
        if r.success and 'enabled' in r.stdout:
            checks.append(ValidationCheck("service_enabled", True, 4, message=f"{self.service} enabled at boot"))
            score += 4
        else:
            checks.append(ValidationCheck("service_enabled", False, 0, max_points=4,
                                          message=f"{self.service} NOT enabled at boot"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── Sudoers: file has wrong permissions ──────────────────────────────────────

@TaskRegistry.register("troubleshooting")
class SudoersWrongPermsFaultTask(TroubleshootingTask):
    PRACTICE_USER = 'sudopractice'
    SUDOERS_FILE = '/etc/sudoers.d/sudopractice'

    def __init__(self):
        super().__init__(
            id="fault_sudoers_perms_001",
            category="troubleshooting",
            difficulty="exam",
            points=10
        )
        self.exam_domain = 3
        self.tags = ['sudo', 'sudoers', 'permissions', 'fault-injection']
        self.exam_tips = [
            "sudo ignores any sudoers.d file with permissions other than 0440",
            "Always use visudo -c to validate before relying on a sudoers file",
            "chmod 440 /etc/sudoers.d/file — not 0777, not 0600",
        ]

    def generate(self, **params):
        self.description = (
            f"TROUBLESHOOTING: sudo Privileges Not Working\n"
            "=" * 50 + "\n\n"
            f"Symptom: User '{self.PRACTICE_USER}' has a sudoers file in\n"
            f"/etc/sudoers.d/ but sudo still says they are not in the sudoers file.\n\n"
            "Tasks:\n"
            f"  1. Identify why sudo is ignoring /etc/sudoers.d/{self.PRACTICE_USER}\n"
            "  2. Fix the issue\n"
            "  3. Verify sudo -l shows the user's privileges"
        )
        self.hints = [
            "Check file permissions: ls -l /etc/sudoers.d/",
            "sudo ignores files with world-writable or group-writable permissions",
            f"Fix: chmod 440 {self.SUDOERS_FILE}",
            f"Verify: sudo -l -U {self.PRACTICE_USER}",
        ]
        return self

    def inject_fault(self):
        # Create user if missing
        r = _run(['id', self.PRACTICE_USER])
        if r.returncode != 0:
            _run(['useradd', '-M', '-s', '/sbin/nologin', self.PRACTICE_USER])

        # Write sudoers file with correct content but wrong permissions
        content = f"{self.PRACTICE_USER} ALL=(ALL) NOPASSWD: /usr/bin/systemctl status\n"
        with open(self.SUDOERS_FILE, 'w') as f:
            f.write(content)
        os.chmod(self.SUDOERS_FILE, 0o777)   # sudo will ignore this

        save_fault_state(self.id, {
            'path': self.SUDOERS_FILE,
            'user': self.PRACTICE_USER,
            'original_perms': '0440',
        })
        return True, f"Created {self.SUDOERS_FILE} with permissions 0777 (sudo will ignore)"

    def restore_fault(self):
        msgs = []
        if os.path.exists(self.SUDOERS_FILE):
            os.remove(self.SUDOERS_FILE)
            msgs.append(f"Removed {self.SUDOERS_FILE}")
        # Remove practice user
        _run(['userdel', self.PRACTICE_USER])
        msgs.append(f"Removed practice user {self.PRACTICE_USER}")
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: file exists (2 pts)
        if os.path.exists(self.SUDOERS_FILE):
            checks.append(ValidationCheck("file_exists", True, 2, message=f"{self.SUDOERS_FILE} exists"))
            score += 2
        else:
            checks.append(ValidationCheck("file_exists", False, 0, max_points=2,
                                          message=f"{self.SUDOERS_FILE} was deleted"))
            return ValidationResult(self.id, False, score, self.points, checks)

        # Check 2: permissions are 0440 (4 pts)
        stat = os.stat(self.SUDOERS_FILE)
        perms = oct(stat.st_mode)[-4:]
        if perms in ('0440', '0400'):
            checks.append(ValidationCheck("correct_perms", True, 4, message=f"Permissions are {perms}"))
            score += 4
        else:
            checks.append(ValidationCheck("correct_perms", False, 0, max_points=4,
                                          message=f"Permissions are {perms}, need 0440"))

        # Check 3: sudo -l recognizes the user (4 pts)
        r = execute_safe(['sudo', '-l', '-U', self.PRACTICE_USER])
        if r.success and 'systemctl' in r.stdout:
            checks.append(ValidationCheck("sudo_works", True, 4, message=f"sudo -l shows privileges for {self.PRACTICE_USER}"))
            score += 4
        else:
            checks.append(ValidationCheck("sudo_works", False, 0, max_points=4,
                                          message=f"sudo still not recognizing {self.PRACTICE_USER}"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── Filesystem: bad fstab entry ───────────────────────────────────────────────

@TaskRegistry.register("troubleshooting")
class BadFstabFaultTask(TroubleshootingTask):
    MARKER = '# RHCSA-FAULT-FSTAB'
    MOUNTPOINT = '/mnt/faulttest'

    def __init__(self):
        super().__init__(
            id="fault_fstab_001",
            category="troubleshooting",
            difficulty="exam",
            points=10
        )
        self.exam_domain = 4
        self.tags = ['fstab', 'mount', 'filesystem', 'fault-injection']
        self.exam_tips = [
            "mount -a tests all fstab entries — run it before rebooting",
            "findmnt --verify --fstab catches syntax errors without mounting",
            "A bad fstab entry will drop you into emergency mode on next boot",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Bad /etc/fstab Entry\n"
            "=" * 50 + "\n\n"
            "Symptom: After adding a filesystem to /etc/fstab, running 'mount -a'\n"
            "produces errors. The bad entry will cause an emergency mode boot.\n\n"
            "Tasks:\n"
            "  1. Identify the bad entry in /etc/fstab\n"
            "  2. Fix or remove the problematic line\n"
            "  3. Verify 'mount -a' runs without errors"
        )
        self.hints = [
            "Test fstab: mount -a",
            "Validate syntax: findmnt --verify --fstab",
            "Inspect entries: cat /etc/fstab",
            "A non-existent UUID or wrong device path causes the error",
            f"Look for the entry referencing {self.MOUNTPOINT}",
        ]
        return self

    def inject_fault(self):
        os.makedirs(self.MOUNTPOINT, exist_ok=True)
        bad_entry = (
            f"UUID=00000000-dead-beef-0000-000000000000 {self.MOUNTPOINT} "
            f"xfs defaults 0 0 {self.MARKER}\n"
        )
        with open('/etc/fstab', 'a') as f:
            f.write(bad_entry)

        save_fault_state(self.id, {'marker': self.MARKER})
        return True, f"Added non-existent UUID entry for {self.MOUNTPOINT} to /etc/fstab"

    def restore_fault(self):
        msgs = []
        _restore_fstab({'marker': self.MARKER}, msgs)
        try:
            os.rmdir(self.MOUNTPOINT)
        except OSError:
            pass
        clear_fault_state()
        return True, '; '.join(msgs)

    def validate(self):
        checks = []
        score = 0

        # Check 1: bad line gone (5 pts)
        r = execute_safe(['grep', '-c', 'RHCSA-FAULT-FSTAB', '/etc/fstab'])
        if r.success and r.stdout.strip() == '0':
            checks.append(ValidationCheck("bad_entry_removed", True, 5, message="Bad fstab entry removed"))
            score += 5
        else:
            checks.append(ValidationCheck("bad_entry_removed", False, 0, max_points=5,
                                          message="Bad fstab entry still present"))

        # Check 2: mount -a succeeds (5 pts)
        r = execute_safe(['mount', '-a'])
        if r.returncode == 0:
            checks.append(ValidationCheck("mount_a_clean", True, 5, message="mount -a completes without errors"))
            score += 5
        else:
            checks.append(ValidationCheck("mount_a_clean", False, 0, max_points=5,
                                          message=f"mount -a still fails: {r.stderr.strip()[:100]}"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


# ── Legacy descriptive tasks (kept, no fault injection) ──────────────────────

class SSHNotStartingTask(TroubleshootingTask):
    """Kept for compatibility — descriptive only, no fault injection."""
    has_fault_injection = False

    def __init__(self):
        super().__init__(
            id="troubleshoot_ssh_001",
            category="troubleshooting",
            difficulty="exam",
            points=12
        )

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: SSH Service Won't Start\n"
            "Symptom: sshd fails to start with 'Permission denied' binding to port.\n\n"
            "Your task:\n"
            "  1. Diagnose the root cause\n"
            "  2. Fix the problem\n"
            "  3. Ensure SSH service starts and is enabled at boot"
        )
        self.hints = [
            "Start by checking: systemctl status sshd",
            "Look at journal logs: journalctl -xeu sshd",
            "Check SELinux denials: ausearch -m AVC -ts recent",
        ]
        return self

    def inject_fault(self):
        return False, "Legacy task — no fault injection"

    def restore_fault(self):
        return True, "Nothing to restore"

    def validate(self):
        from validators.command_validators import validate_service_state, validate_service_enabled
        checks = []
        score = 0
        if validate_service_state('sshd', 'active'):
            checks.append(ValidationCheck("sshd_running", True, 6, message="SSHD is running"))
            score += 6
        else:
            checks.append(ValidationCheck("sshd_running", False, 0, max_points=6, message="SSHD not running"))
        if validate_service_enabled('sshd', True):
            checks.append(ValidationCheck("sshd_enabled", True, 6, message="SSHD enabled at boot"))
            score += 6
        else:
            checks.append(ValidationCheck("sshd_enabled", False, 0, max_points=6, message="SSHD not enabled"))
        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)
