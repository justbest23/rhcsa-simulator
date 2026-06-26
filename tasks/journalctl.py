"""
Journalctl and systemd journal management tasks for RHCSA EX200 v10 exam.
Category: journalctl (4 tasks)

Covers boot log analysis, persistent journal configuration,
unit-based filtering, and journal size management.
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
# 1. BootLogAnalysisTask (medium / 10pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("journalctl")
class BootLogAnalysisTask(BaseTask):
    """Analyze boot logs using journalctl -b to identify boot issues."""

    def __init__(self):
        super().__init__(
            id="journalctl_boot_log_analysis_001",
            category="journalctl",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = False
        self.tags = ['journalctl', 'boot-log', 'troubleshooting']
        self.exam_tips = [
            "journalctl -b 0 shows logs from the current boot.",
            "journalctl -b -1 shows logs from the previous boot (if persistent journal is enabled).",
            "Use -p err to filter only error-level and above messages.",
            "Combine with --no-pager for script-friendly output.",
        ]
        self.output_file = None
        self.priority_filter = None
        self.boot_offset = None

    def generate(self, **params):
        """Generate boot log analysis task with randomized parameters."""
        output_files = [
            '/tmp/boot_errors.log', '/tmp/boot_analysis.log',
            '/tmp/journal_boot_report.txt', '/tmp/boot_issues.txt',
        ]
        self.output_file = params.get('output_file', random.choice(output_files))

        priority_choices = [
            ('err', 'error', 'errors and above (err, crit, alert, emerg)'),
            ('warning', 'warning', 'warnings and above (warning, err, crit, alert, emerg)'),
            ('crit', 'critical', 'critical and above (crit, alert, emerg)'),
        ]
        priority_data = params.get('priority')
        if priority_data:
            self.priority_filter = priority_data
            prio_desc = priority_data
        else:
            self.priority_filter, _, prio_desc = random.choice(priority_choices)

        boot_offsets = [
            (0, 'current boot'),
            (-1, 'previous boot'),
        ]
        self.boot_offset = params.get('boot_offset', random.choice(boot_offsets)[0])
        boot_desc = 'current boot' if self.boot_offset == 0 else 'previous boot'

        self.description = (
            f"Analyze boot logs to identify system issues:\n"
            f"\n"
            f"  1. Use journalctl to view logs from the {boot_desc}\n"
            f"  2. Filter messages by priority: {prio_desc}\n"
            f"  3. Save the filtered output to: {self.output_file}\n"
            f"\n"
            f"  Command to construct:\n"
            f"    journalctl -b {self.boot_offset} -p {self.priority_filter} --no-pager\n"
            f"\n"
            f"  Redirect the output to the file specified above."
        )

        self.hints = [
            f"journalctl -b {self.boot_offset} -p {self.priority_filter} --no-pager > {self.output_file}",
            "journalctl -b 0 = current boot, -b -1 = previous boot",
            f"-p {self.priority_filter} filters by syslog priority level",
            "If previous boot logs are missing, enable persistent journal first",
            "Use --no-pager to disable the pager for redirection",
        ]

        return self

    def validate(self):
        """Validate boot log output file exists and contains relevant data."""
        checks = []
        total_points = 0

        # Check 1: Output file exists (3 points)
        if not os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Output file not found: {self.output_file}"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        checks.append(ValidationCheck(
            name="output_file_exists",
            passed=True,
            points=3,
            message=f"Output file {self.output_file} exists"
        ))
        total_points += 3

        # Check 2: File has content (3 points)
        try:
            file_size = os.path.getsize(self.output_file)
            if file_size > 0:
                checks.append(ValidationCheck(
                    name="file_has_content",
                    passed=True,
                    points=3,
                    message=f"Output file has content ({file_size} bytes)"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="file_has_content",
                    passed=False,
                    points=0,
                    max_points=3,
                    message="Output file is empty - no journal entries matched the filter"
                ))
        except OSError as e:
            checks.append(ValidationCheck(
                name="file_has_content",
                passed=False,
                points=0,
                max_points=3,
                message=f"Cannot read output file: {e}"
            ))

        # Check 3: Content appears to be journal output (4 points)
        try:
            with open(self.output_file, 'r') as f:
                content = f.read(8192)  # Read first 8KB for analysis

            # Journal output typically contains timestamps, hostnames, and unit names
            journal_indicators = [
                'systemd', 'kernel', '.service', 'localhost',
                'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                '-- Boot', '-- Logs begin', 'Subject:',
            ]
            content_lower = content.lower()
            matches = sum(1 for ind in journal_indicators if ind.lower() in content_lower)

            if matches >= 2:
                checks.append(ValidationCheck(
                    name="journal_format",
                    passed=True,
                    points=4,
                    message="Output contains valid journal/log data"
                ))
                total_points += 4
            elif matches >= 1:
                checks.append(ValidationCheck(
                    name="journal_format",
                    passed=True,
                    points=2,
                    message="Output contains some journal data but may be incomplete"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="journal_format",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="Output does not appear to contain journal data"
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="journal_format",
                passed=False,
                points=0,
                max_points=4,
                message=f"Error reading output file: {e}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 2. PersistentJournalTask (exam / 10pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("journalctl")
class PersistentJournalTask(BaseTask):
    """
    Fault-injection: sets Storage=volatile so logs are lost on reboot.
    User must re-enable persistent logging.
    """

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="journalctl_persistent_journal_001",
            category="journalctl",
            difficulty="exam",
            points=10
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'journalctl', 'persistent-journal', 'fault-injection']
        self.exam_tips = [
            "Journal persistence is controlled by Storage= in /etc/systemd/journald.conf.",
            "Storage=persistent: always save to disk.",
            "Storage=auto: saves to disk only if /var/log/journal/ directory exists.",
            "After config changes: systemctl restart systemd-journald",
        ]
        self.storage_setting = None

    def generate(self, **params):
        storage_options = [
            ('persistent', 'Storage=persistent'),
            ('auto', 'Storage=auto'),
        ]
        self.storage_setting, self._target_setting = params.get(
            'storage', random.choice(storage_options)
        ) if isinstance(params.get('storage'), tuple) else random.choice(storage_options)

        self.description = (
            f"Troubleshoot system journal configuration:\n\n"
            f"Symptom: Boot logs are not available from previous reboots.\n"
            f"The systemd journal is not persisting logs to disk.\n\n"
            f"Tasks:\n"
            f"  1. Identify why journal logs are not persisting across reboots\n"
            f"  2. Configure the journal for persistent storage\n"
            f"  3. Restart the journal service to apply the change\n"
            f"  4. Verify: journalctl --list-boots shows entries"
        )
        self.hints = [
            "Check current config: cat /etc/systemd/journald.conf | grep -i storage",
            "Journal config file: /etc/systemd/journald.conf  (section: [Journal])",
            "Verify persistence directory: ls -ld /var/log/journal",
            "Apply change: systemctl restart systemd-journald",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        import shutil

        # Save original journald.conf
        conf = '/etc/systemd/journald.conf'
        backup = '/var/lib/rhcsa-simulator/journald.conf.bak'
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        if not os.path.exists(conf):
            os.makedirs(os.path.dirname(conf), exist_ok=True)
            with open(conf, 'w') as f:
                f.write('[Journal]\n# Storage=auto\n')
        shutil.copy2(conf, backup)

        # Remove /var/log/journal to break persistence
        journal_dir = '/var/log/journal'
        had_dir = os.path.isdir(journal_dir)
        if had_dir:
            shutil.rmtree(journal_dir)

        # Set Storage=volatile in journald.conf
        with open(conf) as f:
            content = f.read()
        import re
        content = re.sub(r'(?m)^#?Storage=.*$', 'Storage=volatile', content)
        if 'Storage=' not in content:
            content = content.replace('[Journal]', '[Journal]\nStorage=volatile')
        with open(conf, 'w') as f:
            f.write(content)

        _sp.run(['systemctl', 'restart', 'systemd-journald'], capture_output=True)

        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {
            'backup': backup,
            'had_dir': had_dir,
            'target_setting': self._target_setting,
        })
        return True, "Set Storage=volatile and removed /var/log/journal"

    def restore_fault(self):
        import subprocess as _sp
        import shutil
        from tasks.troubleshooting import load_fault_state, clear_fault_state

        state = load_fault_state()
        info = state.get('restore_info', {}) if state else {}
        backup = info.get('backup', '/var/lib/rhcsa-simulator/journald.conf.bak')
        had_dir = info.get('had_dir', True)
        journal_dir = '/var/log/journal'

        if os.path.exists(backup):
            shutil.copy2(backup, '/etc/systemd/journald.conf')
            os.remove(backup)

        if had_dir and not os.path.isdir(journal_dir):
            os.makedirs(journal_dir, exist_ok=True)
            _sp.run(['chown', 'root:systemd-journal', journal_dir], capture_output=True)
            _sp.run(['chmod', '2755', journal_dir], capture_output=True)

        _sp.run(['systemctl', 'restart', 'systemd-journald'], capture_output=True)
        clear_fault_state()
        return True, "Restored journald.conf and restarted systemd-journald"

    def validate(self):
        """Validate persistent journal is properly configured."""
        checks = []
        total_points = 0

        # Check 1: /var/log/journal directory exists (3 points)
        journal_dir = '/var/log/journal'
        if os.path.isdir(journal_dir):
            checks.append(ValidationCheck(
                name="journal_dir_exists",
                passed=True,
                points=3,
                message=f"{journal_dir} directory exists"
            ))
            total_points += 3

            # Verify ownership and permissions
            result = execute_safe(['stat', '--format=%U:%G %a', journal_dir])
            if result.success:
                stat_info = result.stdout.strip()
                perm_ok = 'systemd-journal' in stat_info
                if perm_ok:
                    checks[len(checks) - 1].details = f"Permissions: {stat_info}"
        else:
            checks.append(ValidationCheck(
                name="journal_dir_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"{journal_dir} directory does not exist. Run: mkdir -p {journal_dir}"
            ))

        # Check 2: journald.conf has correct Storage setting (4 points)
        journald_conf = '/etc/systemd/journald.conf'
        storage_configured = False
        storage_value_found = None

        if os.path.exists(journald_conf):
            try:
                with open(journald_conf, 'r') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith('#') or not stripped:
                            continue
                        if stripped.lower().startswith('storage='):
                            storage_value_found = stripped.split('=', 1)[1].strip().lower()
                            break

                if self.storage_setting == 'persistent':
                    storage_configured = (storage_value_found == 'persistent')
                elif self.storage_setting == 'auto':
                    # auto is valid, and also if Storage=auto or persistent is set
                    storage_configured = storage_value_found in ('auto', 'persistent')

                # Also accept: Storage=auto with /var/log/journal existing
                if not storage_configured and os.path.isdir(journal_dir):
                    if storage_value_found == 'auto' or (
                        storage_value_found is None and os.path.isdir(journal_dir)
                    ):
                        # Default behavior with directory present counts
                        storage_configured = True

            except Exception as e:
                logger.warning(f"Error reading {journald_conf}: {e}")

        if storage_configured:
            checks.append(ValidationCheck(
                name="storage_setting",
                passed=True,
                points=4,
                message=f"journald.conf Storage setting is correctly configured (found: {storage_value_found})"
            ))
            total_points += 4
        else:
            if storage_value_found:
                msg = f"Storage={storage_value_found} found, expected Storage={self.storage_setting}"
            else:
                msg = f"No active Storage= setting found in {journald_conf}"
            checks.append(ValidationCheck(
                name="storage_setting",
                passed=False,
                points=0,
                max_points=4,
                message=msg
            ))

        # Check 3: Journal service is running and journal data exists (3 points)
        result = execute_safe(['systemctl', 'is-active', 'systemd-journald'])
        journald_active = result.success and 'active' in result.stdout.strip()

        # Check if persistent journal data files exist
        journal_has_data = False
        if os.path.isdir(journal_dir):
            result = execute_safe(['ls', '-A', journal_dir])
            if result.success and result.stdout.strip():
                journal_has_data = True

        if journald_active and journal_has_data:
            checks.append(ValidationCheck(
                name="journal_active_and_data",
                passed=True,
                points=3,
                message="systemd-journald is active and persistent journal data exists"
            ))
            total_points += 3
        elif journald_active:
            checks.append(ValidationCheck(
                name="journal_active_and_data",
                passed=True,
                points=2,
                max_points=3,
                message=(
                    "systemd-journald is active but no persistent data found yet. "
                    "Try: systemctl restart systemd-journald"
                )
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="journal_active_and_data",
                passed=False,
                points=0,
                max_points=3,
                message="systemd-journald is not active or no journal data in /var/log/journal"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 3. FilterJournalByUnitTask (easy / 6pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("journalctl")
class FilterJournalByUnitTask(BaseTask):
    """Filter systemd journal output by a specific service unit."""

    def __init__(self):
        super().__init__(
            id="journalctl_filter_by_unit_001",
            category="journalctl",
            difficulty="easy",
            points=6
        )
        self.requires_persistence = False
        self.tags = ['journalctl', 'filtering', 'units']
        self.exam_tips = [
            "journalctl -u <unit> filters by systemd unit name.",
            "You can combine -u with time filters: --since '1 hour ago'.",
            "Use tab completion: journalctl -u ssh<TAB> to find unit names.",
            "Multiple units: journalctl -u sshd -u httpd shows logs from both.",
        ]
        self.unit_name = None
        self.output_file = None

    def generate(self, **params):
        """Generate journal filtering task with randomized service unit."""
        services = [
            ('sshd.service', 'SSH daemon', 'remote access logs'),
            ('crond.service', 'cron daemon', 'scheduled task execution logs'),
            ('chronyd.service', 'chrony NTP', 'time synchronization logs'),
            ('firewalld.service', 'firewalld', 'firewall management logs'),
            ('NetworkManager.service', 'NetworkManager', 'network configuration logs'),
            ('systemd-logind.service', 'systemd login manager', 'user session logs'),
            ('auditd.service', 'audit daemon', 'security audit logs'),
            ('rsyslog.service', 'rsyslog', 'traditional syslog forwarding logs'),
            ('tuned.service', 'tuned', 'system performance tuning logs'),
            ('httpd.service', 'Apache HTTP server', 'web server access and error logs'),
        ]

        if params.get('unit'):
            self.unit_name = params['unit']
            unit_desc = params.get('unit_desc', 'the specified service')
            log_desc = params.get('log_desc', 'service logs')
        else:
            self.unit_name, unit_desc, log_desc = random.choice(services)

        output_files = [
            f'/tmp/{self.unit_name.replace(".service", "")}_journal.log',
            f'/tmp/journal_{self.unit_name.replace(".service", "")}.txt',
        ]
        self.output_file = params.get('output_file', random.choice(output_files))

        self.description = (
            f"Filter the systemd journal by a specific unit:\n"
            f"\n"
            f"  Service: {self.unit_name} ({unit_desc})\n"
            f"  Purpose: Extract {log_desc}\n"
            f"\n"
            f"  Tasks:\n"
            f"  1. Use journalctl -u to view logs for {self.unit_name}\n"
            f"  2. Save the output to: {self.output_file}\n"
            f"\n"
            f"  The output file should contain journal entries for the specified unit."
        )

        self.hints = [
            f"journalctl -u {self.unit_name} --no-pager > {self.output_file}",
            "journalctl -u <unit> shows all logs for that systemd unit",
            f"Add --since 'today' to limit to today's logs only",
            f"Use -n 50 to show only the last 50 entries",
            "If no output, the service may not have run yet - start it first",
        ]

        return self

    def validate(self):
        """Validate journal output file for the specified unit."""
        checks = []
        total_points = 0

        # Check 1: Output file exists (2 points)
        if not os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Output file not found: {self.output_file}"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        checks.append(ValidationCheck(
            name="output_file_exists",
            passed=True,
            points=2,
            message=f"Output file {self.output_file} exists"
        ))
        total_points += 2

        # Check 2: File contains relevant unit data (4 points)
        try:
            with open(self.output_file, 'r') as f:
                content = f.read(16384)  # First 16KB

            # Derive the unit base name for matching (e.g., sshd from sshd.service)
            unit_base = self.unit_name.replace('.service', '')
            content_lower = content.lower()
            unit_base_lower = unit_base.lower()

            # Check for journal-style content referencing the unit
            has_unit_reference = (
                unit_base_lower in content_lower or
                self.unit_name.lower() in content_lower
            )

            # Check for journal formatting indicators
            journal_markers = ['-- logs begin', '-- boot', 'systemd', unit_base_lower]
            has_journal_format = sum(
                1 for m in journal_markers if m in content_lower
            ) >= 1

            if has_unit_reference and has_journal_format:
                checks.append(ValidationCheck(
                    name="unit_logs_present",
                    passed=True,
                    points=4,
                    message=f"Output contains journal entries for {self.unit_name}"
                ))
                total_points += 4
            elif has_unit_reference or has_journal_format:
                checks.append(ValidationCheck(
                    name="unit_logs_present",
                    passed=True,
                    points=2,
                    message=f"Output contains some data related to {self.unit_name}"
                ))
                total_points += 2
            elif len(content.strip()) > 0:
                # File has content but doesn't clearly match the unit
                # It might be a "No entries" message or wrong unit
                if 'no entries' in content_lower:
                    checks.append(ValidationCheck(
                        name="unit_logs_present",
                        passed=False,
                        points=1,
                        max_points=4,
                        message=(
                            f"Journal reported 'no entries' for {self.unit_name}. "
                            f"The service may not have generated logs yet."
                        )
                    ))
                    total_points += 1
                else:
                    checks.append(ValidationCheck(
                        name="unit_logs_present",
                        passed=False,
                        points=0,
                        max_points=4,
                        message=f"Output does not appear to contain logs for {self.unit_name}"
                    ))
            else:
                checks.append(ValidationCheck(
                    name="unit_logs_present",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="Output file is empty"
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="unit_logs_present",
                passed=False,
                points=0,
                max_points=4,
                message=f"Error reading output file: {e}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 4. JournalSizeManagementTask (medium / 8pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("journalctl")
class JournalSizeManagementTask(BaseTask):
    """Configure journal size limits in journald.conf."""

    def __init__(self):
        super().__init__(
            id="journalctl_size_management_001",
            category="journalctl",
            difficulty="medium",
            points=8
        )
        self.requires_persistence = False
        self.tags = ['journalctl', 'disk-management', 'journald-conf']
        self.exam_tips = [
            "SystemMaxUse= controls the maximum disk space for persistent journal.",
            "RuntimeMaxUse= controls the maximum memory for volatile journal.",
            "After changing journald.conf, restart: systemctl restart systemd-journald.",
            "Use journalctl --disk-usage to check current journal size.",
            "journalctl --vacuum-size=100M trims existing logs to 100MB.",
        ]
        self.max_size = None
        self.runtime_max = None

    def generate(self, **params):
        """Generate journal size management task with randomized limits."""
        size_options = [
            ('100M', '100 megabytes'),
            ('200M', '200 megabytes'),
            ('500M', '500 megabytes'),
            ('1G', '1 gigabyte'),
            ('50M', '50 megabytes'),
            ('256M', '256 megabytes'),
        ]
        runtime_options = [
            ('50M', '50 megabytes'),
            ('100M', '100 megabytes'),
            ('64M', '64 megabytes'),
            ('128M', '128 megabytes'),
        ]

        if params.get('max_size'):
            self.max_size = params['max_size']
            size_desc = params.get('max_size', self.max_size)
        else:
            self.max_size, size_desc = random.choice(size_options)

        if params.get('runtime_max'):
            self.runtime_max = params['runtime_max']
            runtime_desc = params.get('runtime_max', self.runtime_max)
        else:
            self.runtime_max, runtime_desc = random.choice(runtime_options)

        self.description = (
            f"Configure systemd journal size limits:\n"
            f"\n"
            f"  Edit /etc/systemd/journald.conf to set the following:\n"
            f"\n"
            f"  1. SystemMaxUse={self.max_size}\n"
            f"     (Maximum disk space for persistent journal: {size_desc})\n"
            f"\n"
            f"  2. RuntimeMaxUse={self.runtime_max}\n"
            f"     (Maximum memory for volatile journal: {runtime_desc})\n"
            f"\n"
            f"  After editing:\n"
            f"  3. Restart the journal service: systemctl restart systemd-journald\n"
            f"  4. Verify with: journalctl --disk-usage\n"
            f"\n"
            f"  This prevents the journal from consuming excessive disk space."
        )

        self.hints = [
            "Edit /etc/systemd/journald.conf (under [Journal] section)",
            f"Add or uncomment: SystemMaxUse={self.max_size}",
            f"Add or uncomment: RuntimeMaxUse={self.runtime_max}",
            "Make sure the lines are NOT commented out (no leading #)",
            "systemctl restart systemd-journald",
            "journalctl --disk-usage shows current disk usage",
            "journalctl --vacuum-size=<size> trims existing logs",
        ]

        return self

    def validate(self):
        """Validate journal size settings in journald.conf."""
        checks = []
        total_points = 0
        journald_conf = '/etc/systemd/journald.conf'

        if not os.path.exists(journald_conf):
            checks.append(ValidationCheck(
                name="journald_conf_exists",
                passed=False,
                points=0,
                max_points=8,
                message=f"{journald_conf} not found"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        try:
            with open(journald_conf, 'r') as f:
                config_lines = f.readlines()
        except Exception as e:
            checks.append(ValidationCheck(
                name="journald_conf_readable",
                passed=False,
                points=0,
                max_points=8,
                message=f"Cannot read {journald_conf}: {e}"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Parse active (non-commented) settings
        active_settings = {}
        for line in config_lines:
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith(';') or not stripped:
                continue
            if '=' in stripped:
                key, value = stripped.split('=', 1)
                active_settings[key.strip().lower()] = value.strip()

        # Check 1: SystemMaxUse is set correctly (4 points)
        system_max = active_settings.get('systemmaxuse', None)
        if system_max and system_max.upper() == self.max_size.upper():
            checks.append(ValidationCheck(
                name="system_max_use",
                passed=True,
                points=4,
                message=f"SystemMaxUse={self.max_size} is correctly set"
            ))
            total_points += 4
        elif system_max:
            checks.append(ValidationCheck(
                name="system_max_use",
                passed=False,
                points=1,
                max_points=4,
                message=(
                    f"SystemMaxUse={system_max} found, expected {self.max_size}. "
                    f"Check the value in {journald_conf}"
                )
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="system_max_use",
                passed=False,
                points=0,
                max_points=4,
                message=(
                    f"SystemMaxUse not set in {journald_conf}. "
                    f"Add 'SystemMaxUse={self.max_size}' under [Journal]"
                )
            ))

        # Check 2: RuntimeMaxUse is set correctly (3 points)
        runtime_max = active_settings.get('runtimemaxuse', None)
        if runtime_max and runtime_max.upper() == self.runtime_max.upper():
            checks.append(ValidationCheck(
                name="runtime_max_use",
                passed=True,
                points=3,
                message=f"RuntimeMaxUse={self.runtime_max} is correctly set"
            ))
            total_points += 3
        elif runtime_max:
            checks.append(ValidationCheck(
                name="runtime_max_use",
                passed=False,
                points=1,
                max_points=3,
                message=f"RuntimeMaxUse={runtime_max} found, expected {self.runtime_max}"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="runtime_max_use",
                passed=False,
                points=0,
                max_points=3,
                message=(
                    f"RuntimeMaxUse not set in {journald_conf}. "
                    f"Add 'RuntimeMaxUse={self.runtime_max}' under [Journal]"
                )
            ))

        # Check 3: systemd-journald service is active (1 point)
        result = execute_safe(['systemctl', 'is-active', 'systemd-journald'])
        if result.success and 'active' in result.stdout.strip():
            checks.append(ValidationCheck(
                name="journald_running",
                passed=True,
                points=1,
                message="systemd-journald is running (restart may be needed to apply changes)"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="journald_running",
                passed=False,
                points=0,
                max_points=1,
                message="systemd-journald is not running. Run: systemctl restart systemd-journald"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
