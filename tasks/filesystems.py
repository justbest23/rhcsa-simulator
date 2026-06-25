"""
Filesystem management tasks for RHCSA exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import (
    get_filesystem_type, validate_filesystem_type,
    get_block_device_uuid, get_mounted_devices,
    validate_persistent_mount, validate_swap_active, get_total_swap
)
from validators.file_validators import validate_file_contains
from utils.helpers import get_practice_device, get_practice_lv


logger = logging.getLogger(__name__)


@TaskRegistry.register("filesystems")
class CreateFilesystemTask(BaseTask):
    """Create a filesystem on a device."""

    def __init__(self):
        super().__init__(
            id="fs_create_001",
            category="filesystems",
            difficulty="easy",
            points=6
        )
        self.tags = ['v10-new', 'filesystem', 'mkfs']
        self.exam_tips = [
            "Use 'lsblk -f' or 'blkid' to verify filesystem type after creation",
            "XFS is the default filesystem in RHEL 9 - know both mkfs.xfs and mkfs.ext4",
            "Always verify the device path before formatting to avoid data loss",
        ]
        self.device = None
        self.fstype = None

    def generate(self, **params):
        """Generate filesystem creation task."""
        fstypes = [
            ('xfs', 'XFS (Red Hat default)'),
            ('ext4', 'ext4'),
        ]

        if params.get('fstype'):
            self.fstype = params['fstype']
            fstype_desc = next((desc for fs, desc in fstypes if fs == self.fstype), self.fstype)
        else:
            self.fstype, fstype_desc = random.choice(fstypes)

        self.device = params.get('device') or get_practice_device() or '/dev/vdb1'

        self.description = (
            f"Create a filesystem:\n"
            f"  - Device: {self.device}\n"
            f"  - Filesystem type: {fstype_desc}\n"
            f"  - Ensure the filesystem is properly formatted"
        )

        self.hints = [
            f"Use mkfs.{self.fstype} command",
            f"Format: mkfs.{self.fstype} {self.device}",
            "Verify with 'lsblk -f' or 'blkid'",
            "XFS: Use mkfs.xfs, ext4: Use mkfs.ext4"
        ]

        return self

    def validate(self):
        """Validate filesystem creation."""
        checks = []
        total_points = 0

        # Check: Filesystem type matches
        if validate_filesystem_type(self.device, self.fstype):
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=True,
                points=6,
                message=f"Filesystem type is correctly {self.fstype}"
            ))
            total_points += 6
        else:
            actual = get_filesystem_type(self.device)
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=False,
                points=0,
                max_points=6,
                message=f"Filesystem type is {actual}, expected {self.fstype}"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("filesystems")
class MountFilesystemTask(BaseTask):
    """Mount a filesystem at a specific mount point."""

    def __init__(self):
        super().__init__(
            id="fs_mount_001",
            category="filesystems",
            difficulty="easy",
            points=8
        )
        self.tags = ['v10-new', 'filesystem', 'mount']
        self.exam_tips = [
            "Create mount point with 'mkdir -p' before mounting",
            "Use 'mount | grep <mount_point>' or 'df -h' to verify the mount",
            "Temporary mounts with just 'mount' command won't survive reboot",
            "Use 'lsblk' to see all block devices and their mount points",
        ]
        self.device = None
        self.mount_point = None

    def generate(self, **params):
        """Generate mount task."""
        self.device = params.get('device') or get_practice_device() or '/dev/vdb1'
        self.mount_point = params.get('mount_point', f'/mnt/data{random.randint(1,99)}')

        self.description = (
            f"Mount a filesystem:\n"
            f"  - Device: {self.device}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Create mount point if it doesn't exist\n"
            f"  - Mount the filesystem"
        )

        self.hints = [
            f"Create mount point: mkdir -p {self.mount_point}",
            f"Mount filesystem: mount {self.device} {self.mount_point}",
            f"Verify with 'mount | grep {self.mount_point}' or 'df -h'",
            "Check with 'lsblk' to see mount points"
        ]

        return self

    def validate(self):
        """Validate filesystem is mounted."""
        checks = []
        total_points = 0

        mounts = get_mounted_devices()
        mounted = False

        for mount in mounts:
            if mount['mount_point'] == self.mount_point:
                mounted = True
                # Check if correct device is mounted
                if self.device in mount['device']:
                    checks.append(ValidationCheck(
                        name="correct_device",
                        passed=True,
                        points=4,
                        message=f"Correct device {self.device} mounted"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="correct_device",
                        passed=False,
                        points=0,
                        max_points=4,
                        message=f"Wrong device: {mount['device']} (expected {self.device})"
                    ))
                break

        if mounted:
            checks.append(ValidationCheck(
                name="filesystem_mounted",
                passed=True,
                points=4,
                message=f"Filesystem mounted at {self.mount_point}"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="filesystem_mounted",
                passed=False,
                points=0,
                max_points=4,
                message=f"Filesystem not mounted at {self.mount_point}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("filesystems")
class PersistentMountTask(BaseTask):
    """Configure persistent mount in /etc/fstab using UUID."""

    def __init__(self):
        super().__init__(
            id="fs_persistent_001",
            category="filesystems",
            difficulty="medium",
            points=12
        )
        self.tags = ['v10-new', 'filesystem', 'fstab', 'persistence']
        self.exam_tips = [
            "ALWAYS use UUID in /etc/fstab, not device names (get with 'blkid')",
            "Test fstab syntax with 'findmnt --verify' before rebooting",
            "Use 'mount -a' to test mounting all fstab entries without rebooting",
            "Format: UUID=<uuid> <mount_point> <fstype> <options> <dump> <pass>",
            "Typical options: 'defaults' or 'defaults,noatime' for performance",
        ]
        self.requires_persistence = True
        self.device = None
        self.mount_point = None
        self.fstype = None
        self.options = None

    def generate(self, **params):
        """Generate persistent mount task."""
        self.device = params.get('device') or get_practice_device() or '/dev/vdb1'
        self.mount_point = params.get('mount_point', f'/mnt/persistent{random.randint(1,99)}')
        self.fstype = params.get('fstype', random.choice(['xfs', 'ext4']))
        self.options = params.get('options', 'defaults')

        self.description = (
            f"Configure persistent filesystem mount:\n"
            f"  - Device: {self.device}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Filesystem type: {self.fstype}\n"
            f"  - Mount options: {self.options}\n"
            f"  - Use UUID in /etc/fstab (not device name)\n"
            f"  - Mount the filesystem now\n"
            f"  - Ensure it mounts automatically at boot"
        )

        self.hints = [
            f"Get UUID: blkid {self.device}",
            f"Create mount point: mkdir -p {self.mount_point}",
            "Edit /etc/fstab and add: UUID=<uuid> <mount_point> <fstype> <options> 0 0",
            "Mount all fstab entries: mount -a",
            f"Verify: mount | grep {self.mount_point}",
            "Test fstab syntax: findmnt --verify"
        ]

        return self

    def validate(self):
        """Validate persistent mount configuration."""
        checks = []
        total_points = 0

        # Check 1: Currently mounted (3 points)
        mounts = get_mounted_devices()
        currently_mounted = any(m['mount_point'] == self.mount_point for m in mounts)

        if currently_mounted:
            checks.append(ValidationCheck(
                name="currently_mounted",
                passed=True,
                points=3,
                message=f"Filesystem currently mounted at {self.mount_point}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="currently_mounted",
                passed=False,
                points=0,
                max_points=3,
                message=f"Filesystem not currently mounted"
            ))

        # Check 2: Entry in /etc/fstab (5 points)
        uuid = get_block_device_uuid(self.device)
        if uuid and validate_persistent_mount(uuid, self.mount_point, self.fstype):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=5,
                message=f"Entry exists in /etc/fstab with UUID"
            ))
            total_points += 5
        elif validate_persistent_mount(self.device, self.mount_point, self.fstype):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=3,
                message=f"Entry exists in /etc/fstab but not using UUID (partial credit)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=5,
                message=f"No persistent mount entry in /etc/fstab"
            ))

        # Check 3: Correct filesystem type (2 points)
        if validate_filesystem_type(self.device, self.fstype):
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=True,
                points=2,
                message=f"Filesystem type is {self.fstype}"
            ))
            total_points += 2
        else:
            actual = get_filesystem_type(self.device)
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=False,
                points=0,
                max_points=2,
                message=f"Filesystem is {actual}, expected {self.fstype}"
            ))

        # Check 4: Mount point exists (2 points)
        import os
        if os.path.exists(self.mount_point) and os.path.isdir(self.mount_point):
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=True,
                points=2,
                message=f"Mount point directory exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Mount point {self.mount_point} doesn't exist"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


class ConfigureSwapTask(BaseTask):
    """Swap configuration — lives in tasks/swap.py; kept here only to avoid import errors."""

    def __init__(self):
        super().__init__(
            id="fs_swap_001",
            category="filesystems",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new', 'swap', 'fstab', 'persistence']
        self.exam_tips = [
            "Format swap with 'mkswap <device>', activate with 'swapon <device>'",
            "Use UUID in /etc/fstab: UUID=<uuid> none swap defaults 0 0",
            "Verify active swap with 'swapon --show' or 'free -m'",
            "Get UUID with 'blkid <device>' before adding to fstab",
            "Swap must survive reboot - test with 'swapon -a' after editing fstab",
        ]
        self.requires_persistence = True
        self.device = None
        self.size_mb = None

    def generate(self, **params):
        """Generate swap configuration task."""
        from utils.helpers import get_swap_practice_device
        self.device = params.get('device') or get_swap_practice_device() or get_practice_device() or '/dev/sdb'
        self.size_mb = 0  # device determines size

        self.description = (
            f"Configure {self.device} as persistent swap space."
        )

        self.hints = [
            "mkswap formats a device as swap; swapon activates it",
            "Use blkid to get the UUID for a stable /etc/fstab entry",
            "fstab swap entry: UUID=... none swap defaults 0 0",
            "Verify: swapon --show",
        ]

        return self

    def validate(self):
        """Validate swap configuration."""
        checks = []
        total_points = 0

        # Check 1: Swap is active (5 points)
        if validate_swap_active(self.device):
            checks.append(ValidationCheck(
                name="swap_active",
                passed=True,
                points=5,
                message=f"Swap is active on {self.device}"
            ))
            total_points += 5
        else:
            # Try UUID
            uuid = get_block_device_uuid(self.device)
            if uuid and validate_swap_active(uuid):
                checks.append(ValidationCheck(
                    name="swap_active",
                    passed=True,
                    points=5,
                    message=f"Swap is active"
                ))
                total_points += 5
            else:
                checks.append(ValidationCheck(
                    name="swap_active",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Swap is not active on {self.device}"
                ))

        # Check 2: Persistent in /etc/fstab (5 points)
        uuid = get_block_device_uuid(self.device)
        if uuid and validate_file_contains('/etc/fstab', uuid):
            checks.append(ValidationCheck(
                name="swap_persistent",
                passed=True,
                points=5,
                message=f"Swap configured in /etc/fstab with UUID"
            ))
            total_points += 5
        elif validate_file_contains('/etc/fstab', self.device):
            checks.append(ValidationCheck(
                name="swap_persistent",
                passed=True,
                points=3,
                message=f"Swap in /etc/fstab but not using UUID (partial credit)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="swap_persistent",
                passed=False,
                points=0,
                max_points=5,
                message=f"Swap not configured in /etc/fstab"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("filesystems")
class ExtendFilesystemTask(BaseTask):
    """Extend/resize a filesystem (typically after LV extension)."""

    def __init__(self):
        super().__init__(
            id="fs_extend_001",
            category="filesystems",
            difficulty="exam",
            points=10
        )
        self.tags = ['v10-new', 'filesystem', 'resize', 'xfs', 'ext4']
        self.exam_tips = [
            "For XFS: use 'xfs_growfs <mount_point>' (requires mounted filesystem)",
            "For ext4: use 'resize2fs <device>' (can be done online for growth)",
            "XFS can only grow, never shrink - plan accordingly",
            "Always extend the underlying LV/partition before resizing filesystem",
            "Verify new size with 'df -h' after resizing",
        ]
        self.device = None
        self.fstype = None
        self.expected_size_mb = None

    def generate(self, **params):
        """Generate filesystem extend task."""
        # Try to detect existing practice LV
        vg, lv = get_practice_lv()
        if vg and lv:
            default_dev = f'/dev/mapper/{vg}-{lv}'
        else:
            default_dev = '/dev/mapper/vg_practice-lv_practice'
        self.device = params.get('device') or default_dev
        self.fstype = params.get('fstype', random.choice(['xfs', 'ext4']))
        self.expected_size_mb = params.get('size', random.choice([250, 300, 350]))

        resize_cmd = 'xfs_growfs' if self.fstype == 'xfs' else 'resize2fs'

        self.description = (
            f"Extend a filesystem:\n"
            f"  - Device: {self.device}\n"
            f"  - Filesystem type: {self.fstype}\n"
            f"  - Resize to approximately {self.expected_size_mb}MB\n"
            f"  - Filesystem must remain mounted (if applicable)\n"
            f"  - Data must not be lost\n"
            f"  - Note: if this LV does not exist yet, set up practice disks first (Setup → 1)"
        )

        self.hints = [
            "First extend the underlying LV with lvextend, then resize the filesystem",
            f"For XFS: xfs_growfs <mount_point> (must be mounted)",
            f"For ext4: resize2fs {self.device}",
            "XFS can only grow, never shrink",
            "Verify the new size with 'df -h' after resizing",
        ]

        return self

    def validate(self):
        """Validate filesystem has been extended."""
        checks = []
        total_points = 0

        # Check 1: Filesystem type correct (3 points)
        actual_fstype = get_filesystem_type(self.device)
        if actual_fstype == self.fstype:
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=True,
                points=3,
                message=f"Filesystem type is {self.fstype}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="filesystem_type",
                passed=False,
                points=0,
                max_points=3,
                message=f"Filesystem type is {actual_fstype}, expected {self.fstype}"
            ))

        # Check 2: Filesystem size (7 points)
        # This is a simplified check - in practice, we'd check the actual filesystem size
        # For now, just verify the filesystem exists and is accessible
        import os
        mounts = get_mounted_devices()
        mount_point = None
        for m in mounts:
            if self.device in m['device']:
                mount_point = m['mount_point']
                break

        if mount_point:
            try:
                stat = os.statvfs(mount_point)
                size_mb = (stat.f_blocks * stat.f_frsize) / (1024 * 1024)
                tolerance = self.expected_size_mb * 0.1  # 10% tolerance

                if abs(size_mb - self.expected_size_mb) <= tolerance:
                    checks.append(ValidationCheck(
                        name="filesystem_size",
                        passed=True,
                        points=7,
                        message=f"Filesystem size is approximately {int(size_mb)}MB"
                    ))
                    total_points += 7
                else:
                    checks.append(ValidationCheck(
                        name="filesystem_size",
                        passed=False,
                        points=0,
                        max_points=7,
                        message=f"Filesystem size is {int(size_mb)}MB, expected ~{self.expected_size_mb}MB"
                    ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="filesystem_size",
                    passed=False,
                    points=0,
                    max_points=7,
                    message=f"Could not check filesystem size: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="filesystem_accessible",
                passed=False,
                points=0,
                max_points=7,
                message=f"Filesystem not mounted or not accessible"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


class CreateSwapFileTask(BaseTask):
    """Swap file task — lives in tasks/swap.py; kept here only to avoid import errors."""

    def __init__(self):
        super().__init__(
            id="fs_swapfile_001",
            category="filesystems",
            difficulty="exam",
            points=12
        )
        self.tags = ['v10-new', 'swap', 'swapfile', 'fstab', 'persistence']
        self.exam_tips = [
            "Create file: 'dd if=/dev/zero of=/swapfile bs=1M count=<size>' or 'fallocate -l <size>M /swapfile'",
            "CRITICAL: Set permissions to 600 with 'chmod 600 /swapfile' for security",
            "Format with 'mkswap /swapfile', activate with 'swapon /swapfile'",
            "Add to /etc/fstab: /swapfile none swap defaults 0 0 (no UUID for files)",
            "Verify with 'swapon --show' - should show the file path and size",
        ]
        self.requires_persistence = True
        self.swap_file = None
        self.size_mb = None

    def generate(self, **params):
        self.swap_file = params.get('file', '/swapfile')
        self.size_mb = params.get('size', random.choice([256, 512, 1024]))

        self.description = (
            f"Create a {self.size_mb}MB persistent swap file at {self.swap_file}."
        )

        self.hints = [
            "fallocate or dd can create a fixed-size file",
            "Swap files must have permissions 600 before mkswap will accept them",
            "fstab entry for a swap file uses the file path directly, not a UUID",
            "Verify with swapon --show",
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0
        import os
        import stat

        # Check 1: Swap file exists (3 points)
        if os.path.exists(self.swap_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=3,
                message=f"Swap file exists"
            ))
            total_points += 3

            # Check 2: Correct permissions (2 points)
            file_stat = os.stat(self.swap_file)
            perms = stat.S_IMODE(file_stat.st_mode)
            if perms == 0o600:
                checks.append(ValidationCheck(
                    name="permissions_correct",
                    passed=True,
                    points=2,
                    message=f"Permissions are 600"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="permissions_correct",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Permissions are {oct(perms)}, expected 0o600"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Swap file not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 3: Swap is active (4 points)
        if validate_swap_active(self.swap_file):
            checks.append(ValidationCheck(
                name="swap_active",
                passed=True,
                points=4,
                message=f"Swap file is active"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="swap_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Swap file is not active"
            ))

        # Check 4: In /etc/fstab (3 points)
        if validate_file_contains('/etc/fstab', self.swap_file):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=3,
                message=f"Entry in /etc/fstab"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=3,
                message=f"Not in /etc/fstab"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("filesystems")
class UnmountFilesystemTask(BaseTask):
    """Safely unmount a filesystem."""

    def __init__(self):
        super().__init__(
            id="fs_unmount_001",
            category="filesystems",
            difficulty="easy",
            points=6
        )
        self.tags = ['v10-new', 'filesystem', 'unmount']
        self.exam_tips = [
            "Check for processes using the filesystem with 'lsof <mount_point>' or 'fuser -m <mount_point>'",
            "Use 'umount <mount_point>' to unmount (note: umount, not unmount)",
            "If filesystem is busy, use 'umount -l' for lazy unmount as last resort",
            "Verify unmount success with 'mount | grep <mount_point>' (should return nothing)",
        ]
        self.mount_point = None

    def generate(self, **params):
        self.mount_point = params.get('mount_point', f'/mnt/data{random.randint(1,99)}')

        self.description = (
            f"Unmount a filesystem:\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Ensure no processes are using the filesystem\n"
            f"  - Safely unmount the filesystem\n"
            f"  - Remove the mount point directory (optional)"
        )

        self.hints = [
            f"Check for users: lsof {self.mount_point}",
            f"Or: fuser -m {self.mount_point}",
            f"Unmount: umount {self.mount_point}",
            "If busy, use: umount -l (lazy unmount) as last resort",
            f"Verify: mount | grep {self.mount_point}"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        mounts = get_mounted_devices()
        is_mounted = any(m['mount_point'] == self.mount_point for m in mounts)

        if not is_mounted:
            checks.append(ValidationCheck(
                name="unmounted",
                passed=True,
                points=6,
                message=f"Filesystem successfully unmounted"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="unmounted",
                passed=False,
                points=0,
                max_points=6,
                message=f"Filesystem is still mounted at {self.mount_point}"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
