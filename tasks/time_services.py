"""
Time services tasks for RHCSA exam (chrony, timedatectl).
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("time_services")
class ConfigureTimezoneTask(BaseTask):
    """Set system timezone."""

    def __init__(self):
        super().__init__(
            id="time_tz_001",
            category="time_services",
            difficulty="easy",
            points=6
        )
        self.timezone = None

    def generate(self, **params):
        """Generate timezone task."""
        timezones = [
            'America/New_York',
            'America/Los_Angeles',
            'Europe/London',
            'Asia/Tokyo',
            'UTC'
        ]
        self.timezone = params.get('timezone', random.choice(timezones))

        self.description = (
            f"Configure system timezone:\n"
            f"  - Set timezone to: {self.timezone}\n"
            f"  - Change must be persistent"
        )

        self.hints = [
            "List timezones: timedatectl list-timezones",
            f"Set timezone: timedatectl set-timezone {self.timezone}",
            "Verify: timedatectl",
            "Alternative: ln -sf /usr/share/zoneinfo/{tz} /etc/localtime"
        ]

        return self

    def validate(self):
        """Validate timezone configuration."""
        checks = []
        total_points = 0

        result = execute_safe(['timedatectl', 'show', '--property=Timezone'])
        if result.success:
            current_tz = result.stdout.strip().replace('Timezone=', '')
            if current_tz == self.timezone:
                checks.append(ValidationCheck(
                    name="timezone_set",
                    passed=True,
                    points=6,
                    message=f"Timezone is {self.timezone}"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="timezone_set",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Timezone is {current_tz}, expected {self.timezone}"
                ))
        else:
            checks.append(ValidationCheck(
                name="timezone_set",
                passed=False,
                points=0,
                max_points=6,
                message="Could not check timezone"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("time_services")
class ConfigureChronydTask(BaseTask):
    """Configure chrony for NTP synchronization."""

    def __init__(self):
        super().__init__(
            id="time_chrony_001",
            category="time_services",
            difficulty="medium",
            points=12
        )
        self.ntp_server = None

    def generate(self, **params):
        """Generate chrony configuration task."""
        ntp_servers = [
            'time.example.com',
            'ntp.example.org',
            'clock.redhat.com'
        ]
        self.ntp_server = params.get('server', random.choice(ntp_servers))

        self.description = (
            f"Configure chrony NTP synchronization:\n"
            f"  - NTP Server: {self.ntp_server}\n"
            f"  - Edit /etc/chrony.conf\n"
            f"  - Enable and start chronyd service\n"
            f"  - Verify synchronization"
        )

        self.hints = [
            f"Add to /etc/chrony.conf: server {self.ntp_server} iburst",
            "Or: pool {server} iburst",
            "Restart service: systemctl restart chronyd",
            "Enable service: systemctl enable chronyd",
            "Check sync: chronyc sources",
            "Check tracking: chronyc tracking"
        ]

        return self

    def validate(self):
        """Validate chrony configuration."""
        checks = []
        total_points = 0

        # Check 1: chronyd is running (4 points)
        result = execute_safe(['systemctl', 'is-active', 'chronyd'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="chronyd_running",
                passed=True,
                points=4,
                message="chronyd service is running"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="chronyd_running",
                passed=False,
                points=0,
                max_points=4,
                message="chronyd service is not running"
            ))

        # Check 2: chronyd is enabled (2 points)
        result = execute_safe(['systemctl', 'is-enabled', 'chronyd'])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="chronyd_enabled",
                passed=True,
                points=2,
                message="chronyd service is enabled"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="chronyd_enabled",
                passed=False,
                points=0,
                max_points=2,
                message="chronyd service is not enabled"
            ))

        # Check 3: NTP server in config (4 points)
        if validate_file_contains('/etc/chrony.conf', self.ntp_server):
            checks.append(ValidationCheck(
                name="ntp_configured",
                passed=True,
                points=4,
                message=f"NTP server {self.ntp_server} in config"
            ))
            total_points += 4
        elif validate_file_contains('/etc/chrony.conf', 'server ') or validate_file_contains('/etc/chrony.conf', 'pool '):
            checks.append(ValidationCheck(
                name="ntp_configured",
                passed=True,
                points=2,
                message="NTP servers configured (different server)"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="ntp_configured",
                passed=False,
                points=0,
                max_points=4,
                message="No NTP server configured"
            ))

        # Check 4: NTP sync enabled (2 points)
        result = execute_safe(['timedatectl', 'show', '--property=NTPSynchronized'])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="ntp_synced",
                passed=True,
                points=2,
                message="NTP is synchronized"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="ntp_synced",
                passed=False,
                points=0,
                max_points=2,
                message="NTP not synchronized (may take time)"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("time_services")
class EnableNTPSyncTask(BaseTask):
    """Fault-injection: chronyd is stopped/disabled; user must re-enable it."""

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="time_ntp_001",
            category="time_services",
            difficulty="easy",
            points=6
        )
        self.exam_tips = [
            "'timedatectl set-ntp true' enables NTP and starts chronyd automatically.",
            "'systemctl enable --now chronyd' is the lower-level equivalent.",
            "Verify sync with: timedatectl status  (look for 'NTP service: active')",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: NTP Time Sync Disabled\n"
            "Symptom: The system clock is not synchronizing with time servers.\n"
            "chronyd has been stopped and disabled.\n\n"
            "Tasks:\n"
            "  1. Re-enable automatic NTP time synchronization\n"
            "  2. Ensure the chronyd service is running\n"
            "  3. Verify NTP sync is active"
        )
        self.hints = [
            "Enable NTP: timedatectl set-ntp true",
            "Or: systemctl enable --now chronyd",
            "Verify: timedatectl  (look for 'NTP service: active')",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        _sp.run(['timedatectl', 'set-ntp', 'false'], capture_output=True)
        _sp.run(['systemctl', 'stop', 'chronyd'], capture_output=True)
        _sp.run(['systemctl', 'disable', 'chronyd'], capture_output=True)
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'service': 'chronyd'})
        return True, "Disabled NTP and stopped chronyd"

    def restore_fault(self):
        import subprocess as _sp
        _sp.run(['systemctl', 'enable', '--now', 'chronyd'], capture_output=True)
        _sp.run(['timedatectl', 'set-ntp', 'true'], capture_output=True)
        from tasks.troubleshooting import clear_fault_state
        clear_fault_state()
        return True, "Re-enabled chronyd and NTP"

    def validate(self):
        checks = []
        score = 0

        r = execute_safe(['timedatectl', 'show', '--property=NTP'])
        if r.success and 'NTP=yes' in r.stdout:
            checks.append(ValidationCheck("ntp_enabled", True, 3, message="NTP is enabled"))
            score += 3
        else:
            checks.append(ValidationCheck("ntp_enabled", False, 0, max_points=3,
                                          message="NTP is not enabled (timedatectl set-ntp true)"))

        r = execute_safe(['systemctl', 'is-active', 'chronyd'])
        svc_ok = r.success and r.stdout.strip() == 'active'
        if not svc_ok:
            r2 = execute_safe(['systemctl', 'is-active', 'ntpd'])
            svc_ok = r2.success and r2.stdout.strip() == 'active'
        if svc_ok:
            checks.append(ValidationCheck("service_running", True, 3, message="Time service is running"))
            score += 3
        else:
            checks.append(ValidationCheck("service_running", False, 0, max_points=3,
                                          message="No time service running (systemctl start chronyd)"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


@TaskRegistry.register("time_services")
class SetSystemDateTask(BaseTask):
    """Set system date and time manually (requires disabling NTP first)."""

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="time_set_001",
            category="time_services",
            difficulty="easy",
            points=6
        )
        self.target_time = None
        self.exam_tips = [
            "timedatectl set-ntp false MUST come before set-time or it will be rejected.",
            "After setting time manually, re-enable NTP: timedatectl set-ntp true",
            "The format is: timedatectl set-time 'YYYY-MM-DD HH:MM:SS'",
        ]

    def generate(self, **params):
        self.target_time = params.get('time', '2025-06-15 14:30:00')

        self.description = (
            f"Set the system clock manually:\n"
            f"  1. Disable NTP synchronization (required before manual set)\n"
            f"  2. Set the system time to: {self.target_time}\n"
            f"  3. Verify the time was applied\n"
            f"  (Re-enabling NTP afterwards is good practice but not validated here)"
        )
        self.hints = [
            "Disable NTP first: timedatectl set-ntp false",
            f"Set time: timedatectl set-time '{self.target_time}'",
            "Verify: timedatectl  or  date",
            "Re-enable after: timedatectl set-ntp true",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        _sp.run(['timedatectl', 'set-ntp', 'false'], capture_output=True)
        _sp.run(['systemctl', 'stop', 'chronyd'], capture_output=True)
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'service': 'chronyd'})
        return True, "Disabled NTP so manual time-setting is possible"

    def restore_fault(self):
        import subprocess as _sp
        _sp.run(['timedatectl', 'set-ntp', 'true'], capture_output=True)
        _sp.run(['systemctl', 'enable', '--now', 'chronyd'], capture_output=True)
        from tasks.troubleshooting import clear_fault_state
        clear_fault_state()
        return True, "Re-enabled NTP sync"

    def validate(self):
        checks = []
        score = 0

        # Check 1: NTP was disabled first (user ran set-ntp false) — now should be off
        # OR they re-enabled it: either state shows they engaged with the task.
        # We award points for knowing to disable NTP before setting time manually.
        r = execute_safe(['timedatectl', 'show', '--property=NTP'])
        ntp_off = r.success and 'NTP=no' in r.stdout
        if ntp_off:
            checks.append(ValidationCheck("ntp_disabled", True, 3,
                message="NTP is disabled — manual time can be set with timedatectl set-time"))
            score += 3
        else:
            checks.append(ValidationCheck("ntp_disabled", False, 0, max_points=3,
                message="NTP must be disabled before setting time manually: timedatectl set-ntp false"))

        # Check 2: chronyd is stopped (consistent with NTP disabled for manual set)
        r = execute_safe(['systemctl', 'is-active', 'chronyd'])
        if r.success and r.stdout.strip() != 'active':
            checks.append(ValidationCheck("chrony_stopped", True, 3,
                message="chronyd is stopped — system clock is under manual control"))
            score += 3
        else:
            checks.append(ValidationCheck("chrony_stopped", False, 0, max_points=3,
                message="chronyd is still running — stop it before setting time manually"))

        return ValidationResult(self.id, score >= self.points * 0.7, score, self.points, checks)


@TaskRegistry.register("time_services")
class ConfigureNTPPoolTask(BaseTask):
    """Configure multiple NTP servers/pools."""

    def __init__(self):
        super().__init__(
            id="time_pool_001",
            category="time_services",
            difficulty="medium",
            points=10
        )
        self.ntp_pools = None

    def generate(self, **params):
        """Generate NTP pool configuration task."""
        self.ntp_pools = params.get('pools', [
            '0.rhel.pool.ntp.org',
            '1.rhel.pool.ntp.org',
            '2.rhel.pool.ntp.org'
        ])

        self.description = (
            f"Configure NTP server pools:\n"
            f"  - Add the following NTP pools to chrony:\n"
            + "\n".join(f"    - {pool}" for pool in self.ntp_pools) +
            f"\n  - Use 'pool' directive with 'iburst' option\n"
            f"  - Restart chronyd after changes"
        )

        self.hints = [
            "Edit /etc/chrony.conf",
            "Add lines: pool <server> iburst",
            "iburst speeds up initial sync",
            "Restart: systemctl restart chronyd",
            "Verify: chronyc sources -v"
        ]

        return self

    def validate(self):
        """Validate NTP pool configuration."""
        checks = []
        total_points = 0

        # Check 1: chronyd running (3 points)
        result = execute_safe(['systemctl', 'is-active', 'chronyd'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="chronyd_active",
                passed=True,
                points=3,
                message="chronyd is running"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="chronyd_active",
                passed=False,
                points=0,
                max_points=3,
                message="chronyd is not running"
            ))

        # Check 2: At least one pool configured (4 points)
        pools_found = 0
        for pool in self.ntp_pools:
            if validate_file_contains('/etc/chrony.conf', pool):
                pools_found += 1

        if pools_found >= 2:
            checks.append(ValidationCheck(
                name="pools_configured",
                passed=True,
                points=4,
                message=f"{pools_found} NTP pools configured"
            ))
            total_points += 4
        elif pools_found == 1:
            checks.append(ValidationCheck(
                name="pools_configured",
                passed=True,
                points=2,
                message="1 NTP pool configured"
            ))
            total_points += 2
        else:
            # Check for any pool directive
            if validate_file_contains('/etc/chrony.conf', 'pool '):
                checks.append(ValidationCheck(
                    name="pools_configured",
                    passed=True,
                    points=2,
                    message="Some NTP pools configured"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="pools_configured",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="No NTP pools found in config"
                ))

        # Check 3: iburst option used (3 points)
        if validate_file_contains('/etc/chrony.conf', 'iburst'):
            checks.append(ValidationCheck(
                name="iburst_used",
                passed=True,
                points=3,
                message="iburst option configured"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="iburst_used",
                passed=False,
                points=0,
                max_points=3,
                message="iburst option not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
