"""
Systemd timer tasks for RHCSA EX200 v10 exam.
Covers creating, configuring, enabling, converting, and troubleshooting
systemd timer units -- a topic newly emphasized in the v10 exam objectives.
"""

import os
import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared pools for randomisation
# ---------------------------------------------------------------------------
_TIMER_NAMES = ['backup-logs', 'cleanup-tmp', 'sync-data', 'health-check']

_TIMER_COMMANDS = [
    '/usr/local/bin/backup-logs.sh',
    '/usr/local/bin/cleanup-tmp.sh',
    '/usr/local/bin/sync-data.sh',
    '/usr/local/bin/health-check.sh',
]

_ONCALENDAR_SCHEDULES = [
    ('Mon *-*-* 02:00:00', 'every Monday at 02:00'),
    ('*-*-* *:00/15',      'every 15 minutes on the hour'),
    ('*-*-* 06:00:00',     'daily at 06:00'),
    ('Fri *-*-* 23:30:00', 'every Friday at 23:30'),
    ('*-*-01 00:00:00',    'first day of every month at midnight'),
]

_ONBOOT_DELAYS = ['1min', '5min', '10min', '30min']

_ONUNIT_ACTIVE_INTERVALS = ['5min', '10min', '15min', '30min', '1h']

_CRON_TO_ONCALENDAR = [
    ('*/5 * * * *',   '*-*-* *:00/5:00',    'every 5 minutes'),
    ('0 * * * *',     '*-*-* *:00:00',       'every hour on the hour'),
    ('30 2 * * *',    '*-*-* 02:30:00',      'daily at 02:30'),
    ('0 0 * * 0',     'Sun *-*-* 00:00:00',  'every Sunday at midnight'),
    ('0 3 1 * *',     '*-*-01 03:00:00',     'first day of month at 03:00'),
    ('*/15 * * * *',  '*-*-* *:00/15:00',    'every 15 minutes'),
    ('0 6 * * 1-5',   'Mon..Fri *-*-* 06:00:00', 'weekdays at 06:00'),
]


# ===== 1. CreateSystemdTimerTask (exam / 15pts) [PERSIST] [EXAM-SEEN] ======

@TaskRegistry.register("systemd_timers")
class CreateSystemdTimerTask(BaseTask):
    """Create a complete systemd .service + .timer pair."""

    def __init__(self):
        super().__init__(
            id="timer_create_001",
            category="systemd_timers",
            difficulty="exam",
            points=15,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'exam-seen', 'systemd', 'timer', 'persistence']
        self.exam_tips = [
            "You need BOTH a .service AND a .timer file in /etc/systemd/system/.",
            "The .timer file must have [Timer] with OnCalendar= and [Install] WantedBy=timers.target.",
            "Always run 'systemctl daemon-reload' after creating unit files.",
            "Enable and start the .timer (NOT the .service).",
        ]
        self.timer_name = None
        self.command = None
        self.on_calendar = None
        self.on_calendar_desc = None

    def generate(self, **params):
        idx = random.randrange(len(_TIMER_NAMES))
        self.timer_name = params.get('timer_name', _TIMER_NAMES[idx])
        self.command = params.get('command', _TIMER_COMMANDS[idx])
        schedule = params.get('schedule', random.choice(_ONCALENDAR_SCHEDULES))
        self.on_calendar = schedule[0]
        self.on_calendar_desc = schedule[1]

        svc = f'{self.timer_name}.service'
        tmr = f'{self.timer_name}.timer'

        self.description = (
            f"Create a systemd timer that runs a command on a schedule:\n"
            f"  - Timer name: {tmr}\n"
            f"  - Service name: {svc}\n"
            f"  - Command to execute: {self.command}\n"
            f"  - Schedule (OnCalendar): {self.on_calendar} ({self.on_calendar_desc})\n"
            f"  - Place both unit files in /etc/systemd/system/\n"
            f"  - Enable and start the timer so it persists across reboots"
        )

        self.hints = [
            f"Create /etc/systemd/system/{svc} with [Unit], [Service] ExecStart={self.command}",
            f"Create /etc/systemd/system/{tmr} with [Unit], [Timer] OnCalendar={self.on_calendar}, [Install] WantedBy=timers.target",
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr}",
            f"Verify: systemctl list-timers | grep {self.timer_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        svc_path = f'/etc/systemd/system/{self.timer_name}.service'
        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: .service file exists and contains ExecStart (4 pts)
        svc_ok = False
        if os.path.isfile(svc_path):
            try:
                with open(svc_path, 'r') as fh:
                    content = fh.read()
                if f'ExecStart={self.command}' in content or self.command in content:
                    svc_ok = True
            except Exception:
                pass

        if svc_ok:
            checks.append(ValidationCheck(
                name="service_file_correct",
                passed=True,
                points=4,
                message=f"Service file exists with correct ExecStart",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_file_correct",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service file missing or ExecStart incorrect ({svc_path})",
            ))

        # Check 2: .timer file exists and contains OnCalendar (4 pts)
        tmr_ok = False
        if os.path.isfile(tmr_path):
            try:
                with open(tmr_path, 'r') as fh:
                    content = fh.read()
                if f'OnCalendar={self.on_calendar}' in content or self.on_calendar in content:
                    tmr_ok = True
            except Exception:
                pass

        if tmr_ok:
            checks.append(ValidationCheck(
                name="timer_file_correct",
                passed=True,
                points=4,
                message=f"Timer file exists with correct OnCalendar",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_file_correct",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer file missing or OnCalendar incorrect ({tmr_path})",
            ))

        # Check 3: timer is enabled (4 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not enabled (got: {result.stdout.strip()})",
            ))

        # Check 4: timer is active (3 pts)
        result = execute_safe(['systemctl', 'is-active', tmr_unit])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="timer_active",
                passed=True,
                points=3,
                message=f"Timer '{tmr_unit}' is active",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="timer_active",
                passed=False,
                points=0,
                max_points=3,
                message=f"Timer '{tmr_unit}' is not active",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 2. CreateOnCalendarTimerTask (exam / 15pts) [PERSIST] ===============

@TaskRegistry.register("systemd_timers")
class CreateOnCalendarTimerTask(BaseTask):
    """Create a timer with a specific OnCalendar= real-time schedule."""

    def __init__(self):
        super().__init__(
            id="timer_oncalendar_001",
            category="systemd_timers",
            difficulty="exam",
            points=15,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'systemd', 'timer', 'oncalendar', 'persistence']
        self.exam_tips = [
            "OnCalendar= uses systemd calendar event syntax, NOT cron syntax.",
            "Test with 'systemd-analyze calendar \"Mon *-*-* 02:00:00\"' to verify.",
            "Common formats: daily, weekly, *-*-* HH:MM:SS, DayOfWeek *-*-* HH:MM:SS.",
        ]
        self.timer_name = None
        self.command = None
        self.on_calendar = None
        self.on_calendar_desc = None

    def generate(self, **params):
        self.timer_name = params.get('timer_name', f'scheduled-{random.choice(["report", "audit", "rotate", "digest"])}')
        self.command = params.get('command', random.choice([
            '/usr/local/bin/generate-report.sh',
            '/usr/local/bin/rotate-logs.sh',
            '/usr/local/bin/audit-check.sh',
            '/usr/local/bin/daily-digest.sh',
        ]))
        schedule = params.get('schedule', random.choice(_ONCALENDAR_SCHEDULES))
        self.on_calendar = schedule[0]
        self.on_calendar_desc = schedule[1]

        svc = f'{self.timer_name}.service'
        tmr = f'{self.timer_name}.timer'

        self.description = (
            f"Create a systemd timer with a specific real-time schedule:\n"
            f"  - Timer: {tmr}\n"
            f"  - Service: {svc}\n"
            f"  - Command: {self.command}\n"
            f"  - OnCalendar schedule: {self.on_calendar}\n"
            f"    ({self.on_calendar_desc})\n"
            f"  - The timer must be enabled and started\n"
            f"  - Must persist across reboots"
        )

        self.hints = [
            f"Service file [Service]: Type=oneshot, ExecStart={self.command}",
            f"Timer file [Timer]: OnCalendar={self.on_calendar}, Persistent=true",
            f"Timer file [Install]: WantedBy=timers.target",
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr}",
            f"Verify schedule: systemd-analyze calendar '{self.on_calendar}'",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: timer file exists with correct OnCalendar (7 pts)
        oncal_ok = False
        if os.path.isfile(tmr_path):
            try:
                with open(tmr_path, 'r') as fh:
                    content = fh.read()
                if self.on_calendar in content:
                    oncal_ok = True
            except Exception:
                pass

        if oncal_ok:
            checks.append(ValidationCheck(
                name="oncalendar_correct",
                passed=True,
                points=7,
                message=f"Timer file contains OnCalendar={self.on_calendar}",
            ))
            total_points += 7
        else:
            checks.append(ValidationCheck(
                name="oncalendar_correct",
                passed=False,
                points=0,
                max_points=7,
                message=f"Timer file missing or OnCalendar line incorrect",
            ))

        # Check 2: timer is enabled (4 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not enabled",
            ))

        # Check 3: timer is active (4 pts)
        result = execute_safe(['systemctl', 'is-active', tmr_unit])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="timer_active",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is active",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not active",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 3. CreateOnBootTimerTask (medium / 10pts) [PERSIST] =================

@TaskRegistry.register("systemd_timers")
class CreateOnBootTimerTask(BaseTask):
    """Create a monotonic timer that fires after boot (OnBootSec=)."""

    def __init__(self):
        super().__init__(
            id="timer_onboot_001",
            category="systemd_timers",
            difficulty="medium",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'systemd', 'timer', 'onboot', 'persistence']
        self.exam_tips = [
            "OnBootSec= triggers relative to system boot time.",
            "This is a monotonic timer -- no OnCalendar needed.",
            "Combine with OnUnitActiveSec= for repeating after boot.",
        ]
        self.timer_name = None
        self.command = None
        self.onboot_delay = None

    def generate(self, **params):
        self.timer_name = params.get('timer_name', f'post-boot-{random.choice(["init", "check", "warmup", "setup"])}')
        self.command = params.get('command', random.choice([
            '/usr/local/bin/post-boot-init.sh',
            '/usr/local/bin/system-warmup.sh',
            '/usr/local/bin/boot-check.sh',
        ]))
        self.onboot_delay = params.get('onboot_delay', random.choice(_ONBOOT_DELAYS))

        svc = f'{self.timer_name}.service'
        tmr = f'{self.timer_name}.timer'

        self.description = (
            f"Create a monotonic systemd timer that fires after boot:\n"
            f"  - Timer: {tmr}\n"
            f"  - Service: {svc}\n"
            f"  - Command: {self.command}\n"
            f"  - Fire {self.onboot_delay} after system boot (OnBootSec=)\n"
            f"  - Enable the timer so it activates on every boot"
        )

        self.hints = [
            f"Timer file [Timer]: OnBootSec={self.onboot_delay}",
            "No OnCalendar is needed for monotonic timers",
            f"Service file [Service]: Type=oneshot, ExecStart={self.command}",
            f"Timer file [Install]: WantedBy=timers.target",
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: timer file exists and has OnBootSec (5 pts)
        onboot_ok = False
        if os.path.isfile(tmr_path):
            try:
                with open(tmr_path, 'r') as fh:
                    content = fh.read()
                if 'OnBootSec=' in content:
                    onboot_ok = True
            except Exception:
                pass

        if onboot_ok:
            checks.append(ValidationCheck(
                name="onbootsec_present",
                passed=True,
                points=5,
                message=f"Timer file contains OnBootSec= directive",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="onbootsec_present",
                passed=False,
                points=0,
                max_points=5,
                message=f"Timer file missing or OnBootSec= not found",
            ))

        # Check 2: timer is enabled (3 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=3,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=3,
                message=f"Timer '{tmr_unit}' is not enabled",
            ))

        # Check 3: service file exists (2 pts)
        svc_path = f'/etc/systemd/system/{self.timer_name}.service'
        if os.path.isfile(svc_path):
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=True,
                points=2,
                message=f"Service file exists at {svc_path}",
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Service file not found: {svc_path}",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 4. CreateMonotonicTimerTask (medium / 10pts) [PERSIST] ==============

@TaskRegistry.register("systemd_timers")
class CreateMonotonicTimerTask(BaseTask):
    """Create a repeating monotonic timer using OnUnitActiveSec=."""

    def __init__(self):
        super().__init__(
            id="timer_monotonic_001",
            category="systemd_timers",
            difficulty="medium",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'systemd', 'timer', 'monotonic', 'persistence']
        self.exam_tips = [
            "OnUnitActiveSec= fires repeatedly, relative to the last time the unit was activated.",
            "Pair with OnBootSec= to get the first trigger after boot, then repeat.",
            "These are monotonic (relative) timers -- they do NOT use real-time calendar specs.",
        ]
        self.timer_name = None
        self.command = None
        self.interval = None

    def generate(self, **params):
        self.timer_name = params.get('timer_name', f'repeat-{random.choice(["monitor", "poll", "sweep", "ping"])}')
        self.command = params.get('command', random.choice([
            '/usr/local/bin/system-monitor.sh',
            '/usr/local/bin/service-poll.sh',
            '/usr/local/bin/cache-sweep.sh',
            '/usr/local/bin/health-ping.sh',
        ]))
        self.interval = params.get('interval', random.choice(_ONUNIT_ACTIVE_INTERVALS))

        svc = f'{self.timer_name}.service'
        tmr = f'{self.timer_name}.timer'

        self.description = (
            f"Create a repeating monotonic systemd timer:\n"
            f"  - Timer: {tmr}\n"
            f"  - Service: {svc}\n"
            f"  - Command: {self.command}\n"
            f"  - Repeat interval: {self.interval} (OnUnitActiveSec=)\n"
            f"  - Also fire once on boot (OnBootSec={self.interval})\n"
            f"  - Enable and start the timer"
        )

        self.hints = [
            f"Timer file [Timer]: OnBootSec={self.interval}, OnUnitActiveSec={self.interval}",
            f"Service file [Service]: Type=oneshot, ExecStart={self.command}",
            f"Timer file [Install]: WantedBy=timers.target",
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: timer file has OnUnitActiveSec (5 pts)
        onunit_ok = False
        if os.path.isfile(tmr_path):
            try:
                with open(tmr_path, 'r') as fh:
                    content = fh.read()
                if 'OnUnitActiveSec=' in content:
                    onunit_ok = True
            except Exception:
                pass

        if onunit_ok:
            checks.append(ValidationCheck(
                name="onunitactivesec_present",
                passed=True,
                points=5,
                message=f"Timer file contains OnUnitActiveSec= directive",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="onunitactivesec_present",
                passed=False,
                points=0,
                max_points=5,
                message=f"Timer file missing or OnUnitActiveSec= not found",
            ))

        # Check 2: timer is enabled (3 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=3,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=3,
                message=f"Timer '{tmr_unit}' is not enabled",
            ))

        # Check 3: service file exists (2 pts)
        svc_path = f'/etc/systemd/system/{self.timer_name}.service'
        if os.path.isfile(svc_path):
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=True,
                points=2,
                message=f"Service file exists at {svc_path}",
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Service file not found: {svc_path}",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 5. ListActiveTimersTask (easy / 5pts) ===============================

@TaskRegistry.register("systemd_timers")
class ListActiveTimersTask(BaseTask):
    """List active systemd timers and save the output."""

    def __init__(self):
        super().__init__(
            id="timer_list_001",
            category="systemd_timers",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = False
        self.tags = ['v10-new', 'systemd', 'timer', 'diagnostics']
        self.exam_tips = [
            "'systemctl list-timers' shows next trigger time for every active timer.",
            "Add --all to include inactive timers as well.",
        ]
        self.output_file = None

    def generate(self, **params):
        self.output_file = params.get(
            'output', f'/tmp/active-timers-{random.randint(100, 999)}.txt'
        )

        self.description = (
            f"List all active systemd timers:\n"
            f"  - Use the appropriate systemctl command to list timers\n"
            f"  - Save the output to: {self.output_file}\n"
            f"  - The file should include next-trigger and last-trigger columns"
        )

        self.hints = [
            "systemctl list-timers",
            "systemctl list-timers --all",
            f"systemctl list-timers --all > {self.output_file}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: output file exists and contains timer-related data
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=3,
                message=f"Output file exists at {self.output_file}",
            ))
            total_points += 3

            try:
                with open(self.output_file, 'r') as fh:
                    content = fh.read()
                # systemctl list-timers output contains ".timer" entries
                has_timer_data = '.timer' in content or 'NEXT' in content or 'timers listed' in content
                if has_timer_data and len(content.strip()) > 10:
                    checks.append(ValidationCheck(
                        name="output_has_timer_data",
                        passed=True,
                        points=2,
                        message="Output file contains timer listing data",
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="output_has_timer_data",
                        passed=False,
                        points=0,
                        max_points=2,
                        message="Output file does not appear to contain timer listing data",
                    ))
            except Exception as exc:
                checks.append(ValidationCheck(
                    name="output_has_timer_data",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Could not read output file: {exc}",
                ))
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Output file not found: {self.output_file}",
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 6. EnableTimerTask (exam / 12pts) [PERSIST] =========================

@TaskRegistry.register("systemd_timers")
class EnableTimerTask(BaseTask):
    """Enable and start an existing systemd timer."""

    def __init__(self):
        super().__init__(
            id="timer_enable_001",
            category="systemd_timers",
            difficulty="exam",
            points=12,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'systemd', 'timer', 'enable', 'persistence']
        self.exam_tips = [
            "Use 'systemctl enable --now <name>.timer' to enable and start in one step.",
            "The exam WILL reboot -- if you only start without enable you lose points.",
            "Verify with 'systemctl is-enabled <name>.timer' and 'systemctl list-timers'.",
        ]
        self.timer_name = None

    def generate(self, **params):
        # Pick a well-known timer that typically ships with RHEL 10
        well_known_timers = [
            'fstrim',
            'logrotate',
            'dnf-makecache',
            'systemd-tmpfiles-clean',
        ]
        self.timer_name = params.get('timer_name', random.choice(well_known_timers))
        tmr_unit = f'{self.timer_name}.timer'

        self.description = (
            f"Enable and start the '{tmr_unit}' systemd timer:\n"
            f"  - Ensure the timer is enabled to start at boot\n"
            f"  - Ensure the timer is currently active (started)\n"
            f"  - This must survive a reboot"
        )

        self.hints = [
            f"systemctl enable --now {tmr_unit}",
            f"systemctl is-enabled {tmr_unit}",
            f"systemctl is-active {tmr_unit}",
            f"systemctl list-timers | grep {self.timer_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: timer is enabled (6 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=6,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=6,
                message=f"Timer '{tmr_unit}' is not enabled (got: {result.stdout.strip()})",
            ))

        # Check 2: timer is active (6 pts)
        result = execute_safe(['systemctl', 'is-active', tmr_unit])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="timer_active",
                passed=True,
                points=6,
                message=f"Timer '{tmr_unit}' is active",
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="timer_active",
                passed=False,
                points=0,
                max_points=6,
                message=f"Timer '{tmr_unit}' is not active (got: {result.stdout.strip()})",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 7. ConvertCronToTimerTask (hard / 18pts) [PERSIST] ==================

@TaskRegistry.register("systemd_timers")
class ConvertCronToTimerTask(BaseTask):
    """Convert a cron expression into an equivalent systemd timer."""

    def __init__(self):
        super().__init__(
            id="timer_cron_convert_001",
            category="systemd_timers",
            difficulty="hard",
            points=18,
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'systemd', 'timer', 'cron', 'conversion', 'persistence']
        self.exam_tips = [
            "Map cron fields (min hour dom month dow) to OnCalendar= syntax.",
            "Cron '*/5 * * * *' becomes OnCalendar=*-*-* *:00/5:00 (every 5 minutes).",
            "Cron '0 2 * * *' becomes OnCalendar=*-*-* 02:00:00 (daily at 2am).",
            "Use 'systemd-analyze calendar <expr>' to verify your OnCalendar spec.",
        ]
        self.timer_name = None
        self.command = None
        self.cron_expression = None
        self.oncalendar_equivalent = None
        self.cron_desc = None

    def generate(self, **params):
        self.timer_name = params.get('timer_name', f'converted-cron-{random.randint(10, 99)}')
        self.command = params.get('command', '/usr/local/bin/migrated-task.sh')

        mapping = params.get('mapping', random.choice(_CRON_TO_ONCALENDAR))
        self.cron_expression = mapping[0]
        self.oncalendar_equivalent = mapping[1]
        self.cron_desc = mapping[2]

        svc = f'{self.timer_name}.service'
        tmr = f'{self.timer_name}.timer'

        self.description = (
            f"Convert the following cron job to a systemd timer:\n"
            f"  - Cron expression: {self.cron_expression}  ({self.cron_desc})\n"
            f"  - Command: {self.command}\n"
            f"  - Create timer: {tmr}\n"
            f"  - Create service: {svc}\n"
            f"  - Expected OnCalendar equivalent: {self.oncalendar_equivalent}\n"
            f"  - Place files in /etc/systemd/system/\n"
            f"  - Enable and start the timer"
        )

        self.hints = [
            f"Cron '{self.cron_expression}' maps to OnCalendar={self.oncalendar_equivalent}",
            "Cron fields: minute hour day-of-month month day-of-week",
            "OnCalendar: DayOfWeek Year-Month-Day Hour:Minute:Second",
            f"Create /etc/systemd/system/{svc} with ExecStart={self.command}",
            f"Create /etc/systemd/system/{tmr} with OnCalendar={self.oncalendar_equivalent}",
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        svc_path = f'/etc/systemd/system/{self.timer_name}.service'
        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: service file exists with command (4 pts)
        svc_ok = False
        if os.path.isfile(svc_path):
            try:
                with open(svc_path, 'r') as fh:
                    content = fh.read()
                if self.command in content:
                    svc_ok = True
            except Exception:
                pass

        if svc_ok:
            checks.append(ValidationCheck(
                name="service_file_correct",
                passed=True,
                points=4,
                message=f"Service file exists with correct ExecStart",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_file_correct",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service file missing or ExecStart incorrect",
            ))

        # Check 2: timer file exists with approximately correct OnCalendar (6 pts)
        tmr_ok = False
        if os.path.isfile(tmr_path):
            try:
                with open(tmr_path, 'r') as fh:
                    content = fh.read()
                # Accept exact match or close equivalents
                if self.oncalendar_equivalent in content or 'OnCalendar=' in content:
                    tmr_ok = True
            except Exception:
                pass

        if tmr_ok:
            checks.append(ValidationCheck(
                name="oncalendar_correct",
                passed=True,
                points=6,
                message=f"Timer file has OnCalendar= schedule (expected: {self.oncalendar_equivalent})",
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="oncalendar_correct",
                passed=False,
                points=0,
                max_points=6,
                message=f"Timer file missing or no OnCalendar= found",
            ))

        # Check 3: timer is enabled (4 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not enabled",
            ))

        # Check 4: timer is active (4 pts)
        result = execute_safe(['systemctl', 'is-active', tmr_unit])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="timer_active",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is active",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not active",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 8. TroubleshootTimerTask (hard / 15pts) =============================

@TaskRegistry.register("systemd_timers")
class TroubleshootTimerTask(BaseTask):
    """Diagnose why a systemd timer is not firing."""

    def __init__(self):
        super().__init__(
            id="timer_troubleshoot_001",
            category="systemd_timers",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = False
        self.tags = ['v10-new', 'systemd', 'timer', 'troubleshooting']
        self.exam_tips = [
            "Check 'systemctl status <name>.timer' for errors.",
            "Verify the matching .service unit exists and is not failed.",
            "Ensure 'systemctl daemon-reload' was run after creating/editing units.",
            "Use 'journalctl -u <name>.timer' and 'journalctl -u <name>.service'.",
            "Confirm the timer is enabled AND started.",
        ]
        self.timer_name = None
        self.command = None
        self.scenario = None

    def generate(self, **params):
        self.timer_name = params.get('timer_name', random.choice(_TIMER_NAMES))
        self.command = params.get('command', '/usr/local/bin/maintenance.sh')

        scenarios = [
            {
                'id': 'missing_service',
                'desc': 'the matching .service unit file is missing',
                'hint': 'Create the .service file in /etc/systemd/system/',
            },
            {
                'id': 'timer_not_enabled',
                'desc': 'the timer unit is not enabled or started',
                'hint': 'Run systemctl enable --now <name>.timer',
            },
            {
                'id': 'bad_oncalendar',
                'desc': 'the OnCalendar= expression is invalid',
                'hint': 'Use systemd-analyze calendar to verify the expression',
            },
            {
                'id': 'no_daemon_reload',
                'desc': 'systemd has not been reloaded after file changes',
                'hint': 'Run systemctl daemon-reload, then restart the timer',
            },
        ]

        self.scenario = params.get('scenario', random.choice(scenarios))

        tmr_unit = f'{self.timer_name}.timer'

        self.description = (
            f"The systemd timer '{tmr_unit}' is not firing as expected.\n"
            f"  - Likely cause: {self.scenario['desc']}\n"
            f"  - Diagnose the issue and fix it\n"
            f"  - The timer must be enabled, active, and its service unit must exist\n"
            f"  - Command the service should run: {self.command}"
        )

        self.hints = [
            f"systemctl status {tmr_unit}",
            f"systemctl status {self.timer_name}.service",
            f"journalctl -u {tmr_unit}",
            self.scenario['hint'],
            "systemctl daemon-reload",
            f"systemctl enable --now {tmr_unit}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        svc_path = f'/etc/systemd/system/{self.timer_name}.service'
        tmr_path = f'/etc/systemd/system/{self.timer_name}.timer'
        tmr_unit = f'{self.timer_name}.timer'

        # Check 1: timer file exists (3 pts)
        if os.path.isfile(tmr_path):
            checks.append(ValidationCheck(
                name="timer_file_exists",
                passed=True,
                points=3,
                message=f"Timer file exists: {tmr_path}",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="timer_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Timer file not found: {tmr_path}",
            ))

        # Check 2: service file exists (3 pts)
        if os.path.isfile(svc_path):
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=True,
                points=3,
                message=f"Service file exists: {svc_path}",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="service_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Service file not found: {svc_path}",
            ))

        # Check 3: timer is enabled (4 pts)
        result = execute_safe(['systemctl', 'is-enabled', tmr_unit])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=True,
                points=4,
                message=f"Timer '{tmr_unit}' is enabled",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="timer_enabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timer '{tmr_unit}' is not enabled (got: {result.stdout.strip()})",
            ))

        # Check 4: timer is active (5 pts)
        result = execute_safe(['systemctl', 'is-active', tmr_unit])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="timer_active",
                passed=True,
                points=5,
                message=f"Timer '{tmr_unit}' is active and running",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="timer_active",
                passed=False,
                points=0,
                max_points=5,
                message=f"Timer '{tmr_unit}' is not active",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
