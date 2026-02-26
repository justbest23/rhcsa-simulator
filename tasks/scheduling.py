"""
Task scheduling tasks for RHCSA EX200 v10 exam (cron, at).
Systemd timers are in systemd_timers.py.
"""

import random
import os
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("scheduling")
class CreateCronJobTask(BaseTask):
    """Create a user cron job."""

    def __init__(self):
        super().__init__(
            id="sched_cron_001",
            category="scheduling",
            difficulty="exam",
            points=10
        )
        self.requires_persistence = True
        self.tags = ['exam-seen']
        self.exam_tips = [
            "Cron format: minute hour day-of-month month day-of-week command",
            "Use crontab -e to edit, crontab -l to verify",
            "Common: */5 = every 5, 0 2 = at 2:00 AM",
        ]
        self.username = None
        self.command = None
        self.schedule = None
        self.schedule_desc = None

    def generate(self, **params):
        """Generate cron job task."""
        self.username = params.get('username', 'root')

        schedules = [
            ('0 2 * * *', 'daily at 2:00 AM'),
            ('*/15 * * * *', 'every 15 minutes'),
            ('0 */6 * * *', 'every 6 hours'),
            ('0 0 * * 0', 'weekly on Sunday at midnight'),
            ('30 1 * * 1-5', 'weekdays at 1:30 AM'),
        ]

        commands = [
            '/usr/bin/backup.sh',
            '/usr/local/bin/cleanup.sh',
            'echo "Scheduled task" >> /tmp/cronlog.txt',
        ]

        if params.get('schedule'):
            self.schedule = params['schedule']
            self.schedule_desc = params.get('schedule_desc', self.schedule)
        else:
            self.schedule, self.schedule_desc = random.choice(schedules)

        self.command = params.get('command', random.choice(commands))

        self.description = (
            f"Create a cron job:\n"
            f"  - User: {self.username}\n"
            f"  - Schedule: {self.schedule_desc}\n"
            f"  - Cron expression: {self.schedule}\n"
            f"  - Command: {self.command}\n"
            f"  - Use crontab command to configure"
        )

        self.hints = [
            f"Edit crontab: crontab -e (for current user) or crontab -e -u {self.username}",
            f"Add line: {self.schedule} {self.command}",
            "Cron format: minute hour day month weekday command",
            f"Verify: crontab -l -u {self.username}",
            "* means 'every'",
            "*/15 means 'every 15th'"
        ]

        return self

    def validate(self):
        """Validate cron job exists."""
        checks = []
        total_points = 0

        # Check if crontab entry exists
        result = execute_safe(['crontab', '-l', '-u', self.username])
        if result.success and result.stdout.strip():
            found = False
            for entry in result.stdout.split('\n'):
                entry = entry.strip()
                if not entry or entry.startswith('#'):
                    continue
                if self.command in entry:
                    if self.schedule in entry:
                        found = True
                        checks.append(ValidationCheck(
                            name="cron_entry_exact",
                            passed=True,
                            points=10,
                            message=f"Cron job correctly configured with exact schedule"
                        ))
                        total_points += 10
                        break
                    else:
                        checks.append(ValidationCheck(
                            name="cron_entry_partial",
                            passed=True,
                            points=5,
                            message=f"Command found but schedule may differ (partial credit)"
                        ))
                        total_points += 5
                        found = True
                        break

            if not found:
                checks.append(ValidationCheck(
                    name="cron_entry",
                    passed=False,
                    points=0,
                    max_points=10,
                    message=f"Cron job not found in crontab for user {self.username}"
                ))
        else:
            checks.append(ValidationCheck(
                name="crontab_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"No crontab found for user {self.username}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class CreateSystemCronTask(BaseTask):
    """Create a system-wide cron job in /etc/cron.d/."""

    def __init__(self):
        super().__init__(
            id="sched_system_cron_001",
            category="scheduling",
            difficulty="medium",
            points=12
        )
        self.requires_persistence = True
        self.tags = ['v10-new']
        self.exam_tips = [
            "System cron files go in /etc/cron.d/",
            "System cron format includes the user field: min hour day month weekday user command",
            "Files must be owned by root and have 644 permissions",
        ]
        self.job_name = None
        self.command = None
        self.schedule = None
        self.user = None

    def generate(self, **params):
        """Generate system cron task."""
        self.job_name = params.get('job_name', f'custom-job-{random.randint(1,99)}')
        self.user = params.get('user', 'root')
        self.schedule = params.get('schedule', '0 3 * * *')
        self.command = params.get('command', '/usr/local/bin/maintenance.sh')

        self.description = (
            f"Create a system-wide cron job:\n"
            f"  - Job name: {self.job_name}\n"
            f"  - File: /etc/cron.d/{self.job_name}\n"
            f"  - Run as user: {self.user}\n"
            f"  - Schedule: {self.schedule}\n"
            f"  - Command: {self.command}\n"
            f"  - Configure in /etc/cron.d/ (not user crontab)"
        )

        self.hints = [
            f"Create file: /etc/cron.d/{self.job_name}",
            f"Format: {self.schedule} {self.user} {self.command}",
            "System cron format: min hour day month weekday user command",
            f"Permissions: chmod 644 /etc/cron.d/{self.job_name}",
            "No need to restart cron service"
        ]

        return self

    def validate(self):
        """Validate system cron job."""
        checks = []
        total_points = 0

        import os

        cron_file = f'/etc/cron.d/{self.job_name}'

        # Check 1: File exists (4 points)
        if os.path.exists(cron_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=4,
                message=f"Cron file exists at {cron_file}"
            ))
            total_points += 4

            # Check 2: Contains command (4 points)
            if validate_file_contains(cron_file, self.command):
                checks.append(ValidationCheck(
                    name="command_present",
                    passed=True,
                    points=4,
                    message=f"Command found in cron file"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="command_present",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Command not found in {cron_file}"
                ))

            # Check 3: Contains user (2 points)
            if validate_file_contains(cron_file, self.user):
                checks.append(ValidationCheck(
                    name="user_specified",
                    passed=True,
                    points=2,
                    message=f"User '{self.user}' specified in cron file"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="user_specified",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"User not found in {cron_file}"
                ))

            # Check 4: Contains schedule (2 points)
            if validate_file_contains(cron_file, self.schedule):
                checks.append(ValidationCheck(
                    name="schedule_correct",
                    passed=True,
                    points=2,
                    message=f"Schedule configured correctly"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="schedule_correct",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Schedule not found in {cron_file}"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Cron file {cron_file} not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class CreateAtJobTask(BaseTask):
    """Schedule a one-time task with at command."""

    def __init__(self):
        super().__init__(
            id="sched_at_001",
            category="scheduling",
            difficulty="easy",
            points=8
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "Use 'at' for one-time scheduled tasks",
            "Ensure atd service is running: systemctl start atd",
            "View pending jobs: atq",
            "Remove a job: atrm <job_number>",
        ]
        self.time_spec = None
        self.command = None

    def generate(self, **params):
        """Generate at job task."""
        time_specs = [
            ('now + 1 hour', 'in 1 hour'),
            ('now + 30 minutes', 'in 30 minutes'),
            ('tomorrow', 'tomorrow at current time'),
            ('16:00', 'today at 4:00 PM'),
        ]

        if params.get('time'):
            self.time_spec = params['time']
            time_desc = params.get('time_desc', self.time_spec)
        else:
            self.time_spec, time_desc = random.choice(time_specs)

        self.command = params.get('command', 'echo "At job executed" >> /tmp/atjob.log')

        self.description = (
            f"Schedule a one-time task:\n"
            f"  - Time: {time_desc}\n"
            f"  - At spec: {self.time_spec}\n"
            f"  - Command: {self.command}\n"
            f"  - Use the 'at' command"
        )

        self.hints = [
            f"Schedule with at: echo '{self.command}' | at {self.time_spec}",
            "Or use: at {time} <<< '{command}'",
            "View scheduled jobs: atq",
            "View job details: at -c <job_number>",
            "Remove job: atrm <job_number>",
            "Ensure atd service is running: systemctl status atd"
        ]

        return self

    def validate(self):
        """Validate at job is scheduled."""
        checks = []
        total_points = 0

        # Check if atd service is running (3 points)
        result = execute_safe(['systemctl', 'is-active', 'atd'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="atd_running",
                passed=True,
                points=3,
                message=f"atd service is running"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="atd_running",
                passed=False,
                points=0,
                max_points=3,
                message=f"atd service is not running"
            ))

        # Check if there are any at jobs scheduled (5 points)
        result = execute_safe(['atq'])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck(
                name="at_jobs_exist",
                passed=True,
                points=5,
                message=f"At job(s) scheduled ({len(result.stdout.strip().split('\\n'))} job(s))"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="at_jobs_exist",
                passed=False,
                points=0,
                max_points=5,
                message=f"No at jobs scheduled"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class ListCronJobsTask(BaseTask):
    """List and save cron jobs for a user."""

    def __init__(self):
        super().__init__(
            id="sched_list_cron_001",
            category="scheduling",
            difficulty="easy",
            points=6
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "crontab -l lists user cron jobs",
            "Also check /etc/cron.d/, /etc/cron.daily/, /etc/crontab",
        ]
        self.username = None
        self.output_file = None

    def generate(self, **params):
        self.username = params.get('user', 'root')
        self.output_file = params.get('output', '/tmp/cron_jobs.txt')

        self.description = (
            f"List cron jobs for a user:\n"
            f"  - User: {self.username}\n"
            f"  - Save all cron jobs to: {self.output_file}\n"
            f"  - Include any system cron jobs if applicable"
        )

        self.hints = [
            f"List user crontab: crontab -l -u {self.username}",
            f"Save to file: crontab -l -u {self.username} > {self.output_file}",
            "Also check: /etc/cron.d/, /etc/cron.daily/, etc.",
            "System cron: /etc/crontab"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: Output file exists
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=6,
                message=f"Output file created"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class CronExpressionTask(BaseTask):
    """Write correct cron expression from description."""

    def __init__(self):
        super().__init__(
            id="sched_cron_expr_001",
            category="scheduling",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = True
        self.tags = ['exam-seen']
        self.exam_tips = [
            "Cron fields: minute(0-59) hour(0-23) day(1-31) month(1-12) weekday(0-7)",
            "*/N means every N units, 1-5 means Monday through Friday",
            "Practice converting descriptions to cron expressions",
        ]
        self.cron_expression = None
        self.description_text = None
        self.username = None
        self.command = None

    def generate(self, **params):
        expressions = [
            ('*/5 * * * *', 'every 5 minutes', '/usr/local/bin/check_health.sh'),
            ('0 2 * * *', 'every day at 2:00 AM', '/usr/local/bin/backup.sh'),
            ('0 0 * * 0', 'every Sunday at midnight', '/usr/local/bin/weekly_report.sh'),
            ('30 8 1 * *', 'at 8:30 AM on the 1st of every month', '/usr/local/bin/monthly_audit.sh'),
            ('0 */4 * * *', 'every 4 hours', '/usr/local/bin/sync_data.sh'),
            ('0 9 * * 1-5', 'at 9:00 AM on weekdays', '/usr/local/bin/workday_task.sh'),
        ]
        self.cron_expression, self.description_text, self.command = random.choice(expressions)
        self.username = params.get('user', 'root')

        self.description = (
            f"Create a cron job with the correct schedule:\n"
            f"  - User: {self.username}\n"
            f"  - Schedule: {self.description_text}\n"
            f"  - Command: {self.command}\n"
            f"  - Write the correct cron expression and add it to the user's crontab"
        )
        self.hints = [
            "Cron format: minute hour day-of-month month day-of-week",
            f"Expected: {self.cron_expression} {self.command}",
            "*/N = every N units, 0 = at zero, 1-5 = Monday-Friday",
            f"Edit: crontab -e -u {self.username}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['crontab', '-l', '-u', self.username])
        if result.success:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if self.command in line:
                    if self.cron_expression in line:
                        checks.append(ValidationCheck("cron_exact", True, 12, "Correct cron expression"))
                        total_points = 12
                    else:
                        checks.append(ValidationCheck("cron_partial", True, 6, "Command found but schedule differs"))
                        total_points = 6
                    break
            else:
                checks.append(ValidationCheck("cron_missing", False, 0, "Command not found in crontab", max_points=12))
        else:
            checks.append(ValidationCheck("no_crontab", False, 0, f"No crontab for {self.username}", max_points=12))
        return ValidationResult(self.id, total_points >= 8, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class DenyCronAccessTask(BaseTask):
    """Restrict cron access for specific users."""

    def __init__(self):
        super().__init__(
            id="sched_cron_deny_001",
            category="scheduling",
            difficulty="medium",
            points=8
        )
        self.requires_persistence = True
        self.tags = ['v10-new']
        self.exam_tips = [
            "/etc/cron.allow takes precedence over /etc/cron.deny",
            "If cron.allow exists, only listed users can use cron",
            "If only cron.deny exists, listed users are blocked",
        ]
        self.username = None
        self.method = None

    def generate(self, **params):
        self.username = params.get('user', f'user{random.randint(1, 99)}')
        self.method = params.get('method', random.choice(['deny', 'allow']))

        if self.method == 'deny':
            self.description = (
                f"Deny cron access for user {self.username}:\n"
                f"  - Add {self.username} to /etc/cron.deny\n"
                f"  - Verify the user cannot create cron jobs"
            )
        else:
            self.description = (
                f"Allow only specific users to use cron:\n"
                f"  - Create /etc/cron.allow with user {self.username}\n"
                f"  - Only users in cron.allow can use crontab"
            )
        self.hints = [
            f"Deny: echo '{self.username}' >> /etc/cron.deny",
            "Allow: create /etc/cron.allow with allowed usernames",
            "cron.allow takes precedence over cron.deny",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        if self.method == 'deny':
            result = execute_safe(['grep', self.username, '/etc/cron.deny'])
            if result.success:
                checks.append(ValidationCheck("cron_deny", True, 8, f"{self.username} in /etc/cron.deny"))
                total_points = 8
            else:
                checks.append(ValidationCheck("cron_deny", False, 0, f"{self.username} not in /etc/cron.deny", max_points=8))
        else:
            result = execute_safe(['grep', self.username, '/etc/cron.allow'])
            if result.success:
                checks.append(ValidationCheck("cron_allow", True, 8, f"{self.username} in /etc/cron.allow"))
                total_points = 8
            else:
                checks.append(ValidationCheck("cron_allow", False, 0, f"/etc/cron.allow missing or user not listed", max_points=8))
        return ValidationResult(self.id, total_points >= 6, total_points, self.points, checks)


@TaskRegistry.register("scheduling")
class ConfigureCronDirTask(BaseTask):
    """Place a script in /etc/cron.daily or similar directory."""

    def __init__(self):
        super().__init__(
            id="sched_cron_dir_001",
            category="scheduling",
            difficulty="medium",
            points=8
        )
        self.requires_persistence = True
        self.tags = ['v10-new']
        self.exam_tips = [
            "Scripts in /etc/cron.daily/ run once per day via anacron",
            "Scripts must be executable (chmod +x) and have a shebang",
            "No file extension needed - anacron uses run-parts",
        ]
        self.cron_dir = None
        self.script_name = None

    def generate(self, **params):
        dirs = [
            ('/etc/cron.daily', 'daily'),
            ('/etc/cron.hourly', 'hourly'),
            ('/etc/cron.weekly', 'weekly'),
        ]
        self.cron_dir, freq = random.choice(dirs)
        self.script_name = params.get('script', random.choice([
            'cleanup-logs', 'backup-config', 'check-disk', 'rotate-data'
        ]))

        self.description = (
            f"Create a {freq} cron task:\n"
            f"  - Place script '{self.script_name}' in {self.cron_dir}/\n"
            f"  - Script should run a simple command (e.g., log rotation)\n"
            f"  - Script must be executable and have #!/bin/bash shebang"
        )
        self.hints = [
            f"Create: vi {self.cron_dir}/{self.script_name}",
            "First line: #!/bin/bash",
            f"Make executable: chmod +x {self.cron_dir}/{self.script_name}",
            "Scripts in cron.daily run once per day via anacron",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        script_path = f'{self.cron_dir}/{self.script_name}'

        result = execute_safe(['test', '-f', script_path])
        if result.success:
            checks.append(ValidationCheck("script_exists", True, 3, "Script exists"))
            total_points += 3
        else:
            checks.append(ValidationCheck("script_exists", False, 0, f"{script_path} not found", max_points=3))
            return ValidationResult(self.id, False, 0, self.points, checks)

        result = execute_safe(['test', '-x', script_path])
        if result.success:
            checks.append(ValidationCheck("executable", True, 3, "Script is executable"))
            total_points += 3
        else:
            checks.append(ValidationCheck("executable", False, 0, "Script not executable", max_points=3))

        result = execute_safe(['head', '-1', script_path])
        if result.success and '#!/bin/bash' in result.stdout:
            checks.append(ValidationCheck("shebang", True, 2, "Has #!/bin/bash shebang"))
            total_points += 2
        else:
            checks.append(ValidationCheck("shebang", False, 0, "Missing shebang", max_points=2))

        return ValidationResult(self.id, total_points >= 5, total_points, self.points, checks)
