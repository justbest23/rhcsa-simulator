"""
Systemd service management tasks for RHCSA EX200 v10 exam.
Covers starting, stopping, enabling, disabling, masking services,
troubleshooting failed services, viewing dependencies, configuring
restart policies, and managing processes.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Common service pools used across multiple tasks
# ---------------------------------------------------------------------------
_STARTABLE_SERVICES = ['httpd', 'nginx', 'sshd', 'chronyd', 'firewalld', 'rsyslog', 'crond']
_STOPPABLE_SERVICES = ['postfix', 'bluetooth', 'cups', 'avahi-daemon', 'kdump']
_MASKABLE_SERVICES = ['cups', 'bluetooth', 'postfix', 'avahi-daemon', 'rpcbind']
_TROUBLESHOOT_SERVICES = ['httpd', 'nginx', 'mariadb', 'named', 'vsftpd']


# ===== 1. StartServiceTask (easy / 5pts) ==================================

@TaskRegistry.register("services")
class StartServiceTask(BaseTask):
    """Start a systemd service (without enabling)."""

    has_setup = True

    def setup_environment(self):
        from tasks import env_setup
        return env_setup.make_service_absent(self.id, self.service_name)

    def __init__(self):
        super().__init__(
            id="svc_start_001",
            category="services",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = False
        self.tags = ["systemctl", "start", "services"]
        self.exam_tips = [
            "systemctl start only starts the service NOW; it does NOT survive reboot.",
            "Always verify with 'systemctl is-active <service>'.",
        ]
        self.service_name = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STARTABLE_SERVICES))

        self.description = (
            f"Start the '{self.service_name}' service so it is currently running.\n"
            f"  - Do NOT enable it at boot (only start it now).\n"
            f"  - Verify the service is in an 'active (running)' state."
        )

        self.hints = [
            f"systemctl start {self.service_name}",
            f"systemctl is-active {self.service_name}",
            f"systemctl status {self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        result = execute_safe(['systemctl', 'is-active', self.service_name])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="service_active",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is running",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_active",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is not running (got: {result.stdout.strip()})",
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 2. EnableServiceTask (easy / 5pts) [PERSIST] =======================

@TaskRegistry.register("services")
class EnableServiceTask(BaseTask):
    """Enable a systemd service at boot."""

    has_setup = True

    def setup_environment(self):
        from tasks import env_setup
        return env_setup.make_service_absent(self.id, self.service_name)

    def __init__(self):
        super().__init__(
            id="svc_enable_001",
            category="services",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = True
        self.tags = ["systemctl", "enable", "boot", "persistence"]
        self.exam_tips = [
            "'systemctl enable' creates symlinks in the target's wants directory.",
            "This survives reboot -- the grader WILL reboot your VM.",
        ]
        self.service_name = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STARTABLE_SERVICES))

        self.description = (
            f"Enable the '{self.service_name}' service to start automatically at boot.\n"
            f"  - Use the appropriate systemctl command.\n"
            f"  - Verify the service is enabled."
        )

        self.hints = [
            f"systemctl enable {self.service_name}",
            f"systemctl is-enabled {self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        result = execute_safe(['systemctl', 'is-enabled', self.service_name])
        if result.success and result.stdout.strip() == 'enabled':
            checks.append(ValidationCheck(
                name="service_enabled",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is enabled at boot",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_enabled",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is not enabled (got: {result.stdout.strip()})",
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 3. StartAndEnableServiceTask (exam / 10pts) [PERSIST] ==============

@TaskRegistry.register("services")
class StartAndEnableServiceTask(BaseTask):
    """Start AND enable a systemd service (the most common exam task)."""

    has_setup = True

    def setup_environment(self):
        from tasks import env_setup
        return env_setup.make_service_absent(self.id, self.service_name)

    def __init__(self):
        super().__init__(
            id="svc_start_enable_001",
            category="services",
            difficulty="exam",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ["systemctl", "enable", "start", "exam-core", "persistence"]
        self.exam_tips = [
            "Use 'systemctl enable --now <service>' to do both in one command.",
            "The exam WILL reboot -- if you only start without enable, you lose points.",
        ]
        self.service_name = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STARTABLE_SERVICES))

        self.description = (
            f"Enable '{self.service_name}' to start now and persistently at every boot."
        )

        self.hints = [
            f"systemctl enable --now {self.service_name}",
            f"systemctl status {self.service_name}",
            f"systemctl is-active {self.service_name}",
            f"systemctl is-enabled {self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is active (5 points)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="service_active",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is running",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_active",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is not running",
            ))

        # Check 2: service is enabled (5 points)
        result = execute_safe(['systemctl', 'is-enabled', self.service_name])
        if result.success and result.stdout.strip() == 'enabled':
            checks.append(ValidationCheck(
                name="service_enabled",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is enabled at boot",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_enabled",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is not enabled at boot",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 4. StopAndDisableServiceTask (medium / 8pts) [PERSIST] =============

@TaskRegistry.register("services")
class StopAndDisableServiceTask(BaseTask):
    """Stop a service and disable it from starting at boot."""

    has_setup = True

    def setup_environment(self):
        from tasks import env_setup
        return env_setup.make_service_present(self.id, self.service_name)

    def __init__(self):
        super().__init__(
            id="svc_stop_disable_001",
            category="services",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = True
        self.tags = ["systemctl", "stop", "disable", "persistence"]
        self.exam_tips = [
            "Use 'systemctl disable --now <service>' to stop and disable in one step.",
            "Verify with both 'is-active' and 'is-enabled'.",
        ]
        self.service_name = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STOPPABLE_SERVICES))

        self.description = (
            f"Configure the '{self.service_name}' service:\n"
            f"  - Stop the service if it is currently running\n"
            f"  - Disable the service so it does NOT start at boot\n"
            f"  - Verify the service is stopped and disabled"
        )

        self.hints = [
            f"systemctl disable --now {self.service_name}",
            f"systemctl is-active {self.service_name}  # should say 'inactive'",
            f"systemctl is-enabled {self.service_name}  # should say 'disabled'",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is inactive (4 points)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        is_inactive = result.stdout.strip() in ('inactive', 'unknown', 'dead')
        if is_inactive or (not result.success):
            checks.append(ValidationCheck(
                name="service_inactive",
                passed=True,
                points=4,
                message=f"Service '{self.service_name}' is stopped",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_inactive",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service '{self.service_name}' is still running (state: {result.stdout.strip()})",
            ))

        # Check 2: service is disabled (4 points)
        result = execute_safe(['systemctl', 'is-enabled', self.service_name])
        is_disabled = result.stdout.strip() in ('disabled', 'masked', 'static', 'not-found')
        if is_disabled or (not result.success):
            checks.append(ValidationCheck(
                name="service_disabled",
                passed=True,
                points=4,
                message=f"Service '{self.service_name}' is disabled at boot",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_disabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service '{self.service_name}' is still enabled (state: {result.stdout.strip()})",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 5. MaskServiceTask (medium / 8pts) [PERSIST] =======================

@TaskRegistry.register("services")
class MaskServiceTask(BaseTask):
    """Mask a service to completely prevent it from being started."""

    def __init__(self):
        super().__init__(
            id="svc_mask_001",
            category="services",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = True
        self.tags = ["systemctl", "mask", "security", "persistence"]
        self.exam_tips = [
            "'systemctl mask' creates a symlink to /dev/null -- the service cannot be started at all.",
            "To undo: 'systemctl unmask <service>'.",
            "Masking is stronger than disabling.",
        ]
        self.service_name = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_MASKABLE_SERVICES))

        self.description = (
            f"Mask the '{self.service_name}' service:\n"
            f"  - Stop the service if it is running\n"
            f"  - Mask the service so it cannot be started by any means\n"
            f"  - Verify the service is masked"
        )

        self.hints = [
            f"systemctl stop {self.service_name}",
            f"systemctl mask {self.service_name}",
            f"systemctl status {self.service_name}  # should show 'masked'",
            f"systemctl is-enabled {self.service_name}  # should say 'masked'",
            f"To undo later: systemctl unmask {self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is masked (5 points)
        result = execute_safe(['systemctl', 'is-enabled', self.service_name])
        if 'masked' in result.stdout.strip():
            checks.append(ValidationCheck(
                name="service_masked",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is masked",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_masked",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is not masked (state: {result.stdout.strip()})",
            ))

        # Check 2: service is not running (3 points)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        is_inactive = result.stdout.strip() in ('inactive', 'unknown', 'dead', 'failed')
        if is_inactive or (not result.success):
            checks.append(ValidationCheck(
                name="service_stopped",
                passed=True,
                points=3,
                message=f"Service '{self.service_name}' is not running",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="service_stopped",
                passed=False,
                points=0,
                max_points=3,
                message=f"Service '{self.service_name}' is still running",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 6. TroubleshootServiceTask (hard / 15pts) ==========================

@TaskRegistry.register("services")
class TroubleshootServiceTask(BaseTask):
    """Diagnose why a service is failing and get it running."""

    def __init__(self):
        super().__init__(
            id="svc_troubleshoot_001",
            category="services",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = False
        self.tags = ["troubleshooting", "systemctl", "journalctl", "diagnostics"]
        self.exam_tips = [
            "Always check: systemctl status <service>, journalctl -xeu <service>",
            "Common failures: wrong ExecStart path, missing dependencies, SELinux denials.",
            "Use 'systemctl list-units --failed' to see all failed units.",
        ]
        self.service_name = None
        self.failure_scenario = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_TROUBLESHOOT_SERVICES))

        scenarios = [
            {
                'id': 'wrong_config',
                'desc': 'configuration file error',
                'hint': 'Check config syntax and journalctl for error messages',
            },
            {
                'id': 'missing_dependency',
                'desc': 'missing dependency or prerequisite',
                'hint': 'Check dependencies with systemctl list-dependencies',
            },
            {
                'id': 'port_conflict',
                'desc': 'port already in use by another process',
                'hint': 'Use ss -tlnp or netstat -tlnp to find port conflicts',
            },
            {
                'id': 'permission_denied',
                'desc': 'file permission or SELinux issue',
                'hint': 'Check /var/log/audit/audit.log and file permissions',
            },
        ]

        self.failure_scenario = params.get('scenario', random.choice(scenarios))

        self.description = (
            f"The '{self.service_name}' service is failing to start.\n"
            f"  - Diagnose the issue (likely: {self.failure_scenario['desc']})\n"
            f"  - Fix the problem\n"
            f"  - Start the service successfully\n"
            f"  - Ensure the service stays running"
        )

        self.hints = [
            f"systemctl status {self.service_name}",
            f"journalctl -xeu {self.service_name}",
            self.failure_scenario['hint'],
            f"After fixing: systemctl restart {self.service_name}",
            f"Verify: systemctl is-active {self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is active (10 points -- primary goal)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="service_running",
                passed=True,
                points=10,
                message=f"Service '{self.service_name}' is running",
            ))
            total_points += 10
        else:
            checks.append(ValidationCheck(
                name="service_running",
                passed=False,
                points=0,
                max_points=10,
                message=f"Service '{self.service_name}' is not running (state: {result.stdout.strip()})",
            ))

        # Check 2: service is not in failed state (5 points)
        result = execute_safe(['systemctl', 'is-failed', self.service_name])
        if result.stdout.strip() != 'failed':
            checks.append(ValidationCheck(
                name="service_not_failed",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' is not in a failed state",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_not_failed",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' is in a failed state",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 7. ListFailedServicesTask (easy / 5pts) ============================

@TaskRegistry.register("services")
class ListFailedServicesTask(BaseTask):
    """List all failed systemd services and save to a file."""

    def __init__(self):
        super().__init__(
            id="svc_list_failed_001",
            category="services",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = False
        self.tags = ["systemctl", "failed", "diagnostics"]
        self.exam_tips = [
            "Use 'systemctl --failed' or 'systemctl list-units --state=failed'.",
            "On the exam, check for failed units EARLY -- they may block other tasks.",
        ]
        self.output_file = None

    def generate(self, **params):
        self.output_file = params.get(
            'output', f'/tmp/failed-services-{random.randint(100, 999)}.txt'
        )

        self.description = (
            f"Identify and record all failed systemd units:\n"
            f"  - List all systemd units that are in a 'failed' state\n"
            f"  - Save the output to: {self.output_file}\n"
            f"  - The file should contain the output of the failed-units listing"
        )

        self.hints = [
            "systemctl --failed",
            "systemctl list-units --state=failed",
            f"systemctl --failed > {self.output_file}",
        ]
        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        # Check: output file exists and has content
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
                if len(content.strip()) > 0:
                    checks.append(ValidationCheck(
                        name="output_has_content",
                        passed=True,
                        points=2,
                        message="Output file contains data",
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="output_has_content",
                        passed=False,
                        points=0,
                        max_points=2,
                        message="Output file is empty",
                    ))
            except Exception as exc:
                checks.append(ValidationCheck(
                    name="output_has_content",
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


# ===== 8. ViewServiceDependenciesTask (medium / 8pts) =====================

@TaskRegistry.register("services")
class ViewServiceDependenciesTask(BaseTask):
    """View and record the dependency tree of a systemd service."""

    def __init__(self):
        super().__init__(
            id="svc_dependencies_001",
            category="services",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = False
        self.tags = ["systemctl", "dependencies", "diagnostics"]
        self.exam_tips = [
            "Use 'systemctl list-dependencies <service>' to see the full tree.",
            "Add --reverse to see what depends ON this service.",
        ]
        self.service_name = None
        self.output_file = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STARTABLE_SERVICES))
        self.output_file = params.get(
            'output', f'/tmp/{self.service_name}-deps-{random.randint(100, 999)}.txt'
        )

        self.description = (
            f"Examine the dependency tree of the '{self.service_name}' service:\n"
            f"  - List all dependencies of {self.service_name}\n"
            f"  - Save the full dependency listing to: {self.output_file}\n"
            f"  - The output should include the complete dependency tree"
        )

        self.hints = [
            f"systemctl list-dependencies {self.service_name}",
            f"systemctl list-dependencies {self.service_name} > {self.output_file}",
            f"For reverse deps: systemctl list-dependencies --reverse {self.service_name}",
            f"systemctl show {self.service_name} -p Requires,Wants,After",
        ]
        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        # Check 1: output file exists (4 points)
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=4,
                message=f"Dependency output file exists",
            ))
            total_points += 4

            # Check 2: file contains meaningful content (4 points)
            try:
                with open(self.output_file, 'r') as fh:
                    content = fh.read()
                # A valid dependency listing will contain ".service" or ".target" or ".slice"
                has_units = any(
                    ext in content for ext in ['.service', '.target', '.socket', '.slice']
                )
                if has_units and len(content.strip()) > 20:
                    checks.append(ValidationCheck(
                        name="valid_dependency_tree",
                        passed=True,
                        points=4,
                        message="File contains a valid dependency listing",
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="valid_dependency_tree",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="File does not appear to contain a valid dependency tree",
                    ))
            except Exception as exc:
                checks.append(ValidationCheck(
                    name="valid_dependency_tree",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not read file: {exc}",
                ))
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Output file not found: {self.output_file}",
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 9. ConfigureServiceRestartTask (hard / 15pts) [PERSIST] =============

@TaskRegistry.register("services")
class ConfigureServiceRestartTask(BaseTask):
    """Create a systemd drop-in override to configure Restart=always."""

    def __init__(self):
        super().__init__(
            id="svc_restart_policy_001",
            category="services",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = True
        self.tags = ["systemctl", "override", "drop-in", "restart-policy", "persistence"]
        self.exam_tips = [
            "Use 'systemctl edit <service>' to create a drop-in override.",
            "Or manually create /etc/systemd/system/<service>.d/override.conf",
            "Always run 'systemctl daemon-reload' after editing unit files.",
            "Restart= options: no, on-success, on-failure, on-abnormal, on-watchdog, on-abort, always",
        ]
        self.service_name = None
        self.restart_policy = None
        self.restart_sec = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_STARTABLE_SERVICES))
        self.restart_policy = params.get('restart_policy', 'always')
        self.restart_sec = params.get('restart_sec', random.choice([5, 10, 15, 30]))

        self.description = (
            f"Configure automatic restart for the '{self.service_name}' service:\n"
            f"  - Create a systemd drop-in override for {self.service_name}\n"
            f"  - Set Restart={self.restart_policy}\n"
            f"  - Set RestartSec={self.restart_sec}\n"
            f"  - Reload systemd and ensure the service is running\n"
            f"  - The override must persist across reboots"
        )

        self.hints = [
            f"mkdir -p /etc/systemd/system/{self.service_name}.service.d",
            f"Create /etc/systemd/system/{self.service_name}.service.d/override.conf",
            f"Contents:\n[Service]\nRestart={self.restart_policy}\nRestartSec={self.restart_sec}",
            "systemctl daemon-reload",
            f"systemctl restart {self.service_name}",
            f"Verify: systemctl show {self.service_name} -p Restart,RestartUSec",
            f"Alternative: systemctl edit {self.service_name}",
        ]
        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        override_dir = f'/etc/systemd/system/{self.service_name}.service.d'
        override_file = os.path.join(override_dir, 'override.conf')

        # Check 1: override directory exists (3 points)
        if os.path.isdir(override_dir):
            checks.append(ValidationCheck(
                name="override_dir_exists",
                passed=True,
                points=3,
                message=f"Drop-in directory exists: {override_dir}",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="override_dir_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Drop-in directory not found: {override_dir}",
            ))

        # Check 2: override.conf exists and contains Restart= (4 points)
        # Also accept any .conf file in the drop-in directory
        found_restart = False
        if os.path.isdir(override_dir):
            for conf_name in os.listdir(override_dir):
                if conf_name.endswith('.conf'):
                    conf_path = os.path.join(override_dir, conf_name)
                    try:
                        with open(conf_path, 'r') as fh:
                            content = fh.read()
                        if f'Restart={self.restart_policy}' in content:
                            found_restart = True
                            break
                    except Exception:
                        continue

        if found_restart:
            checks.append(ValidationCheck(
                name="restart_policy_set",
                passed=True,
                points=4,
                message=f"Restart={self.restart_policy} found in drop-in override",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="restart_policy_set",
                passed=False,
                points=0,
                max_points=4,
                message=f"Restart={self.restart_policy} not found in any drop-in conf",
            ))

        # Check 3: systemd shows the correct restart property (4 points)
        result = execute_safe(['systemctl', 'show', self.service_name, '-p', 'Restart'])
        if result.success and f'Restart={self.restart_policy}' in result.stdout:
            checks.append(ValidationCheck(
                name="restart_effective",
                passed=True,
                points=4,
                message=f"systemd reports Restart={self.restart_policy} (daemon-reload done)",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="restart_effective",
                passed=False,
                points=0,
                max_points=4,
                message=(
                    f"systemd does not report Restart={self.restart_policy} "
                    f"(got: {result.stdout.strip()}). Did you run daemon-reload?"
                ),
            ))

        # Check 4: service is currently active (4 points)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="service_active",
                passed=True,
                points=4,
                message=f"Service '{self.service_name}' is running",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service '{self.service_name}' is not running",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 10. ManageProcessesTask (medium / 8pts) ============================

@TaskRegistry.register("services")
class ManageProcessesTask(BaseTask):
    """Identify and manage processes related to a service."""

    def __init__(self):
        super().__init__(
            id="svc_manage_proc_001",
            category="services",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = False
        self.tags = ["processes", "ps", "pgrep", "kill", "signals"]
        self.exam_tips = [
            "Use 'ps aux | grep <process>' or 'pgrep -a <process>' to find PIDs.",
            "Use 'systemctl status <service>' to see the main PID and cgroup.",
            "kill -HUP <pid> reloads config; kill -TERM <pid> graceful stop.",
        ]
        self.service_name = None
        self.process_name = None

    def generate(self, **params):
        service_process_map = {
            'httpd': 'httpd',
            'nginx': 'nginx',
            'sshd': 'sshd',
            'chronyd': 'chronyd',
            'firewalld': 'firewalld',
            'crond': 'crond',
            'rsyslog': 'rsyslogd',
        }

        self.service_name = params.get('service', random.choice(list(service_process_map.keys())))
        self.process_name = service_process_map.get(self.service_name, self.service_name)

        self.description = (
            f"Manage the '{self.service_name}' service and its processes:\n"
            f"  - Ensure the '{self.service_name}' service is running\n"
            f"  - Identify the main process ID (PID) of '{self.process_name}'\n"
            f"  - Verify the process is visible via ps/pgrep commands\n"
            f"  - The service must remain running after your investigation"
        )

        self.hints = [
            f"systemctl start {self.service_name}",
            f"systemctl status {self.service_name}  # shows Main PID",
            f"pgrep -a {self.process_name}",
            f"ps aux | grep {self.process_name}",
            f"systemctl show {self.service_name} -p MainPID",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is running (4 points)
        result = execute_safe(['systemctl', 'is-active', self.service_name])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="service_active",
                passed=True,
                points=4,
                message=f"Service '{self.service_name}' is running",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service '{self.service_name}' is not running",
            ))

        # Check 2: process is visible via pgrep (4 points)
        result = execute_safe(['pgrep', '-c', self.process_name])
        if result.success and result.stdout.strip().isdigit() and int(result.stdout.strip()) > 0:
            checks.append(ValidationCheck(
                name="process_running",
                passed=True,
                points=4,
                message=f"Process '{self.process_name}' found ({result.stdout.strip()} instance(s))",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="process_running",
                passed=False,
                points=0,
                max_points=4,
                message=f"Process '{self.process_name}' not found via pgrep",
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
