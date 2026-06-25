"""
Boot and system target tasks for RHCSA EX200 v10 exam.
Category: boot (10 tasks)
"""

import os
import random
import logging
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


# ---------------------------------------------------------------------------
# 1. SetDefaultTargetTask (easy / 5pts) [PERSIST]
# ---------------------------------------------------------------------------
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
        self.requires_persistence = True
        self.tags = ["systemd", "target", "boot"]
        self.exam_tips = [
            "systemctl set-default is the fastest way to change the boot target.",
            "On the exam, always verify with 'systemctl get-default' after setting.",
        ]
        self.target = None

    def generate(self, **params):
        """Generate target change task."""
        targets = [
            ('multi-user.target', 'multi-user (text / no GUI)'),
            ('graphical.target', 'graphical (full GUI desktop)'),
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
            "Use 'systemctl set-default <target>' to change the default target",
            "Use 'systemctl get-default' to verify the current target",
            "Common targets: multi-user.target, graphical.target",
            "You can also use 'systemctl isolate <target>' to switch immediately",
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


# ---------------------------------------------------------------------------
# 2. ModifyGrubTimeoutTask (medium / 8pts) [PERSIST]
# ---------------------------------------------------------------------------
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
        self.requires_persistence = True
        self.tags = ["grub", "bootloader", "timeout"]
        self.exam_tips = [
            "Always run grub2-mkconfig after editing /etc/default/grub.",
            "On UEFI: grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg",
            "On BIOS: grub2-mkconfig -o /boot/grub2/grub.cfg",
        ]
        self.timeout = None

    def generate(self, **params):
        """Generate GRUB timeout modification task."""
        self.timeout = params.get('timeout', random.choice([3, 5, 8, 10, 15, 20]))

        self.description = (
            f"Configure the GRUB bootloader:\n"
            f"  - Set the boot menu timeout to {self.timeout} seconds\n"
            f"  - Edit /etc/default/grub and update GRUB_TIMEOUT\n"
            f"  - Regenerate the GRUB configuration\n"
            f"  - Changes must persist across reboots"
        )

        self.hints = [
            "Edit /etc/default/grub and modify the GRUB_TIMEOUT value",
            "After editing, run 'grub2-mkconfig -o /boot/grub2/grub.cfg'",
            "On UEFI systems, use '/boot/efi/EFI/redhat/grub.cfg' instead",
            "Verify with 'grep GRUB_TIMEOUT /etc/default/grub'",
        ]

        return self

    def validate(self):
        """Validate GRUB timeout configuration."""
        checks = []
        total_points = 0

        # Check 1: Timeout value in /etc/default/grub (4 points)
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
                name="grub_config_regenerated",
                passed=True,
                points=4,
                message="GRUB configuration file has been regenerated"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=False,
                points=0,
                max_points=4,
                message="GRUB configuration not found or not regenerated"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 3. AddKernelParameterTask (medium / 10pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class AddKernelParameterTask(BaseTask):
    """Add a kernel boot parameter via GRUB or grubby."""

    def __init__(self):
        super().__init__(
            id="boot_kernel_param_add_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = True
        self.requires_reboot = True
        self.tags = ["grub", "kernel", "grubby", "boot-parameter"]
        self.exam_tips = [
            "grubby --args='<param>' --update-kernel=ALL is the fastest method.",
            "Alternatively edit GRUB_CMDLINE_LINUX in /etc/default/grub and regenerate.",
            "Verify with: grubby --info=DEFAULT or cat /proc/cmdline (after reboot).",
        ]
        self.parameter = None
        self.parameter_desc = None

    def generate(self, **params):
        """Generate kernel parameter addition task."""
        parameters = [
            ('audit=1', 'enable kernel auditing'),
            ('crashkernel=auto', 'reserve memory for kdump crash kernel'),
            ('net.ifnames=0', 'use traditional network interface naming'),
            ('biosdevname=0', 'disable BIOS-based device naming'),
            ('nofb', 'disable framebuffer console'),
            ('systemd.unit=multi-user.target', 'boot directly to multi-user target'),
            ('ipv6.disable=1', 'disable IPv6 at kernel level'),
            ('rd.auto=1', 'enable automatic assembly of storage'),
        ]

        if params.get('parameter'):
            self.parameter = params['parameter']
            self.parameter_desc = params.get('description', 'the specified parameter')
        else:
            self.parameter, self.parameter_desc = random.choice(parameters)

        self.description = (
            f"Configure kernel boot parameters:\n"
            f"  - Add '{self.parameter}' to the default kernel command line\n"
            f"  - Purpose: {self.parameter_desc}\n"
            f"  - You may use grubby --args or edit /etc/default/grub\n"
            f"  - If editing /etc/default/grub, regenerate the GRUB config\n"
            f"  - Changes must persist across reboots"
        )

        self.hints = [
            f"Method 1 (grubby): grubby --args='{self.parameter}' --update-kernel=ALL",
            "Method 2: Edit /etc/default/grub GRUB_CMDLINE_LINUX line",
            "If using method 2, run 'grub2-mkconfig -o /boot/grub2/grub.cfg'",
            "Verify: grubby --info=DEFAULT | grep args",
        ]

        return self

    def validate(self):
        """Validate kernel parameter is added."""
        checks = []
        total_points = 0

        # Check if parameter contains '='
        if '=' in self.parameter:
            param_name, param_value = self.parameter.split('=', 1)
            param_in_grub = validate_grub_parameter_value(param_name, param_value)
        else:
            param_in_grub = validate_grub_parameter(self.parameter)

        # Check 1: Parameter present in kernel command line (6 points)
        if param_in_grub:
            checks.append(ValidationCheck(
                name="kernel_param_added",
                passed=True,
                points=6,
                message=f"Kernel parameter '{self.parameter}' is present"
            ))
            total_points += 6
        else:
            current_cmdline = get_grub_cmdline()
            checks.append(ValidationCheck(
                name="kernel_param_added",
                passed=False,
                points=0,
                max_points=6,
                message=(
                    f"Parameter '{self.parameter}' not found in GRUB_CMDLINE_LINUX. "
                    f"Current: {current_cmdline}"
                )
            ))

        # Check 2: GRUB config exists / updated (4 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=True,
                points=4,
                message="GRUB configuration is up to date"
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


# ---------------------------------------------------------------------------
# 4. RemoveKernelParameterTask (medium / 10pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class RemoveKernelParameterTask(BaseTask):
    """
    Fault-injection: injects a kernel parameter via grubby so it is
    guaranteed to be present; user must remove it.
    Uses only params that are NOT on a clean RHEL 10 kernel cmdline
    to avoid double-injecting parameters that are already there.
    """

    has_fault_injection = True

    # These are NOT present on a default RHEL 10 kernel cmdline
    _INJECTABLE_PARAMS = ['nofb', 'audit=0', 'biosdevname=0', 'nosplash']

    def __init__(self):
        super().__init__(
            id="boot_kernel_param_remove_001",
            category="boot",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = True
        self.requires_reboot = True
        self.tags = ["grub", "kernel", "grubby", "boot-parameter", "fault-injection"]
        self.exam_tips = [
            "grubby --remove-args='<param>' --update-kernel=ALL is the fastest way.",
            "Be careful when editing GRUB_CMDLINE_LINUX not to break the quoting.",
            "Verify removal: grubby --info=DEFAULT | grep args",
        ]
        self.parameter = None

    def generate(self, **params):
        self.parameter = params.get('parameter', random.choice(self._INJECTABLE_PARAMS))

        self.description = (
            f"Configure kernel boot parameters:\n"
            f"  - The parameter '{self.parameter}' has been added to the kernel command line\n"
            f"  - Remove it so it will not be present at next boot\n"
            f"  - You may use grubby --remove-args or edit /etc/default/grub\n"
            f"  - If editing /etc/default/grub, regenerate the GRUB config afterwards"
        )
        self.hints = [
            f"Method 1 (faster): grubby --remove-args='{self.parameter}' --update-kernel=ALL",
            "Method 2: Edit /etc/default/grub, remove from GRUB_CMDLINE_LINUX",
            "  Then: grub2-mkconfig -o /boot/grub2/grub.cfg",
            "Verify: grubby --info=DEFAULT | grep args",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        param = self.parameter
        r = _sp.run(['grubby', '--args', param, '--update-kernel=ALL'], capture_output=True)
        if r.returncode != 0:
            return False, f"grubby failed: {r.stderr.decode().strip()}"
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'parameter': param})
        return True, f"Added kernel parameter '{param}' via grubby"

    def restore_fault(self):
        import subprocess as _sp
        param = self.parameter
        _sp.run(['grubby', '--remove-args', param, '--update-kernel=ALL'], capture_output=True)
        from tasks.troubleshooting import clear_fault_state
        clear_fault_state()
        return True, f"Removed kernel parameter '{param}'"

    def validate(self):
        checks = []
        total_points = 0

        if '=' in self.parameter:
            param_name = self.parameter.split('=', 1)[0]
            param_exists = validate_grub_parameter(param_name)
        else:
            param_exists = validate_grub_parameter(self.parameter)

        # Check 1: Parameter removed (6 pts)
        if not param_exists:
            checks.append(ValidationCheck(
                name="kernel_param_removed",
                passed=True,
                points=6,
                message=f"Kernel parameter '{self.parameter}' has been removed"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="kernel_param_removed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Parameter '{self.parameter}' is still in the kernel cmdline"
            ))

        # Check 2: GRUB config regenerated (4 pts)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=True,
                points=4,
                message="GRUB configuration has been updated"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="grub_config_regenerated",
                passed=False,
                points=0,
                max_points=4,
                message="GRUB config not yet regenerated (run grub2-mkconfig or use grubby)"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 5. BootTroubleshootingTask (exam / 15pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class BootTroubleshootingTask(BaseTask):
    """Composite boot troubleshooting scenario combining target + GRUB + parameter fixes."""

    def __init__(self):
        super().__init__(
            id="boot_troubleshoot_001",
            category="boot",
            difficulty="exam",
            points=15
        )
        self.requires_persistence = True
        self.tags = ["troubleshooting", "grub", "systemd", "exam-scenario"]
        self.exam_tips = [
            "Always verify ALL changes: systemctl get-default, grep /etc/default/grub, grubby --info=DEFAULT.",
            "If asked to regenerate GRUB config, remember BIOS vs UEFI paths differ.",
        ]
        self.target = None
        self.timeout = None
        self.extra_param = None

    def generate(self, **params):
        """Generate boot troubleshooting task."""
        scenarios = [
            {
                'desc': 'System boots to graphical target but must boot to text mode',
                'target': 'multi-user.target',
                'timeout': random.choice([3, 5, 8]),
                'extra_param': 'quiet',
            },
            {
                'desc': 'System boots to text mode but must provide a GUI',
                'target': 'graphical.target',
                'timeout': random.choice([5, 10, 15]),
                'extra_param': 'rhgb',
            },
            {
                'desc': 'System boots with no timeout and auditing disabled',
                'target': 'multi-user.target',
                'timeout': random.choice([5, 10]),
                'extra_param': 'audit=1',
            },
        ]

        scenario = params.get('scenario', random.choice(scenarios))
        self.target = scenario['target']
        self.timeout = scenario['timeout']
        self.extra_param = scenario.get('extra_param', 'quiet')

        self.description = (
            f"Boot Troubleshooting Scenario:\n"
            f"  Problem: {scenario['desc']}\n"
            f"\n"
            f"  Required fixes:\n"
            f"  1. Set default target to: {self.target}\n"
            f"  2. Set GRUB timeout to: {self.timeout} seconds\n"
            f"  3. Ensure '{self.extra_param}' is in the kernel command line\n"
            f"  4. Regenerate the GRUB configuration\n"
            f"  - All changes must persist across reboots"
        )

        self.hints = [
            f"systemctl set-default {self.target}",
            f"Edit /etc/default/grub: GRUB_TIMEOUT={self.timeout}",
            f"Ensure '{self.extra_param}' appears in GRUB_CMDLINE_LINUX",
            "Run grub2-mkconfig -o /boot/grub2/grub.cfg",
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
                message=f"Target is '{current}', expected '{self.target}'"
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

        # Check 3: Extra kernel parameter present (3 points)
        if '=' in self.extra_param:
            pn, pv = self.extra_param.split('=', 1)
            param_ok = validate_grub_parameter_value(pn, pv)
        else:
            param_ok = validate_grub_parameter(self.extra_param)

        if param_ok:
            checks.append(ValidationCheck(
                name="extra_param_present",
                passed=True,
                points=3,
                message=f"Kernel parameter '{self.extra_param}' is present"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="extra_param_present",
                passed=False,
                points=0,
                max_points=3,
                message=f"Kernel parameter '{self.extra_param}' not found in GRUB_CMDLINE_LINUX"
            ))

        # Check 4: GRUB config regenerated (3 points)
        if is_grub_config_updated():
            checks.append(ValidationCheck(
                name="grub_regenerated",
                passed=True,
                points=3,
                message="GRUB configuration has been regenerated"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="grub_regenerated",
                passed=False,
                points=0,
                max_points=3,
                message="GRUB configuration has not been regenerated"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 6. ValidateFstabTask (exam / 12pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class ValidateFstabTask(BaseTask):
    """
    Fault-injection fstab task.

    inject_fault() adds two broken entries:
      1. A non-existent UUID — must be removed entirely.
      2. A /backup entry missing 'nofail' — must have nofail added so a
         missing device doesn't hang the boot sequence.
    """

    BAD_UUID_MARKER  = 'RHCSA-FAULT-FSTAB-BADUID'
    NOFAIL_MARKER    = 'RHCSA-FAULT-FSTAB-NOFAIL'
    NOFAIL_MOUNTPOINT = '/backup'
    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="boot_fstab_001",
            category="boot",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = True
        self.tags = ["fstab", "boot", "troubleshooting", "fault-injection"]
        self.exam_tips = [
            "A broken fstab WILL prevent boot and cost you the entire exam.",
            "Always run 'findmnt --verify' and 'mount -a' BEFORE rebooting.",
            "'nofail' lets the system boot even when an optional device is absent.",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: /etc/fstab Has Boot-Blocking Errors\n"
            "=" * 50 + "\n\n"
            "Two problems have been injected into /etc/fstab:\n\n"
            "  Problem 1 — An entry references a UUID that does not exist.\n"
            "    Symptom: 'mount -a' fails; system may drop to emergency shell.\n"
            "    Fix: identify and remove the bad entry.\n\n"
            f"  Problem 2 — {self.NOFAIL_MOUNTPOINT} is in fstab without 'nofail'.\n"
            "    Symptom: if the device is absent at boot, boot hangs.\n"
            "    Fix: add 'nofail' to its mount options.\n\n"
            "Tasks:\n"
            "  1. Run 'findmnt --verify' to identify the bad entries\n"
            "  2. Remove the non-existent UUID entry\n"
            f"  3. Add 'nofail' to the {self.NOFAIL_MOUNTPOINT} entry\n"
            "  4. Verify 'mount -a' completes without errors"
        )
        self.hints = [
            "'findmnt --verify' shows which entries are invalid",
            "Remove the bad UUID line entirely — it references a device that doesn't exist",
            f"Edit the {self.NOFAIL_MOUNTPOINT} line: change 'defaults' to 'defaults,nofail'",
            "'mount -a' should return exit code 0 when fstab is clean",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        os.makedirs(self.NOFAIL_MOUNTPOINT, exist_ok=True)

        entries = (
            f"UUID=00000000-dead-beef-0000-badbadbad00 /mnt/nonexistent xfs defaults 0 2"
            f"  # {self.BAD_UUID_MARKER}\n"
            f"/dev/sdZ99 {self.NOFAIL_MOUNTPOINT} xfs defaults 0 0"
            f"  # {self.NOFAIL_MARKER}\n"
        )
        with open('/etc/fstab', 'a') as f:
            f.write(entries)

        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {
            'bad_uuid_marker': self.BAD_UUID_MARKER,
            'nofail_marker': self.NOFAIL_MARKER,
        })
        return True, "Added bad UUID entry and nofail-missing /backup entry to /etc/fstab"

    def restore_fault(self):
        try:
            with open('/etc/fstab') as f:
                lines = f.readlines()
            cleaned = [l for l in lines
                       if self.BAD_UUID_MARKER not in l and self.NOFAIL_MARKER not in l]
            with open('/etc/fstab', 'w') as f:
                f.writelines(cleaned)
            try:
                os.rmdir(self.NOFAIL_MOUNTPOINT)
            except OSError:
                pass
            from tasks.troubleshooting import clear_fault_state
            clear_fault_state()
            return True, "Removed injected fstab entries"
        except Exception as e:
            return False, f"Restore error: {e}"

    def validate(self):
        checks = []
        score = 0

        with open('/etc/fstab') as f:
            fstab_lines = f.readlines()
        fstab_text = ''.join(fstab_lines)

        # Check 1: bad UUID entry removed (4 pts)
        if self.BAD_UUID_MARKER not in fstab_text:
            checks.append(ValidationCheck("bad_entry_removed", True, 4,
                message="Non-existent UUID entry has been removed"))
            score += 4
        else:
            checks.append(ValidationCheck("bad_entry_removed", False, 0, max_points=4,
                message="Bad UUID entry still in /etc/fstab — will cause boot failure"))

        # Check 2: findmnt --verify passes (2 pts)
        r = execute_safe(['findmnt', '--verify'])
        if r.returncode == 0:
            checks.append(ValidationCheck("fstab_valid", True, 2,
                message="findmnt --verify reports no errors"))
            score += 2
        else:
            checks.append(ValidationCheck("fstab_valid", False, 0, max_points=2,
                message=f"findmnt --verify still reports errors"))

        # Check 3: mount -a succeeds (2 pts)
        r = execute_safe(['mount', '-a'])
        if r.returncode == 0:
            checks.append(ValidationCheck("mount_a_clean", True, 2,
                message="mount -a completes without errors"))
            score += 2
        else:
            checks.append(ValidationCheck("mount_a_clean", False, 0, max_points=2,
                message=f"mount -a still fails: {r.stderr.strip()[:80]}"))

        # Check 4: /backup entry has nofail (4 pts)
        nofail_line = next(
            (l for l in fstab_lines if self.NOFAIL_MARKER in l), None
        )
        if nofail_line is None:
            # User removed the line entirely — also acceptable, award partial
            checks.append(ValidationCheck("nofail_added", False, 2, max_points=4,
                message=f"{self.NOFAIL_MOUNTPOINT} entry was removed (ok) but adding nofail is the preferred fix"))
            score += 2
        else:
            parts = nofail_line.split()
            options = parts[3] if len(parts) >= 4 else ''
            if 'nofail' in options:
                checks.append(ValidationCheck("nofail_added", True, 4,
                    message=f"{self.NOFAIL_MOUNTPOINT} entry has 'nofail' — safe for missing device"))
                score += 4
            else:
                checks.append(ValidationCheck("nofail_added", False, 0, max_points=4,
                    message=f"{self.NOFAIL_MOUNTPOINT} entry still lacks 'nofail' — will block boot if device absent"))

        return ValidationResult(self.id, score >= self.points * 0.6, score, self.points, checks)


# ---------------------------------------------------------------------------
# 7. AnalyzeBootTimeTask (medium / 10pts)
# ---------------------------------------------------------------------------
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
        self.requires_persistence = False
        self.tags = ["systemd-analyze", "performance", "boot"]
        self.exam_tips = [
            "systemd-analyze blame lists services by startup time.",
            "systemd-analyze critical-chain shows the dependency chain.",
        ]
        self.output_file = "/tmp/boot_analysis.txt"
        self.top_n = 5

    def generate(self, **params):
        """Generate boot analysis task."""
        self.output_file = params.get('output_file', "/tmp/boot_analysis.txt")
        self.top_n = params.get('top_n', random.choice([5, 8, 10]))

        self.description = (
            f"Analyze system boot performance:\n"
            f"  1. Use systemd-analyze to get the total boot time\n"
            f"  2. Identify the {self.top_n} slowest services using systemd-analyze blame\n"
            f"  3. Write ALL output to: {self.output_file}\n"
            f"\n"
            f"  The file should contain:\n"
            f"  - Total boot time (from 'systemd-analyze')\n"
            f"  - Top {self.top_n} slowest services (from 'systemd-analyze blame')"
        )

        self.hints = [
            "Run 'systemd-analyze' to see the total boot time",
            f"Run 'systemd-analyze blame | head -{self.top_n}' for slowest services",
            "Redirect output with '>' or '>>'",
            "'systemd-analyze critical-chain' shows the dependency chain",
        ]

        return self

    def validate(self):
        """Validate boot analysis output."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if not os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"Output file {self.output_file} not found"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        checks.append(ValidationCheck(
            name="file_exists",
            passed=True,
            points=2,
            message=f"Output file {self.output_file} exists"
        ))
        total_points += 2

        try:
            with open(self.output_file, 'r') as f:
                content = f.read()
            content_lower = content.lower()

            # Check 2: Contains boot time information (4 points)
            boot_time_markers = [
                'startup finished', 'kernel', 'userspace',
                'graphical.target', 'multi-user.target', 'reached'
            ]
            has_boot_time = any(m in content_lower for m in boot_time_markers)
            if has_boot_time:
                checks.append(ValidationCheck(
                    name="boot_time_recorded",
                    passed=True,
                    points=4,
                    message="Boot time information recorded correctly"
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

            # Check 3: Contains service blame data (4 points)
            service_markers = ['.service', 'ms', 'min']
            # Count how many .service lines appear
            service_lines = [
                l for l in content.splitlines()
                if '.service' in l or '.target' in l
            ]
            if len(service_lines) >= min(3, self.top_n):
                checks.append(ValidationCheck(
                    name="services_listed",
                    passed=True,
                    points=4,
                    message=f"Service startup times recorded ({len(service_lines)} entries found)"
                ))
                total_points += 4
            elif any(m in content_lower for m in service_markers):
                checks.append(ValidationCheck(
                    name="services_listed",
                    passed=True,
                    points=2,
                    message="Some service data found, but fewer entries than expected"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="services_listed",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="Missing service blame data (run systemd-analyze blame)"
                ))

        except Exception as e:
            checks.append(ValidationCheck(
                name="file_readable",
                passed=False,
                points=0,
                max_points=8,
                message=f"Could not read file: {e}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 8. ListBootEntriesTask (easy / 6pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class ListBootEntriesTask(BaseTask):
    """List available GRUB boot entries using grubby."""

    def __init__(self):
        super().__init__(
            id="boot_list_entries_001",
            category="boot",
            difficulty="easy",
            points=6
        )
        self.requires_persistence = False
        self.tags = ["grub", "grubby", "kernel", "boot-entries"]
        self.exam_tips = [
            "grubby --info=ALL lists every boot entry with details.",
            "grubby --default-kernel shows which kernel boots by default.",
        ]
        self.output_file = "/tmp/boot_entries.txt"

    def generate(self, **params):
        """Generate boot entries listing task."""
        self.output_file = params.get(
            'output_file',
            random.choice(["/tmp/boot_entries.txt", "/tmp/grub_entries.txt"])
        )

        self.description = (
            f"List available boot entries:\n"
            f"  1. Use grubby to list all boot kernels\n"
            f"  2. Identify the default boot entry\n"
            f"  3. Save the output to: {self.output_file}\n"
            f"\n"
            f"  Your output should show:\n"
            f"  - Available kernel versions\n"
            f"  - Which kernel is set as default"
        )

        self.hints = [
            "'grubby --info=ALL' shows all boot entries",
            "'grubby --default-kernel' shows the default kernel",
            "'grubby --default-index' shows the default entry index",
            "Also try: ls /boot/vmlinuz*",
        ]

        return self

    def validate(self):
        """Validate boot entries listing."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if not os.path.exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Output file not found: {self.output_file}"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

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

            # Check 2: Contains kernel/boot info (4 points)
            kernel_indicators = ['vmlinuz', 'kernel', 'index', 'title', 'root', 'args']
            has_kernel_info = any(ind in content for ind in kernel_indicators)

            if has_kernel_info:
                checks.append(ValidationCheck(
                    name="kernel_info",
                    passed=True,
                    points=4,
                    message="Boot entry information recorded correctly"
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

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 9. SELinuxAutorelabelTask (easy / 5pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot")
class SELinuxAutorelabelTask(BaseTask):
    """Configure SELinux to perform a full relabel on next boot."""

    def __init__(self):
        super().__init__(
            id="boot_selinux_relabel_001",
            category="boot",
            difficulty="easy",
            points=5
        )
        self.requires_persistence = False
        self.requires_reboot = True
        self.tags = ["selinux", "autorelabel", "boot"]
        self.exam_tips = [
            "After resetting root password via rd.break you MUST 'touch /.autorelabel'.",
            "Forgetting this step will leave the system with wrong SELinux labels.",
            "Alternative: 'fixfiles -F onboot' also schedules relabeling.",
        ]

    def generate(self, **params):
        """Generate SELinux autorelabel task."""
        self.description = (
            f"Configure SELinux to relabel all files on next boot:\n"
            f"\n"
            f"  After resetting root password or making major SELinux changes,\n"
            f"  you must trigger a full filesystem relabel.\n"
            f"\n"
            f"  Create the autorelabel trigger file:\n"
            f"  - File: /.autorelabel\n"
            f"\n"
            f"  Note: On actual reboot, SELinux will relabel every file.\n"
            f"  This can take several minutes on large systems."
        )

        self.hints = [
            "Use 'touch /.autorelabel' to create the trigger file",
            "The file must be at the root of the filesystem: /",
            "After reboot SELinux will relabel and automatically delete the file",
            "Alternative: 'fixfiles -F onboot'",
        ]

        return self

    def validate(self):
        """Validate autorelabel trigger file exists."""
        checks = []
        total_points = 0

        if os.path.exists('/.autorelabel'):
            checks.append(ValidationCheck(
                name="autorelabel_exists",
                passed=True,
                points=5,
                message="/.autorelabel exists - SELinux will relabel on next boot"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="autorelabel_exists",
                passed=False,
                points=0,
                max_points=5,
                message="/.autorelabel not found - run 'touch /.autorelabel'"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 10. RebuildInitramfsTask (medium / 8pts)
# ---------------------------------------------------------------------------
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
        self.requires_persistence = False
        self.requires_reboot = True
        self.tags = ["dracut", "initramfs", "kernel", "boot"]
        self.exam_tips = [
            "'dracut -f' rebuilds initramfs for the running kernel.",
            "After adding kernel modules or changing dracut config, always rebuild.",
            "Verify with 'lsinitrd' to list initramfs contents.",
        ]

    def generate(self, **params):
        """Generate initramfs rebuild task."""
        self.description = (
            f"Rebuild the initramfs (initial RAM filesystem):\n"
            f"  1. Identify the current kernel version with 'uname -r'\n"
            f"  2. Rebuild the initramfs for the current kernel using dracut\n"
            f"  3. Verify the initramfs image was updated\n"
            f"\n"
            f"  When to rebuild initramfs:\n"
            f"  - After adding new kernel modules\n"
            f"  - After modifying /etc/dracut.conf or dracut.conf.d/\n"
            f"  - After certain storage configuration changes"
        )

        self.hints = [
            "'uname -r' shows the running kernel version",
            "'dracut -f' forces rebuild for the current kernel",
            "'dracut -f /boot/initramfs-$(uname -r).img $(uname -r)' is explicit",
            "'lsinitrd' lists contents of the initramfs",
            "Check: ls -la /boot/initramfs-*",
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

        # Check 1: initramfs file exists (4 points)
        if os.path.exists(initramfs_path):
            checks.append(ValidationCheck(
                name="initramfs_exists",
                passed=True,
                points=4,
                message=f"initramfs exists: {initramfs_path}"
            ))
            total_points += 4

            # Check 2: initramfs is readable / valid (4 points)
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
                    message="initramfs may be corrupted or lsinitrd not available"
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
