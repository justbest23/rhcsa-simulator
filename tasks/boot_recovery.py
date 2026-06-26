"""
Boot recovery and emergency access tasks for RHCSA EX200 v10 exam.
Category: boot_recovery (6 tasks)

Covers rd.break root password reset, chroot environments, emergency
target booting, fstab recovery, and read-only root filesystem repair.
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
# 1. RootPasswordResetTask (exam / 20pts) [EXAM-SEEN]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class RootPasswordResetTask(BaseTask):
    """Reset root password using the rd.break boot procedure."""

    exam_eligible = False

    def __init__(self):
        super().__init__(
            id="boot_recovery_root_pw_reset_001",
            category="boot_recovery",
            difficulty="exam",
            points=20
        )
        self.requires_persistence = False
        self.requires_reboot = True
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "On RHEL 10 sulogin may require existing root password",
            "rd.break drops to initramfs before root is mounted",
            "Remember: mount -o remount,rw /sysroot then chroot /sysroot",
        ]
        self.new_password = None

    def generate(self, **params):
        """Generate root password reset task with randomized scenario."""
        passwords = [
            'Ex200Pass!', 'Redhat@2024', 'RhcsaExam#1',
            'BootFix$99', 'R00tReset!', 'P@ssw0rd123',
        ]
        self.new_password = params.get('password', random.choice(passwords))

        scenarios = [
            (
                "You have inherited a RHEL server and do not know the root password.",
                "Use the rd.break method to reset it."
            ),
            (
                "The root password has expired and the account is inaccessible.",
                "Boot into the initramfs to reset it."
            ),
            (
                "A colleague left the organization and the root password is unknown.",
                "Gain access through the rd.break boot procedure."
            ),
        ]
        scenario_desc, scenario_action = random.choice(scenarios)

        self.description = (
            f"SCENARIO: {scenario_desc}\n"
            f"\n"
            f"Recover root access and set the root password to: {self.new_password}\n"
            f"\n"
            f"The system is currently running. You will need to interrupt the boot\n"
            f"process to gain access without the current root password.\n"
            f"Changes must survive reboot."
        )

        self.hints = [
            "The GRUB bootloader allows editing kernel parameters before boot",
            "Pressing 'e' at the GRUB menu lets you edit the boot entry",
            "The kernel command line accepts special boot parameters that alter the init process",
            "After gaining a shell, the real root filesystem is not yet mounted writable",
            f"The new root password to set is: {self.new_password}",
            "SELinux labels will be wrong after chroot modifications — plan accordingly",
        ]

        return self

    def validate(self):
        """Validate root password was recently reset and account is active."""
        checks = []
        total_points = 0

        # Check 1: /etc/shadow exists and root entry present (4 points)
        result = execute_safe(['stat', '--format=%Y', '/etc/shadow'])
        shadow_exists = result.success
        if shadow_exists:
            checks.append(ValidationCheck(
                name="shadow_accessible",
                passed=True,
                points=4,
                message="/etc/shadow is accessible and contains password data"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="shadow_accessible",
                passed=False,
                points=0,
                max_points=4,
                message=f"/etc/shadow is not accessible: {result.stderr}"
            ))

        # Check 2: Root password was recently modified (8 points)
        # Use chage -l root to inspect last password change date
        result = execute_safe(['chage', '-l', 'root'])
        pw_recently_changed = False
        if result.success:
            import datetime
            today_str = datetime.date.today().strftime('%b %d, %Y')
            # Also check with alternate date formats
            today_alt = datetime.date.today().strftime('%Y-%m-%d')
            output = result.stdout
            for line in output.splitlines():
                if 'last password change' in line.lower():
                    if today_str in line or today_alt in line or 'never' not in line.lower():
                        pw_recently_changed = True
                    break

        if pw_recently_changed:
            checks.append(ValidationCheck(
                name="password_recently_changed",
                passed=True,
                points=8,
                message="Root password has been recently changed"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="password_recently_changed",
                passed=False,
                points=0,
                max_points=8,
                message="Root password does not appear to have been recently changed"
            ))

        # Check 3: Root account is not locked (8 points)
        result = execute_safe(['passwd', '-S', 'root'])
        account_active = False
        if result.success:
            parts = result.stdout.strip().split()
            # passwd -S output: root PS|NP|LK <date> ...
            # PS = password set, NP = no password, LK = locked
            if len(parts) >= 2 and parts[1] in ('PS', 'P'):
                account_active = True

        if account_active:
            checks.append(ValidationCheck(
                name="root_account_active",
                passed=True,
                points=8,
                message="Root account is active and not locked"
            ))
            total_points += 8
        else:
            status_info = result.stdout.strip() if result.success else result.stderr
            checks.append(ValidationCheck(
                name="root_account_active",
                passed=False,
                points=0,
                max_points=8,
                message=f"Root account may be locked or has no password set. Status: {status_info}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 2. RootPasswordResetSuloginTask (hard / 20pts) [EXAM-SEEN]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class RootPasswordResetSuloginTask(BaseTask):
    """Reset root password using rd.break with SELinux autorelabel awareness (RHEL 10 sulogin)."""

    def __init__(self):
        super().__init__(
            id="boot_recovery_root_pw_sulogin_001",
            category="boot_recovery",
            difficulty="hard",
            points=20
        )
        self.requires_persistence = False
        self.requires_reboot = True
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "On RHEL 10 sulogin may require existing root password",
            "rd.break drops to initramfs before root is mounted",
            "Remember: mount -o remount,rw /sysroot then chroot /sysroot",
            "RHEL 10 emergency mode uses sulogin which needs root password - use rd.break instead",
            "After password reset in chroot: touch /.autorelabel is MANDATORY for SELinux",
        ]
        self.new_password = None
        self.require_relabel_method = None

    def generate(self, **params):
        """Generate sulogin-aware root password reset task."""
        passwords = [
            'SuL0gin!Fix', 'Rd.Br3ak#1', 'Rhel10Pass!',
            'Ch00tReset$', 'S3linux@Lab', 'ExamR00t!9',
        ]
        self.new_password = params.get('password', random.choice(passwords))

        relabel_methods = [
            ('autorelabel_file', 'touch /.autorelabel'),
            ('fixfiles_onboot', 'fixfiles -F onboot'),
        ]
        method_key, method_cmd = params.get(
            'relabel_method',
            random.choice(relabel_methods)
        )
        self.require_relabel_method = method_key

        self.description = (
            f"Reset the root password (RHEL 10 sulogin-aware procedure):\n"
            f"\n"
            f"  IMPORTANT: On RHEL 10, emergency mode uses sulogin which requires\n"
            f"  the root password. If you do not know the root password, you MUST\n"
            f"  use the rd.break method instead of emergency.target.\n"
            f"\n"
            f"  Steps:\n"
            f"  1. Reboot and interrupt the GRUB menu\n"
            f"  2. Append 'rd.break' to the kernel line and boot (Ctrl-x)\n"
            f"  3. mount -o remount,rw /sysroot\n"
            f"  4. chroot /sysroot\n"
            f"  5. Set root password to: {self.new_password}\n"
            f"  6. Trigger SELinux relabel using: {method_cmd}\n"
            f"  7. Exit chroot and reboot\n"
            f"\n"
            f"  The SELinux relabel step is CRITICAL - skipping it will leave\n"
            f"  /etc/shadow with incorrect SELinux context and login will fail."
        )

        self.hints = [
            "rd.break stops boot BEFORE /sysroot is mounted read-write",
            "mount -o remount,rw /sysroot && chroot /sysroot",
            f"passwd root  (set to: {self.new_password})",
            f"Trigger relabel: {method_cmd}",
            "If using touch /.autorelabel, the file must be at /sysroot root (/ inside chroot)",
            "Do NOT use systemd.unit=emergency.target if root password is unknown on RHEL 10",
        ]

        return self

    def validate(self):
        """Validate password reset AND SELinux relabel was triggered."""
        checks = []
        total_points = 0

        # Check 1: Root account is active and password set (6 points)
        result = execute_safe(['passwd', '-S', 'root'])
        account_active = False
        if result.success:
            parts = result.stdout.strip().split()
            if len(parts) >= 2 and parts[1] in ('PS', 'P'):
                account_active = True

        if account_active:
            checks.append(ValidationCheck(
                name="root_account_active",
                passed=True,
                points=6,
                message="Root account is active with a password set"
            ))
            total_points += 6
        else:
            status_info = result.stdout.strip() if result.success else result.stderr
            checks.append(ValidationCheck(
                name="root_account_active",
                passed=False,
                points=0,
                max_points=6,
                message=f"Root account is locked or no password set. Status: {status_info}"
            ))

        # Check 2: /etc/shadow recently modified (6 points)
        result = execute_safe(['stat', '--format=%Y', '/etc/shadow'])
        shadow_recently_modified = False
        if result.success:
            try:
                import time
                shadow_mtime = int(result.stdout.strip())
                now = int(time.time())
                # Consider "recently" as within the last 24 hours
                if (now - shadow_mtime) < 86400:
                    shadow_recently_modified = True
            except (ValueError, TypeError):
                pass

        if shadow_recently_modified:
            checks.append(ValidationCheck(
                name="shadow_recently_modified",
                passed=True,
                points=6,
                message="/etc/shadow was modified within the last 24 hours"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="shadow_recently_modified",
                passed=False,
                points=0,
                max_points=6,
                message="/etc/shadow does not appear to have been recently modified"
            ))

        # Check 3: SELinux autorelabel triggered (8 points)
        # Method A: /.autorelabel file exists
        autorelabel_file_exists = os.path.exists('/.autorelabel')

        # Method B: Check if fixfiles onboot was used (creates /.autorelabel too,
        # or check /etc/selinux/fixfiles_exclude_dirs or relabel trigger)
        fixfiles_triggered = False
        if not autorelabel_file_exists:
            # fixfiles -F onboot also creates /.autorelabel on RHEL systems
            result = execute_safe(['ls', '-la', '/.autorelabel'])
            fixfiles_triggered = result.success

        # Method C: Check SELinux context on /etc/shadow is correct
        selinux_context_ok = False
        result = execute_safe(['ls', '-Z', '/etc/shadow'])
        if result.success:
            output = result.stdout.strip()
            if 'shadow_t' in output:
                selinux_context_ok = True

        relabel_ok = autorelabel_file_exists or fixfiles_triggered or selinux_context_ok

        if relabel_ok:
            if autorelabel_file_exists:
                detail_msg = "/.autorelabel file found - relabel will occur on next boot"
            elif selinux_context_ok:
                detail_msg = "SELinux context on /etc/shadow is correct (shadow_t)"
            else:
                detail_msg = "SELinux relabel appears to have been triggered"

            checks.append(ValidationCheck(
                name="selinux_relabel_triggered",
                passed=True,
                points=8,
                message=detail_msg
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="selinux_relabel_triggered",
                passed=False,
                points=0,
                max_points=8,
                message=(
                    "SELinux relabel not triggered. "
                    "Run 'touch /.autorelabel' or 'fixfiles -F onboot' inside chroot. "
                    "Without this, /etc/shadow will have wrong SELinux context and login fails."
                )
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 3. ChrootPracticeTask (exam / 12pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class ChrootPracticeTask(BaseTask):
    """Practice setting up a chroot environment for system recovery."""

    def __init__(self):
        super().__init__(
            id="boot_recovery_chroot_practice_001",
            category="boot_recovery",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "In rd.break, /sysroot is where the real root filesystem is mounted.",
            "After chroot you must mount /proc, /sys, /dev for full functionality.",
            "Some commands (e.g. passwd, systemctl) need these pseudo-filesystems.",
        ]
        self.chroot_dir = None
        self.required_mounts = None

    def generate(self, **params):
        """Generate chroot environment setup task with randomized directory."""
        chroot_dirs = [
            '/mnt/sysimage', '/mnt/recovery', '/tmp/chroot_test',
            '/mnt/rescue', '/tmp/sysroot_sim',
        ]
        self.chroot_dir = params.get('chroot_dir', random.choice(chroot_dirs))

        mount_sets = [
            ['proc', 'sys', 'dev'],
            ['proc', 'sys', 'dev', 'dev/pts'],
            ['proc', 'sys', 'dev', 'run'],
        ]
        self.required_mounts = params.get('mounts', random.choice(mount_sets))

        mount_instructions = "\n".join(
            [f"     - mount --bind /{m} {self.chroot_dir}/{m}" for m in self.required_mounts]
        )

        self.description = (
            f"Set up a chroot environment for system recovery practice:\n"
            f"\n"
            f"  1. Create the chroot directory: {self.chroot_dir}\n"
            f"  2. Create the required subdirectories for bind mounts:\n"
            f"     {', '.join(self.required_mounts)}\n"
            f"  3. Bind-mount the pseudo-filesystems:\n"
            f"{mount_instructions}\n"
            f"  4. Verify the chroot is functional: chroot {self.chroot_dir} /bin/bash\n"
            f"\n"
            f"  This simulates what happens during rd.break recovery when you\n"
            f"  chroot into /sysroot."
        )

        self.hints = [
            f"mkdir -p {self.chroot_dir}",
            f"Create subdirs: " + ", ".join(
                [f"mkdir -p {self.chroot_dir}/{m}" for m in self.required_mounts]
            ),
            f"mount --bind /proc {self.chroot_dir}/proc",
            f"mount --bind /sys {self.chroot_dir}/sys",
            f"mount --bind /dev {self.chroot_dir}/dev",
            "Test with: chroot " + self.chroot_dir + " /bin/bash -c 'echo OK'",
        ]

        return self

    def validate(self):
        """Validate chroot directory structure and mount points."""
        checks = []
        total_points = 0

        # Check 1: Chroot base directory exists (3 points)
        if os.path.isdir(self.chroot_dir):
            checks.append(ValidationCheck(
                name="chroot_dir_exists",
                passed=True,
                points=3,
                message=f"Chroot directory {self.chroot_dir} exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="chroot_dir_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Chroot directory {self.chroot_dir} does not exist"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: Required subdirectories exist (3 points)
        missing_dirs = []
        for mount in self.required_mounts:
            mount_path = os.path.join(self.chroot_dir, mount)
            if not os.path.isdir(mount_path):
                missing_dirs.append(mount)

        if not missing_dirs:
            checks.append(ValidationCheck(
                name="subdirs_exist",
                passed=True,
                points=3,
                message=f"All required subdirectories exist: {', '.join(self.required_mounts)}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="subdirs_exist",
                passed=False,
                points=0,
                max_points=3,
                message=f"Missing subdirectories: {', '.join(missing_dirs)}"
            ))

        # Check 3: Pseudo-filesystems are mounted (6 points)
        # Check mount output for bind mounts into chroot
        result = execute_safe(['findmnt', '--list', '--output=TARGET', '--noheadings'])
        mounted_targets = []
        if result.success:
            mounted_targets = [line.strip() for line in result.stdout.splitlines()]

        mounted_count = 0
        mount_details = []
        for mount in self.required_mounts:
            target = os.path.join(self.chroot_dir, mount)
            if target in mounted_targets:
                mounted_count += 1
                mount_details.append(f"{mount}: mounted")
            else:
                mount_details.append(f"{mount}: NOT mounted")

        points_per_mount = 6 // max(len(self.required_mounts), 1)
        mount_points_earned = mounted_count * points_per_mount
        # Cap at 6
        mount_points_earned = min(mount_points_earned, 6)

        if mounted_count == len(self.required_mounts):
            checks.append(ValidationCheck(
                name="mounts_active",
                passed=True,
                points=6,
                message=f"All {mounted_count} pseudo-filesystems are bind-mounted",
                details="; ".join(mount_details)
            ))
            total_points += 6
        elif mounted_count > 0:
            checks.append(ValidationCheck(
                name="mounts_active",
                passed=False,
                points=mount_points_earned,
                max_points=6,
                message=f"{mounted_count}/{len(self.required_mounts)} pseudo-filesystems mounted",
                details="; ".join(mount_details)
            ))
            total_points += mount_points_earned
        else:
            checks.append(ValidationCheck(
                name="mounts_active",
                passed=False,
                points=0,
                max_points=6,
                message="No pseudo-filesystems are bind-mounted into the chroot",
                details="; ".join(mount_details)
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 4. EmergencyTargetBootTask (exam / 10pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class EmergencyTargetBootTask(BaseTask):
    """Boot into emergency.target for system rescue."""

    def __init__(self):
        super().__init__(
            id="boot_recovery_emergency_target_001",
            category="boot_recovery",
            difficulty="exam",
            points=10
        )
        self.requires_persistence = False
        self.requires_reboot = True
        self.tags = ['systemd', 'emergency', 'rescue']
        self.exam_tips = [
            "emergency.target provides minimal environment with root filesystem only.",
            "rescue.target loads more services and is less restrictive.",
            "Append systemd.unit=emergency.target to kernel line in GRUB.",
            "On RHEL 10, emergency/rescue targets use sulogin - root password required.",
        ]
        self.target = None

    def generate(self, **params):
        """Generate emergency/rescue target boot task."""
        target_choices = [
            ('emergency.target', 'emergency', 'absolute minimal shell with only / mounted'),
            ('rescue.target', 'rescue', 'single-user mode with basic services running'),
        ]

        choice = params.get('target')
        if choice:
            for t, name, desc in target_choices:
                if t == choice:
                    self.target = t
                    target_name = name
                    target_desc = desc
                    break
            else:
                self.target = choice
                target_name = choice
                target_desc = 'the specified target'
        else:
            self.target, target_name, target_desc = random.choice(target_choices)

        self.description = (
            f"Configure the system to boot into {target_name} mode by default.\n"
            f"\n"
            f"Target: {self.target}\n"
            f"This target provides: {target_desc}.\n"
            f"\n"
            f"The change must be persistent — the system should boot into this target\n"
            f"on the next and all subsequent reboots, not just once."
        )

        self.hints = [
            "systemctl can manage the default boot target permanently",
            "Use 'systemctl --help' or 'man systemctl' to find the relevant subcommand",
            "Verify your change with a systemctl query before rebooting",
        ]

        return self

    def validate(self):
        """Validate system is configured for emergency/rescue target."""
        checks = []
        total_points = 0

        # Check 1: Default target is set correctly (6 points)
        result = execute_safe(['systemctl', 'get-default'])
        current_target = result.stdout.strip() if result.success else 'unknown'

        if current_target == self.target:
            checks.append(ValidationCheck(
                name="default_target_set",
                passed=True,
                points=6,
                message=f"Default target is correctly set to '{self.target}'"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="default_target_set",
                passed=False,
                points=0,
                max_points=6,
                message=f"Default target is '{current_target}', expected '{self.target}'"
            ))

        # Check 2: Verify the target unit exists and is loadable (4 points)
        result = execute_safe(['systemctl', 'cat', self.target])
        if result.success:
            checks.append(ValidationCheck(
                name="target_unit_available",
                passed=True,
                points=4,
                message=f"Target unit '{self.target}' is available on the system"
            ))
            total_points += 4
        else:
            # Try an alternative check
            result_alt = execute_safe(['systemctl', 'list-units', '--type=target', '--all'])
            target_found = False
            if result_alt.success and self.target in result_alt.stdout:
                target_found = True

            if target_found:
                checks.append(ValidationCheck(
                    name="target_unit_available",
                    passed=True,
                    points=4,
                    message=f"Target unit '{self.target}' found in system targets"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="target_unit_available",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Target unit '{self.target}' may not be available on this system"
                ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 5. FixBrokenFstabRecoveryTask (hard / 18pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class FixBrokenFstabRecoveryTask(BaseTask):
    """Fix invalid /etc/fstab entries that prevent the system from booting."""

    def __init__(self):
        super().__init__(
            id="boot_recovery_fix_fstab_001",
            category="boot_recovery",
            difficulty="hard",
            points=18
        )
        self.requires_persistence = True
        self.requires_reboot = True
        self.tags = ['fstab', 'troubleshooting', 'boot-failure']
        self.exam_tips = [
            "A single typo in /etc/fstab can prevent boot entirely.",
            "Always run 'findmnt --verify' and 'mount -a' BEFORE rebooting.",
            "Use 'nofail' on non-critical mounts to avoid boot failures.",
            "If locked out, boot with rd.break or emergency.target to fix fstab.",
            "Comment out broken lines rather than deleting them for audit purposes.",
        ]
        self.broken_entries = None
        self.mount_point = None
        self.bad_device = None

    def generate(self, **params):
        """Generate fstab recovery task with randomized broken entries."""
        broken_scenarios = [
            {
                'mount_point': '/data',
                'bad_device': '/dev/sdz1',
                'fs_type': 'xfs',
                'description': 'references non-existent device /dev/sdz1',
            },
            {
                'mount_point': '/backup',
                'bad_device': 'UUID=aaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
                'fs_type': 'ext4',
                'description': 'contains an invalid UUID that does not match any device',
            },
            {
                'mount_point': '/opt/appdata',
                'bad_device': '/dev/mapper/vg_missing-lv_data',
                'fs_type': 'xfs',
                'description': 'references a non-existent LVM logical volume',
            },
            {
                'mount_point': '/srv/nfs',
                'bad_device': '192.168.99.99:/exports/share',
                'fs_type': 'nfs',
                'description': 'has an unreachable NFS server address',
            },
            {
                'mount_point': '/mnt/external',
                'bad_device': '/dev/sdb1',
                'fs_type': 'vfat',
                'description': 'references a device that is not connected',
            },
        ]

        scenario = params.get('scenario', random.choice(broken_scenarios))
        self.mount_point = scenario['mount_point']
        self.bad_device = scenario['bad_device']
        self.broken_entries = scenario

        self.description = (
            f"Fix a broken /etc/fstab entry that prevents normal boot:\n"
            f"\n"
            f"  Problem: The fstab {scenario['description']}.\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Bad device: {self.bad_device}\n"
            f"  - Filesystem type: {scenario['fs_type']}\n"
            f"\n"
            f"  Required:\n"
            f"  1. Identify the problematic entry in /etc/fstab\n"
            f"  2. Either remove/comment out the entry, or fix it with valid values\n"
            f"  3. If keeping the entry, add the 'nofail' mount option\n"
            f"  4. Run 'findmnt --verify' to confirm no errors remain\n"
            f"  5. Run 'mount -a' to verify all remaining entries work\n"
            f"\n"
            f"  WARNING: On a real system, a broken fstab means the system\n"
            f"  drops to emergency mode (or fails to boot at all)."
        )

        self.hints = [
            "Open /etc/fstab with vi or nano and look for the bad entry",
            f"The broken line references '{self.bad_device}' mounted at '{self.mount_point}'",
            "Comment out with '#' or remove the broken line entirely",
            "Alternatively fix the device path and add 'nofail' option",
            "'findmnt --verify' validates fstab without mounting",
            "'mount -a' tests mounting all fstab entries",
            "If booted to emergency mode: mount -o remount,rw / first",
        ]

        return self

    def validate(self):
        """Validate fstab is fixed and bootable."""
        checks = []
        total_points = 0

        # Check 1: /etc/fstab exists (2 points)
        if not os.path.exists('/etc/fstab'):
            checks.append(ValidationCheck(
                name="fstab_exists",
                passed=False,
                points=0,
                max_points=2,
                message="/etc/fstab not found - critical error"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        checks.append(ValidationCheck(
            name="fstab_exists",
            passed=True,
            points=2,
            message="/etc/fstab exists"
        ))
        total_points += 2

        # Check 2: findmnt --verify passes (6 points)
        result = execute_safe(['findmnt', '--verify'])
        verify_output = (result.stdout or '') + (result.stderr or '')
        if result.success:
            checks.append(ValidationCheck(
                name="fstab_verify_clean",
                passed=True,
                points=6,
                message="findmnt --verify reports no fstab errors"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="fstab_verify_clean",
                passed=False,
                points=0,
                max_points=6,
                message=f"findmnt --verify found errors: {verify_output[:200]}"
            ))

        # Check 3: Bad entry removed or fixed (6 points)
        try:
            with open('/etc/fstab', 'r') as f:
                fstab_content = f.read()

            bad_entry_active = False
            for line in fstab_content.splitlines():
                stripped = line.strip()
                if stripped.startswith('#') or not stripped:
                    continue
                parts = stripped.split()
                if len(parts) >= 2:
                    # Check if the problematic device or mount point is still active without nofail
                    if parts[0] == self.bad_device and parts[1] == self.mount_point:
                        # Entry still present - check if it has nofail
                        if len(parts) >= 4 and 'nofail' in parts[3]:
                            bad_entry_active = False  # Fixed with nofail
                        else:
                            bad_entry_active = True

            if not bad_entry_active:
                checks.append(ValidationCheck(
                    name="bad_entry_fixed",
                    passed=True,
                    points=6,
                    message=f"Problematic fstab entry for {self.mount_point} has been fixed or removed"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="bad_entry_fixed",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=(
                        f"The broken entry for {self.bad_device} at {self.mount_point} "
                        f"is still active without 'nofail'. This will prevent boot."
                    )
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="bad_entry_fixed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Could not read /etc/fstab: {e}"
            ))

        # Check 4: mount -a succeeds (4 points)
        result = execute_safe(['mount', '-a'])
        if result.success:
            checks.append(ValidationCheck(
                name="mount_all_succeeds",
                passed=True,
                points=4,
                message="'mount -a' completed successfully - all fstab entries are mountable"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="mount_all_succeeds",
                passed=False,
                points=0,
                max_points=4,
                message=f"'mount -a' failed: {result.stderr}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ---------------------------------------------------------------------------
# 6. RecoverFromReadOnlyRootTask (hard / 15pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("boot_recovery")
class RecoverFromReadOnlyRootTask(BaseTask):
    """Remount a read-only root filesystem as read-write for recovery."""

    def __init__(self):
        super().__init__(
            id="boot_recovery_ro_root_001",
            category="boot_recovery",
            difficulty="hard",
            points=15
        )
        self.requires_persistence = True
        self.requires_reboot = True
        self.tags = ['mount', 'root-filesystem', 'emergency']
        self.exam_tips = [
            "In emergency mode, / is often mounted read-only.",
            "Use 'mount -o remount,rw /' to make it writable.",
            "After fixing issues, remount as read-write and verify with 'mount | grep \" / \"'.",
            "If root is on LVM, you may need to activate VGs first: vgchange -ay",
        ]
        self.additional_task = None

    def generate(self, **params):
        """Generate read-only root recovery task."""
        additional_tasks = [
            {
                'desc': 'create the file /root/recovery_marker.txt with content "recovery complete"',
                'file_path': '/root/recovery_marker.txt',
                'content': 'recovery complete',
            },
            {
                'desc': 'create the file /etc/recovery_verified with the current date',
                'file_path': '/etc/recovery_verified',
                'content': 'date',
            },
            {
                'desc': 'create the file /tmp/rw_test_passed with content "filesystem is writable"',
                'file_path': '/tmp/rw_test_passed',
                'content': 'filesystem is writable',
            },
            {
                'desc': 'create the file /root/rw_confirmed with content "root rw confirmed"',
                'file_path': '/root/rw_confirmed',
                'content': 'root rw confirmed',
            },
        ]

        self.additional_task = params.get('additional_task', random.choice(additional_tasks))

        self.description = (
            f"Recover from a read-only root filesystem:\n"
            f"\n"
            f"  Scenario: The system has booted into emergency mode and the\n"
            f"  root filesystem (/) is mounted read-only. You cannot modify\n"
            f"  any configuration files until it is remounted read-write.\n"
            f"\n"
            f"  Steps:\n"
            f"  1. Verify root is mounted read-only: mount | grep ' / '\n"
            f"  2. Remount root as read-write: mount -o remount,rw /\n"
            f"  3. Verify it is now read-write: mount | grep ' / '\n"
            f"  4. Prove write access by creating a test file:\n"
            f"     {self.additional_task['desc']}\n"
            f"  5. Ensure / remains read-write after changes (check /etc/fstab)"
        )

        self.hints = [
            "mount | grep ' / ' shows current mount options for root",
            "mount -o remount,rw /  remounts root read-write in place",
            "If LVM: vgchange -ay to activate volume groups",
            f"After remount: {self.additional_task['desc']}",
            "Check /etc/fstab to ensure root is not configured as 'ro'",
        ]

        return self

    def validate(self):
        """Validate root filesystem is read-write and test file exists."""
        checks = []
        total_points = 0

        # Check 1: Root filesystem is mounted read-write (6 points)
        result = execute_safe(['mount'])
        root_rw = False
        if result.success:
            for line in result.stdout.splitlines():
                # Look for the root mount: "... on / type ... (rw,...)"
                if ' / ' in line and ' type ' in line:
                    if '(rw' in line or ',rw' in line:
                        root_rw = True
                    break

        if root_rw:
            checks.append(ValidationCheck(
                name="root_is_rw",
                passed=True,
                points=6,
                message="Root filesystem (/) is mounted read-write"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="root_is_rw",
                passed=False,
                points=0,
                max_points=6,
                message="Root filesystem (/) is NOT mounted read-write. Run: mount -o remount,rw /"
            ))

        # Check 2: Test file created (5 points)
        test_file = self.additional_task['file_path']
        expected_content = self.additional_task['content']

        if os.path.exists(test_file):
            try:
                with open(test_file, 'r') as f:
                    file_content = f.read().strip()

                if expected_content == 'date':
                    # Any non-empty content is acceptable for date-based files
                    content_ok = len(file_content) > 0
                else:
                    content_ok = expected_content in file_content

                if content_ok:
                    checks.append(ValidationCheck(
                        name="test_file_created",
                        passed=True,
                        points=5,
                        message=f"Test file {test_file} exists with correct content"
                    ))
                    total_points += 5
                else:
                    checks.append(ValidationCheck(
                        name="test_file_created",
                        passed=False,
                        points=2,
                        max_points=5,
                        message=(
                            f"Test file {test_file} exists but content does not match. "
                            f"Expected '{expected_content}', got '{file_content[:80]}'"
                        )
                    ))
                    total_points += 2
            except Exception as e:
                checks.append(ValidationCheck(
                    name="test_file_created",
                    passed=False,
                    points=1,
                    max_points=5,
                    message=f"Test file {test_file} exists but cannot be read: {e}"
                ))
                total_points += 1
        else:
            checks.append(ValidationCheck(
                name="test_file_created",
                passed=False,
                points=0,
                max_points=5,
                message=f"Test file {test_file} not found"
            ))

        # Check 3: /etc/fstab does not force ro on root (4 points)
        fstab_ok = False
        try:
            with open('/etc/fstab', 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith('#') or not stripped:
                        continue
                    parts = stripped.split()
                    if len(parts) >= 4 and parts[1] == '/':
                        options = parts[3].split(',')
                        # Root should not have 'ro' as a permanent option
                        if 'ro' not in options:
                            fstab_ok = True
                        break
                else:
                    # No explicit root entry means system uses defaults (usually rw)
                    fstab_ok = True
        except Exception:
            fstab_ok = False

        if fstab_ok:
            checks.append(ValidationCheck(
                name="fstab_root_not_ro",
                passed=True,
                points=4,
                message="/etc/fstab does not force read-only mount on /"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="fstab_root_not_ro",
                passed=False,
                points=0,
                max_points=4,
                message="/etc/fstab has 'ro' option for root - remove it to prevent boot issues"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
