"""
Boot and system target tasks for RHCSA exam.
"""

import os
import random
import logging
import subprocess
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import (
    get_default_target, validate_default_target,
    get_grub_timeout, validate_grub_timeout,
    get_grub_cmdline, validate_grub_parameter,
    validate_grub_parameter_value, is_grub_config_updated
)
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


@TaskRegistry.register("boot")
class SetDefaultTargetTask(BaseTask):
    """Set systemd default boot target."""

    def __init__(self):
        super().__init__(
            id="boot_target_001",
            category="boot",
            difficulty="easy",
            points=5
        )
        self.target = None

    def generate(self, **params):
        """Generate target change task."""
        targets = [
            ('multi-user.target', 'multi-user (no GUI)'),
            ('graphical.target', 'graphical (GUI)'),
        ]

        choice = params.get('target')
        if choice:
            self.target = choice
            target_desc = next((desc for t, desc in targets if t == choice), choice)
        else:
            self.target, target_desc = random.choice(targets)

        self.description = (
            f"Configure the system boot target:\n"
            f"  - Set the default systemd target to {target_desc}\n"
            f"  - Target: {self.target}\n"
            f"  - Ensure the change persists across reboots"
        )

        self.hints = [
            "Use 'systemctl set-default <target>' to change default target",
            "Use 'systemctl get-default' to verify the current target",
            "Common targets: multi-user.target, graphical.target",
            "You can also use 'systemctl isolate <target>' to switch immediately"
        ]

        return self

    def validate(self):
        """Validate default target setting."""
        checks = []
        total_points = 0

        current_target = get_default_target()

        if current_target == self.target:
            checks.append(ValidationCheck(
                name="default_target",
                passed=True,
                points=5,
                message=f"Default target is correctly set to '{self.target}'"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="default_target",
                passed=False,
                points=0,
                max_points=5,
                message=f"Default target is '{current_target}', expected '{self.target}'"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class ModifyGrubTimeoutTask(BaseTask):
    """Modify GRUB boot menu timeout."""

    def __init__(self):
        super().__init__(
            id="boot_grub_timeout_001",
            category="boot",
            difficulty="medium",
            points=8
        )
        self.timeout = None

    def generate(self, **params):
        """Generate GRUB timeout modification task."""
        self.timeout = params.get('timeout', random.choice([3, 5, 10, 15]))

        self.description = (
            f"Configure the GRUB bootloader:\n"
            f"  - Set the boot menu timeout to {self.timeout} seconds\n"
            f"  - Edit /etc/default/grub\n"
            f"  - Regenerate the GRUB configuration\n"
            f"  - Changes must persist across reboots"
        )

        self.hints = [
            "Edit /etc/default/grub and modify GRUB_TIMEOUT",
            "After editing, run 'grub2-mkconfig -o /boot/grub2/grub.cfg'",
            "On UEFI systems, use '/boot/efi/EFI/redhat/grub.cfg'",
            "Verify changes with 'grep GRUB_TIMEOUT /etc/default/grub'"
        ]

        return self

    def validate(self):
        """Validate GRUB timeout configuration."""
        checks = []
        total_points = 0

        # Check 1: Timeout in /etc/default/grub (4 points)
        current_timeout = get_grub_timeout()
        if current_timeout == self.timeout:
            checks.append(ValidationCheck(
                name="grub_timeout_set",
                passed=True,
                points=4,
                message=f"GRUB timeout correctly set to {self.timeout} seconds"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_timeout_set",
                passed=False,
                points=0,
                max_points=4,
                message=f"GRUB timeout is {current_timeout}, expected {self.timeout}"
            ))

        # Check 2: GRUB config regenerated (4 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_config_exists",
                passed=True,
                points=4,
                message="GRUB configuration file exists"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_config_exists",
                passed=False,
                points=0,
                max_points=4,
                message="GRUB configuration not found or not regenerated"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class AddKernelParameterTask(BaseTask):
    """Add a kernel boot parameter via GRUB."""

    def __init__(self):
        super().__init__(
            id="boot_kernel_param_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.parameter = None
        self.parameter_desc = None

    def generate(self, **params):
        """Generate kernel parameter addition task."""
        parameters = [
            ('quiet', 'suppress most boot messages'),
            ('rhgb', 'Red Hat graphical boot'),
            ('rd.break', 'break into emergency shell'),
            ('systemd.unit=multi-user.target', 'boot to multi-user target'),
        ]

        if params.get('parameter'):
            self.parameter = params.get('parameter')
            self.parameter_desc = params.get('description', 'the specified parameter')
        else:
            self.parameter, self.parameter_desc = random.choice(parameters)

        self.description = (
            f"Configure kernel boot parameters:\n"
            f"  - Add '{self.parameter}' to the kernel command line\n"
            f"  - Purpose: {self.parameter_desc}\n"
            f"  - Edit /etc/default/grub (GRUB_CMDLINE_LINUX)\n"
            f"  - Regenerate GRUB configuration\n"
            f"  - Changes must persist across reboots"
        )

        self.hints = [
            "Edit /etc/default/grub",
            f"Add '{self.parameter}' to GRUB_CMDLINE_LINUX line",
            "Separate parameters with spaces",
            "Run 'grub2-mkconfig -o /boot/grub2/grub.cfg' to apply",
            "Verify with 'grep GRUB_CMDLINE_LINUX /etc/default/grub'"
        ]

        return self

    def validate(self):
        """Validate kernel parameter is added."""
        checks = []
        total_points = 0

        # Check if parameter contains '='
        if '=' in self.parameter:
            param_name, param_value = self.parameter.split('=', 1)
            param_exists = validate_grub_parameter_value(param_name, param_value)
        else:
            param_exists = validate_grub_parameter(self.parameter)

        # Check 1: Parameter in GRUB_CMDLINE_LINUX (6 points)
        if param_exists:
            checks.append(ValidationCheck(
                name="kernel_param_added",
                passed=True,
                points=6,
                message=f"Kernel parameter '{self.parameter}' added successfully"
            ))
            total_points += 6
        else:
            current_cmdline = get_grub_cmdline()
            checks.append(ValidationCheck(
                name="kernel_param_added",
                passed=False,
                points=0,
                max_points=6,
                message=f"Parameter '{self.parameter}' not found in GRUB_CMDLINE_LINUX. Current: {current_cmdline}"
            ))

        # Check 2: GRUB config exists (4 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=True,
                points=4,
                message="GRUB configuration updated"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=False,
                points=0,
                max_points=4,
                message="GRUB configuration needs to be regenerated"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class RemoveKernelParameterTask(BaseTask):
    """Remove a kernel boot parameter from GRUB."""

    def __init__(self):
        super().__init__(
            id="boot_kernel_param_remove_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.parameter = None

    def generate(self, **params):
        """Generate kernel parameter removal task."""
        parameters = ['quiet', 'rhgb', 'splash']
        self.parameter = params.get('parameter', random.choice(parameters))

        self.description = (
            f"Configure kernel boot parameters:\n"
            f"  - Remove '{self.parameter}' from the kernel command line\n"
            f"  - Edit /etc/default/grub (GRUB_CMDLINE_LINUX)\n"
            f"  - Regenerate GRUB configuration\n"
            f"  - Changes must persist across reboots"
        )

        self.hints = [
            "Edit /etc/default/grub",
            f"Remove '{self.parameter}' from GRUB_CMDLINE_LINUX line",
            "Be careful not to remove other parameters",
            "Run 'grub2-mkconfig -o /boot/grub2/grub.cfg' to apply",
            "Verify with 'grep GRUB_CMDLINE_LINUX /etc/default/grub'"
        ]

        return self

    def validate(self):
        """Validate kernel parameter is removed."""
        checks = []
        total_points = 0

        param_exists = validate_grub_parameter(self.parameter)

        # Check 1: Parameter removed from GRUB_CMDLINE_LINUX (6 points)
        if not param_exists:
            checks.append(ValidationCheck(
                name="kernel_param_removed",
                passed=True,
                points=6,
                message=f"Kernel parameter '{self.parameter}' removed successfully"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="kernel_param_removed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Parameter '{self.parameter}' still present in GRUB_CMDLINE_LINUX"
            ))

        # Check 2: GRUB config regenerated (4 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=True,
                points=4,
                message="GRUB configuration updated"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=False,
                points=0,
                max_points=4,
                message="GRUB configuration needs to be regenerated"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class BootTroubleshootingTask(BaseTask):
    """Boot troubleshooting scenario task."""

    def __init__(self):
        super().__init__(
            id="boot_troubleshoot_001",
            category="boot",
            difficulty="exam",
            points=12
        )
        self.target = 'multi-user.target'
        self.timeout = 5

    def generate(self, **params):
        """Generate boot troubleshooting task."""
        scenarios = [
            {
                'description': 'System boots to graphical interface but should boot to text mode',
                'target': 'multi-user.target',
                'timeout': 5
            },
            {
                'description': 'System boots to text mode but should have GUI',
                'target': 'graphical.target',
                'timeout': 10
            }
        ]

        scenario = params.get('scenario', random.choice(scenarios))
        self.target = scenario['target']
        self.timeout = scenario['timeout']
        scenario_desc = scenario['description']

        self.description = (
            f"Boot Configuration Task:\n"
            f"  Scenario: {scenario_desc}\n"
            f"  \n"
            f"  Required changes:\n"
            f"  - Set default target to: {self.target}\n"
            f"  - Set GRUB timeout to: {self.timeout} seconds\n"
            f"  - Regenerate GRUB configuration\n"
            f"  - All changes must persist across reboots"
        )

        self.hints = [
            "Use 'systemctl set-default <target>' for boot target",
            "Edit /etc/default/grub for GRUB settings",
            "Run 'grub2-mkconfig -o /boot/grub2/grub.cfg'",
            "Verify with 'systemctl get-default' and check /etc/default/grub"
        ]

        return self

    def validate(self):
        """Validate boot troubleshooting solution."""
        checks = []
        total_points = 0

        # Check 1: Default target (5 points)
        if validate_default_target(self.target):
            checks.append(ValidationCheck(
                name="target_fixed",
                passed=True,
                points=5,
                message=f"Default target correctly set to {self.target}"
            ))
            total_points += 5
        else:
            current = get_default_target()
            checks.append(ValidationCheck(
                name="target_fixed",
                passed=False,
                points=0,
                max_points=5,
                message=f"Target is {current}, expected {self.target}"
            ))

        # Check 2: GRUB timeout (4 points)
        if validate_grub_timeout(self.timeout):
            checks.append(ValidationCheck(
                name="timeout_fixed",
                passed=True,
                points=4,
                message=f"GRUB timeout correctly set to {self.timeout} seconds"
            ))
            total_points += 4
        else:
            current = get_grub_timeout()
            checks.append(ValidationCheck(
                name="timeout_fixed",
                passed=False,
                points=0,
                max_points=4,
                message=f"Timeout is {current}, expected {self.timeout}"
            ))

        # Check 3: GRUB config regenerated (3 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_regenerated",
                passed=True,
                points=3,
                message="GRUB configuration regenerated"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="grub_regenerated",
                passed=False,
                points=0,
                max_points=3,
                message="GRUB configuration not regenerated"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class EmergencyBootTask(BaseTask):
    """Emergency boot and rescue mode knowledge task."""

    def __init__(self):
        super().__init__(
            id="boot_emergency_001",
            category="boot",
            difficulty="exam",
            points=8
        )
        self.target = None

    def generate(self, **params):
        """Generate emergency boot configuration task."""
        self.target = params.get('target', 'emergency.target')

        self.description = (
            f"Configure system for emergency boot scenario:\n"
            f"  - Understand how to boot into emergency mode\n"
            f"  - Know the difference between rescue and emergency targets\n"
            f"  \n"
            f"  For this task:\n"
            f"  - Ensure the system can boot normally (default target set)\n"
            f"  - Document: To boot into emergency mode, add 'systemd.unit=emergency.target'\n"
            f"  - Document: To boot into rescue mode, add 'systemd.unit=rescue.target'\n"
            f"  \n"
            f"  Verify your current default target is set correctly"
        )

        self.hints = [
            "Emergency mode: minimal environment, root filesystem mounted read-only",
            "Rescue mode: more services than emergency, network may be available",
            "At GRUB menu, press 'e' to edit boot parameters temporarily",
            "Add systemd.unit=emergency.target to kernel line for emergency mode",
            "Use 'systemctl get-default' to check current default target"
        ]

        return self

    def validate(self):
        """Validate system can boot normally."""
        checks = []
        total_points = 0

        current_target = get_default_target()

        # Check: System has a valid default target (not emergency/rescue)
        valid_targets = ['multi-user.target', 'graphical.target']

        if current_target in valid_targets:
            checks.append(ValidationCheck(
                name="normal_boot_configured",
                passed=True,
                points=8,
                message=f"System configured for normal boot: {current_target}"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="normal_boot_configured",
                passed=False,
                points=0,
                max_points=8,
                message=f"Default target is {current_target}, should be multi-user or graphical"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class AnalyzeBootTimeTask(BaseTask):
    """Analyze system boot time and identify slow services."""

    def __init__(self):
        super().__init__(
            id="boot_analyze_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.output_file = "/tmp/boot_analysis.txt"

    def generate(self, **params):
        """Generate boot analysis task."""
        self.output_file = params.get('output_file', "/tmp/boot_analysis.txt")

        self.description = (
            f"Analyze system boot performance:\n"
            f"  1. Use systemd-analyze to get total boot time\n"
            f"  2. Identify the 5 slowest services using systemd-analyze blame\n"
            f"  3. Write the output to: {self.output_file}\n"
            f"  \n"
            f"  The file should contain:\n"
            f"  - Total boot time (from 'systemd-analyze')\n"
            f"  - Top 5 slowest services (from 'systemd-analyze blame')"
        )

        self.hints = [
            "Run 'systemd-analyze' to see total boot time",
            "Run 'systemd-analyze blame' to see service startup times",
            "Use 'systemd-analyze blame | head -5' for top 5 slowest",
            "Redirect output with '>' or '>>'",
            "You can also try 'systemd-analyze critical-chain' for dependency chain"
        ]

        return self

    def validate(self):
        """Validate boot analysis output."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=2,
                message=f"Output file {self.output_file} exists"
            ))
            total_points += 2

            # Read file content
            try:
                with open(self.output_file, 'r') as f:
                    content = f.read().lower()

                # Check 2: Contains boot time info (4 points)
                has_boot_time = any(x in content for x in ['startup finished', 'kernel', 'userspace', 'graphical.target', 'multi-user.target'])
                if has_boot_time:
                    checks.append(ValidationCheck(
                        name="boot_time_recorded",
                        passed=True,
                        points=4,
                        message="Boot time information recorded"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="boot_time_recorded",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Missing boot time information (run systemd-analyze)"
                    ))

                # Check 3: Contains service blame info (4 points)
                has_services = any(x in content for x in ['.service', 'ms', 'min', 's '])
                if has_services:
                    checks.append(ValidationCheck(
                        name="services_listed",
                        passed=True,
                        points=4,
                        message="Service startup times recorded"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="services_listed",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Missing service blame info (run systemd-analyze blame)"
                    ))

            except Exception as e:
                checks.append(ValidationCheck(
                    name="file_readable",
                    passed=False,
                    points=0,
                    max_points=8,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"Output file {self.output_file} not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class ValidateFstabTask(BaseTask):
    """Validate fstab configuration and fix errors."""

    def __init__(self):
        super().__init__(
            id="boot_fstab_001",
            category="boot",
            difficulty="medium",
            points=10
        )

    def generate(self, **params):
        """Generate fstab validation task."""
        self.description = (
            f"Validate the /etc/fstab configuration:\n"
            f"  1. Use 'findmnt --verify' to check for fstab errors\n"
            f"  2. Ensure there are no syntax errors or invalid entries\n"
            f"  3. Use 'mount -a' to verify all entries can be mounted\n"
            f"  \n"
            f"  Note: A broken fstab can prevent system boot!\n"
            f"  Always verify fstab changes before rebooting."
        )

        self.hints = [
            "'findmnt --verify' checks fstab syntax without mounting",
            "'findmnt --verify --verbose' shows more details",
            "'mount -a' attempts to mount all fstab entries",
            "Check that all devices/UUIDs in fstab actually exist",
            "Ensure mount points exist before adding to fstab"
        ]

        return self

    def validate(self):
        """Validate fstab is correct."""
        checks = []
        total_points = 0

        # Check 1: fstab exists (2 points)
        if os.path.exists('/etc/fstab'):
            checks.append(ValidationCheck(
                name="fstab_exists",
                passed=True,
                points=2,
                message="/etc/fstab exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="fstab_exists",
                passed=False,
                points=0,
                max_points=2,
                message="/etc/fstab not found!"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: findmnt --verify passes (4 points)
        result = execute_safe(['findmnt', '--verify'])
        if result.success:
            checks.append(ValidationCheck(
                name="fstab_syntax_valid",
                passed=True,
                points=4,
                message="fstab syntax is valid (findmnt --verify passed)"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="fstab_syntax_valid",
                passed=False,
                points=0,
                max_points=4,
                message=f"fstab has errors: {result.stderr or result.stdout}"
            ))

        # Check 3: mount -a succeeds (4 points)
        result = execute_safe(['mount', '-a'])
        if result.success:
            checks.append(ValidationCheck(
                name="mount_all_succeeds",
                passed=True,
                points=4,
                message="All fstab entries can be mounted (mount -a passed)"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="mount_all_succeeds",
                passed=False,
                points=0,
                max_points=4,
                message=f"mount -a failed: {result.stderr}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class RebuildInitramfsTask(BaseTask):
    """Rebuild initramfs using dracut."""

    def __init__(self):
        super().__init__(
            id="boot_initramfs_001",
            category="boot",
            difficulty="medium",
            points=8
        )

    def generate(self, **params):
        """Generate initramfs rebuild task."""
        self.description = (
            f"Rebuild the initramfs (initial RAM filesystem):\n"
            f"  1. List current kernel versions with 'uname -r'\n"
            f"  2. Rebuild initramfs for current kernel using dracut\n"
            f"  3. Verify the initramfs was updated\n"
            f"  \n"
            f"  When to rebuild initramfs:\n"
            f"  - After adding new kernel modules\n"
            f"  - After changing boot configuration\n"
            f"  - After modifying /etc/dracut.conf"
        )

        self.hints = [
            "'uname -r' shows current kernel version",
            "'dracut -f' rebuilds initramfs for current kernel",
            "'dracut -f /boot/initramfs-$(uname -r).img $(uname -r)' explicit rebuild",
            "'lsinitrd' lists contents of initramfs",
            "Check /boot/ for initramfs files: ls -la /boot/initramfs*"
        ]

        return self

    def validate(self):
        """Validate initramfs exists and is recent."""
        checks = []
        total_points = 0

        # Get current kernel version
        result = execute_safe(['uname', '-r'])
        if not result.success:
            checks.append(ValidationCheck(
                name="kernel_version",
                passed=False,
                points=0,
                max_points=8,
                message="Could not determine kernel version"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        kernel_version = result.stdout.strip()
        initramfs_path = f"/boot/initramfs-{kernel_version}.img"

        # Check 1: initramfs exists (4 points)
        if os.path.exists(initramfs_path):
            checks.append(ValidationCheck(
                name="initramfs_exists",
                passed=True,
                points=4,
                message=f"initramfs exists: {initramfs_path}"
            ))
            total_points += 4

            # Check 2: initramfs is readable/valid (4 points)
            result = execute_safe(['lsinitrd', initramfs_path, '--list'])
            if result.success:
                checks.append(ValidationCheck(
                    name="initramfs_valid",
                    passed=True,
                    points=4,
                    message="initramfs is valid and readable"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="initramfs_valid",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="initramfs may be corrupted"
                ))
        else:
            checks.append(ValidationCheck(
                name="initramfs_exists",
                passed=False,
                points=0,
                max_points=8,
                message=f"initramfs not found: {initramfs_path}"
            ))

        passed = total_points >= (self.points * 0.5)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class ResetRootPasswordProcedureTask(BaseTask):
    """Document the root password reset procedure."""

    def __init__(self):
        super().__init__(
            id="boot_password_reset_001",
            category="boot",
            difficulty="exam",
            points=15
        )
        self.output_file = "/tmp/password_reset_procedure.txt"

    def generate(self, **params):
        """Generate password reset documentation task."""
        self.output_file = params.get('output_file', "/tmp/password_reset_procedure.txt")

        self.description = (
            f"Document the root password reset procedure:\n"
            f"  \n"
            f"  This is a CRITICAL RHCSA skill. You cannot actually perform\n"
            f"  this in the simulator, but you MUST know the steps.\n"
            f"  \n"
            f"  Write the complete procedure to: {self.output_file}\n"
            f"  \n"
            f"  Your documentation must include:\n"
            f"  1. How to interrupt the boot process (GRUB)\n"
            f"  2. The kernel parameter to add (rd.break)\n"
            f"  3. How to remount sysroot read-write\n"
            f"  4. How to chroot into the system\n"
            f"  5. How to change the password\n"
            f"  6. SELinux relabeling step\n"
            f"  7. How to exit and continue boot"
        )

        self.hints = [
            "At GRUB menu, press 'e' to edit boot entry",
            "Add 'rd.break' to the end of the linux line",
            "Press Ctrl+X to boot with modified parameters",
            "mount -o remount,rw /sysroot",
            "chroot /sysroot",
            "passwd root",
            "touch /.autorelabel",
            "exit twice to continue boot"
        ]

        return self

    def validate(self):
        """Validate password reset procedure documentation."""
        checks = []
        total_points = 0

        if not os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=15,
                message=f"Documentation file not found: {self.output_file}"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        try:
            with open(self.output_file, 'r') as f:
                content = f.read().lower()

            # Check for key steps
            step_checks = [
                ('grub_edit', ['grub', 'press e', 'edit'], 2, "GRUB edit step"),
                ('rd_break', ['rd.break', 'rd break'], 3, "rd.break parameter"),
                ('remount', ['remount', 'mount -o', 'rw /sysroot', 'remount,rw'], 2, "Remount sysroot"),
                ('chroot', ['chroot', '/sysroot'], 2, "Chroot into sysroot"),
                ('passwd', ['passwd', 'password'], 2, "Password change command"),
                ('selinux', ['autorelabel', 'touch /', 'selinux', '.autorelabel'], 3, "SELinux relabel"),
                ('exit', ['exit', 'reboot', 'ctrl+x', 'ctrl-x'], 1, "Exit/continue boot"),
            ]

            for check_name, keywords, points, description in step_checks:
                found = any(kw in content for kw in keywords)
                if found:
                    checks.append(ValidationCheck(
                        name=check_name,
                        passed=True,
                        points=points,
                        message=f"✓ {description} documented"
                    ))
                    total_points += points
                else:
                    checks.append(ValidationCheck(
                        name=check_name,
                        passed=False,
                        points=0,
                        max_points=points,
                        message=f"✗ Missing: {description}"
                    ))

        except Exception as e:
            checks.append(ValidationCheck(
                name="file_readable",
                passed=False,
                points=0,
                max_points=15,
                message=f"Could not read file: {e}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class JournalBootLogsTask(BaseTask):
    """Analyze boot logs using journalctl."""

    def __init__(self):
        super().__init__(
            id="boot_journal_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.output_file = "/tmp/boot_errors.txt"

    def generate(self, **params):
        """Generate journal boot log analysis task."""
        self.output_file = params.get('output_file', "/tmp/boot_errors.txt")

        self.description = (
            f"Analyze boot logs for errors:\n"
            f"  1. Use journalctl to view current boot logs\n"
            f"  2. Filter for errors and warnings\n"
            f"  3. Save any errors/warnings to: {self.output_file}\n"
            f"  \n"
            f"  Useful journalctl options:\n"
            f"  - journalctl -b (current boot)\n"
            f"  - journalctl -b -1 (previous boot)\n"
            f"  - journalctl -p err (errors only)\n"
            f"  - journalctl --list-boots (list all boots)"
        )

        self.hints = [
            "'journalctl -b' shows current boot logs",
            "'journalctl -b -p err' shows only errors from current boot",
            "'journalctl -b -p warning' shows warnings and above",
            "'journalctl --list-boots' lists available boot logs",
            "Combine: 'journalctl -b -p err..warning' for errors and warnings"
        ]

        return self

    def validate(self):
        """Validate boot log analysis."""
        checks = []
        total_points = 0

        # Check 1: File exists (3 points)
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=3,
                message=f"Output file {self.output_file} created"
            ))
            total_points += 3

            # Check 2: File has content (3 points)
            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()

                if len(content.strip()) > 0:
                    checks.append(ValidationCheck(
                        name="has_content",
                        passed=True,
                        points=3,
                        message="File contains log data"
                    ))
                    total_points += 3

                    # Check 3: Looks like journal output (4 points)
                    journal_indicators = ['systemd', 'kernel', 'err', 'warn', 'failed', 'error', 'starting', 'started']
                    has_journal = any(ind in content.lower() for ind in journal_indicators)

                    if has_journal:
                        checks.append(ValidationCheck(
                            name="journal_format",
                            passed=True,
                            points=4,
                            message="Content appears to be from journalctl"
                        ))
                        total_points += 4
                    else:
                        checks.append(ValidationCheck(
                            name="journal_format",
                            passed=False,
                            points=0,
                            max_points=4,
                            message="Content doesn't look like journal output"
                        ))
                else:
                    checks.append(ValidationCheck(
                        name="has_content",
                        passed=True,
                        points=7,  # Give full points if no errors exist
                        message="File is empty (no errors found - this is good!)"
                    ))
                    total_points += 7

            except Exception as e:
                checks.append(ValidationCheck(
                    name="file_readable",
                    passed=False,
                    points=0,
                    max_points=7,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"Output file not found: {self.output_file}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class SELinuxAutorelabelTask(BaseTask):
    """Configure SELinux autorelabel on next boot."""

    def __init__(self):
        super().__init__(
            id="boot_selinux_relabel_001",
            category="boot",
            difficulty="easy",
            points=5
        )

    def generate(self, **params):
        """Generate SELinux autorelabel task."""
        self.description = (
            f"Configure SELinux to relabel on next boot:\n"
            f"  \n"
            f"  After resetting root password or making major changes,\n"
            f"  you must trigger SELinux relabeling.\n"
            f"  \n"
            f"  Create the autorelabel trigger file:\n"
            f"  - File: /.autorelabel\n"
            f"  \n"
            f"  Note: On actual reboot, SELinux will relabel all files.\n"
            f"  This can take several minutes on large systems."
        )

        self.hints = [
            "Use 'touch /.autorelabel' to create the trigger file",
            "The file must be in the root directory: /",
            "After reboot, SELinux will relabel and delete the file",
            "Alternative: 'fixfiles -F onboot' also schedules relabel",
            "Check with: ls -la /.autorelabel"
        ]

        return self

    def validate(self):
        """Validate autorelabel file exists."""
        checks = []
        total_points = 0

        if os.path.exists('/.autorelabel'):
            checks.append(ValidationCheck(
                name="autorelabel_exists",
                passed=True,
                points=5,
                message="/.autorelabel file created - SELinux will relabel on next boot"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="autorelabel_exists",
                passed=False,
                points=0,
                max_points=5,
                message="/.autorelabel not found - use 'touch /.autorelabel'"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class ChrootPracticeTask(BaseTask):
    """Practice chroot environment setup (simulates rd.break recovery)."""

    def __init__(self):
        super().__init__(
            id="boot_chroot_001",
            category="boot",
            difficulty="exam",
            points=12
        )
        self.practice_dir = "/tmp/sysroot_practice"

    def generate(self, **params):
        """Generate chroot practice task."""
        self.practice_dir = params.get('practice_dir', "/tmp/sysroot_practice")

        self.description = (
            f"Practice chroot workflow (simulates rd.break recovery):\n"
            f"  \n"
            f"  When you use rd.break, you land in a minimal environment\n"
            f"  and must chroot into the real system at /sysroot.\n"
            f"  \n"
            f"  For this practice:\n"
            f"  1. Create practice directory: {self.practice_dir}\n"
            f"  2. Create subdirectories: bin, etc, lib, lib64, usr\n"
            f"  3. Copy /etc/passwd to {self.practice_dir}/etc/\n"
            f"  4. Create a file {self.practice_dir}/chroot_test.txt\n"
            f"     containing 'chroot practice complete'\n"
            f"  \n"
            f"  This simulates the sysroot structure you'd see after rd.break"
        )

        self.hints = [
            f"mkdir -p {self.practice_dir}/{{bin,etc,lib,lib64,usr}}",
            f"cp /etc/passwd {self.practice_dir}/etc/",
            f"echo 'chroot practice complete' > {self.practice_dir}/chroot_test.txt",
            "In real recovery: mount -o remount,rw /sysroot",
            "Then: chroot /sysroot"
        ]

        return self

    def validate(self):
        """Validate chroot practice setup."""
        checks = []
        total_points = 0

        # Check 1: Practice directory exists (2 points)
        if os.path.isdir(self.practice_dir):
            checks.append(ValidationCheck(
                name="practice_dir",
                passed=True,
                points=2,
                message=f"Practice directory {self.practice_dir} exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="practice_dir",
                passed=False,
                points=0,
                max_points=2,
                message=f"Practice directory {self.practice_dir} not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Required subdirectories (3 points)
        required_dirs = ['bin', 'etc', 'lib', 'lib64', 'usr']
        dirs_found = sum(1 for d in required_dirs if os.path.isdir(os.path.join(self.practice_dir, d)))

        if dirs_found == len(required_dirs):
            checks.append(ValidationCheck(
                name="subdirs",
                passed=True,
                points=3,
                message="All required subdirectories created"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="subdirs",
                passed=False,
                points=0,
                max_points=3,
                message=f"Missing subdirectories. Found {dirs_found}/{len(required_dirs)}"
            ))

        # Check 3: passwd file copied (3 points)
        passwd_path = os.path.join(self.practice_dir, 'etc', 'passwd')
        if os.path.exists(passwd_path):
            checks.append(ValidationCheck(
                name="passwd_copied",
                passed=True,
                points=3,
                message="passwd file copied to etc/"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="passwd_copied",
                passed=False,
                points=0,
                max_points=3,
                message="passwd file not found in etc/"
            ))

        # Check 4: Test file with correct content (4 points)
        test_file = os.path.join(self.practice_dir, 'chroot_test.txt')
        if os.path.exists(test_file):
            try:
                with open(test_file, 'r') as f:
                    content = f.read().strip().lower()
                if 'chroot practice complete' in content:
                    checks.append(ValidationCheck(
                        name="test_file",
                        passed=True,
                        points=4,
                        message="Test file created with correct content"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="test_file",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Test file exists but has wrong content"
                    ))
            except:
                checks.append(ValidationCheck(
                    name="test_file",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="Could not read test file"
                ))
        else:
            checks.append(ValidationCheck(
                name="test_file",
                passed=False,
                points=0,
                max_points=4,
                message="chroot_test.txt not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("boot")
class ListBootEntriesTask(BaseTask):
    """List and understand GRUB boot entries."""

    def __init__(self):
        super().__init__(
            id="boot_list_entries_001",
            category="boot",
            difficulty="easy",
            points=6
        )
        self.output_file = "/tmp/boot_entries.txt"

    def generate(self, **params):
        """Generate boot entries listing task."""
        self.output_file = params.get('output_file', "/tmp/boot_entries.txt")

        self.description = (
            f"List available boot entries:\n"
            f"  1. Use grubby to list all boot kernels\n"
            f"  2. Identify the default boot entry\n"
            f"  3. Save the output to: {self.output_file}\n"
            f"  \n"
            f"  Your output should show:\n"
            f"  - Available kernel versions\n"
            f"  - Which kernel is set as default"
        )

        self.hints = [
            "'grubby --info=ALL' shows all boot entries",
            "'grubby --default-kernel' shows default kernel",
            "'grubby --default-index' shows default entry index",
            "Also check: ls /boot/vmlinuz*",
            "GRUB config: /boot/grub2/grub.cfg"
        ]

        return self

    def validate(self):
        """Validate boot entries listing."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=2,
                message=f"Output file {self.output_file} exists"
            ))
            total_points += 2

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read().lower()

                # Check 2: Contains kernel info (4 points)
                kernel_indicators = ['vmlinuz', 'kernel', 'index', 'title', 'boot']
                has_kernel_info = any(ind in content for ind in kernel_indicators)

                if has_kernel_info:
                    checks.append(ValidationCheck(
                        name="kernel_info",
                        passed=True,
                        points=4,
                        message="Boot entry information recorded"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="kernel_info",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Missing kernel/boot entry information"
                    ))

            except Exception as e:
                checks.append(ValidationCheck(
                    name="file_readable",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Output file not found: {self.output_file}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
