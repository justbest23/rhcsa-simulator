"""
Advanced storage tasks for RHCSA 9 exam.
Includes Stratis, VDO, and advanced LVM operations.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains
from utils.helpers import get_practice_device


logger = logging.getLogger(__name__)


# ============================================================================
# STRATIS STORAGE TASKS (RHCSA 9)
# ============================================================================

@TaskRegistry.register("storage")
class CreateStratisPoolTask(BaseTask):
    """Create a Stratis storage pool."""

    def __init__(self):
        super().__init__(
            id="stratis_pool_001",
            category="storage",
            difficulty="exam",
            points=8
        )
        self.pool_name = None
        self.device = None

    def generate(self, **params):
        """Generate Stratis pool creation task."""
        pool_num = random.randint(1, 99)
        self.pool_name = params.get('pool_name', f'stratispool{pool_num}')
        self.device = params.get('device') or get_practice_device() or '/dev/sdc'

        self.description = (
            f"Create a Stratis storage pool:\n"
            f"  - Pool name: {self.pool_name}\n"
            f"  - Block device: {self.device}\n"
            f"  - Ensure stratisd service is running"
        )

        self.hints = [
            "Install stratis: dnf install stratisd stratis-cli",
            "Start service: systemctl enable --now stratisd",
            f"Create pool: stratis pool create {self.pool_name} {self.device}",
            "List pools: stratis pool list",
        ]

        self.learn_content = {
            'concept': "Stratis is a local storage management solution that provides "
                      "easy-to-use management of pools, filesystems, and snapshots. "
                      "It's designed for modern Linux systems and simplifies storage administration.",
            'when_to_use': "Use Stratis when you need managed local storage with "
                          "easy snapshot and thin provisioning capabilities.",
        }

        return self

    def validate(self):
        """Validate Stratis pool creation."""
        checks = []
        total_points = 0

        # Check 1: stratisd service running (2 points)
        result = execute_safe(['systemctl', 'is-active', 'stratisd'])
        if result.success and 'active' in result.stdout:
            checks.append(ValidationCheck(
                name="stratisd_active",
                passed=True,
                points=2,
                message="stratisd service is running"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="stratisd_active",
                passed=False,
                points=0,
                max_points=2,
                message="stratisd service is not running"
            ))

        # Check 2: Pool exists (6 points)
        result = execute_safe(['stratis', 'pool', 'list'])
        if result.success and self.pool_name in result.stdout:
            checks.append(ValidationCheck(
                name="pool_exists",
                passed=True,
                points=6,
                message=f"Stratis pool '{self.pool_name}' exists"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="pool_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Stratis pool '{self.pool_name}' not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class CreateStratisFilesystemTask(BaseTask):
    """Create a filesystem on a Stratis pool."""

    def __init__(self):
        super().__init__(
            id="stratis_fs_001",
            category="storage",
            difficulty="exam",
            points=10
        )
        self.pool_name = None
        self.fs_name = None
        self.mountpoint = None

    def generate(self, **params):
        """Generate Stratis filesystem task."""
        fs_num = random.randint(1, 99)
        self.pool_name = params.get('pool_name', 'stratispool1')
        self.fs_name = params.get('fs_name', f'stratisfs{fs_num}')
        self.mountpoint = params.get('mountpoint', f'/mnt/stratis{fs_num}')

        self.description = (
            f"Create a Stratis filesystem:\n"
            f"  - Pool: {self.pool_name}\n"
            f"  - Filesystem name: {self.fs_name}\n"
            f"  - Mount at: {self.mountpoint}\n"
            f"  - Configure persistent mount in /etc/fstab"
        )

        self.hints = [
            f"Create filesystem: stratis filesystem create {self.pool_name} {self.fs_name}",
            f"Create mountpoint: mkdir -p {self.mountpoint}",
            "List filesystems: stratis filesystem list",
            "Use x-systemd.requires=stratisd.service in fstab mount options",
            f"Device path: /dev/stratis/{self.pool_name}/{self.fs_name}",
        ]

        return self

    def validate(self):
        """Validate Stratis filesystem."""
        checks = []
        total_points = 0

        # Check 1: Filesystem exists (4 points)
        result = execute_safe(['stratis', 'filesystem', 'list'])
        if result.success and self.fs_name in result.stdout:
            checks.append(ValidationCheck(
                name="fs_exists",
                passed=True,
                points=4,
                message=f"Stratis filesystem '{self.fs_name}' exists"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="fs_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Stratis filesystem '{self.fs_name}' not found"
            ))

        # Check 2: Mountpoint exists (2 points)
        if validate_file_exists(self.mountpoint, file_type='directory'):
            checks.append(ValidationCheck(
                name="mountpoint_exists",
                passed=True,
                points=2,
                message=f"Mount point exists: {self.mountpoint}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mountpoint_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Mount point missing: {self.mountpoint}"
            ))

        # Check 3: Currently mounted (2 points)
        result = execute_safe(['findmnt', self.mountpoint])
        if result.success:
            checks.append(ValidationCheck(
                name="mounted",
                passed=True,
                points=2,
                message="Filesystem is mounted"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mounted",
                passed=False,
                points=0,
                max_points=2,
                message="Filesystem is not mounted"
            ))

        # Check 4: fstab entry (2 points)
        if validate_file_contains('/etc/fstab', self.mountpoint):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=2,
                message="Persistent mount configured in /etc/fstab"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=2,
                message="No fstab entry found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class CreateStratisSnapshotTask(BaseTask):
    """Create a snapshot of a Stratis filesystem."""

    def __init__(self):
        super().__init__(
            id="stratis_snapshot_001",
            category="storage",
            difficulty="hard",
            points=8
        )
        self.pool_name = None
        self.fs_name = None
        self.snapshot_name = None

    def generate(self, **params):
        """Generate Stratis snapshot task."""
        self.pool_name = params.get('pool_name', 'stratispool1')
        self.fs_name = params.get('fs_name', 'stratisfs1')
        self.snapshot_name = params.get('snapshot_name', f'{self.fs_name}-snap')

        self.description = (
            f"Create a Stratis snapshot:\n"
            f"  - Pool: {self.pool_name}\n"
            f"  - Source filesystem: {self.fs_name}\n"
            f"  - Snapshot name: {self.snapshot_name}"
        )

        self.hints = [
            f"Create snapshot: stratis filesystem snapshot {self.pool_name} {self.fs_name} {self.snapshot_name}",
            "List all filesystems: stratis filesystem list",
            "Snapshots appear as regular filesystems",
        ]

        return self

    def validate(self):
        """Validate Stratis snapshot."""
        checks = []
        total_points = 0

        # Check: Snapshot exists
        result = execute_safe(['stratis', 'filesystem', 'list'])
        if result.success and self.snapshot_name in result.stdout:
            checks.append(ValidationCheck(
                name="snapshot_exists",
                passed=True,
                points=8,
                message=f"Snapshot '{self.snapshot_name}' exists"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="snapshot_exists",
                passed=False,
                points=0,
                max_points=8,
                message=f"Snapshot '{self.snapshot_name}' not found"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ============================================================================
# ADVANCED LVM TASKS
# ============================================================================

@TaskRegistry.register("lvm")
class ExtendLogicalVolumeTask(BaseTask):
    """Extend an LVM logical volume."""

    def __init__(self):
        super().__init__(
            id="lvm_extend_001",
            category="lvm",
            difficulty="exam",
            points=8
        )
        self.vg_name = None
        self.lv_name = None
        self.new_size = None

    def generate(self, **params):
        """Generate LV extension task."""
        self.vg_name = params.get('vg_name', 'datavg')
        self.lv_name = params.get('lv_name', 'datalv')
        self.new_size = params.get('new_size', '800M')

        self.description = (
            f"Extend a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}\n"
            f"  - New size: {self.new_size}\n"
            f"  - Resize the filesystem to use the new space"
        )

        self.hints = [
            f"Extend LV: lvextend -L {self.new_size} /dev/{self.vg_name}/{self.lv_name}",
            "Or use relative size: lvextend -L +200M ...",
            "Resize XFS: xfs_growfs /mountpoint",
            "Resize ext4: resize2fs /dev/vg/lv",
            "One command: lvextend -r -L {size} /dev/vg/lv",
        ]

        return self

    def validate(self):
        """Validate LV extension."""
        checks = []
        total_points = 0

        # Check 1: LV exists (2 points)
        result = execute_safe(['lvs', f'{self.vg_name}/{self.lv_name}'])
        if result.success:
            checks.append(ValidationCheck(
                name="lv_exists",
                passed=True,
                points=2,
                message=f"Logical volume exists"
            ))
            total_points += 2

            # Check 2: LV size (6 points)
            result = execute_safe(['lvs', '--noheadings', '-o', 'lv_size', '--units', 'm',
                                  f'{self.vg_name}/{self.lv_name}'])
            if result.success:
                try:
                    size_str = result.stdout.strip().replace('m', '').replace('M', '').replace('<', '')
                    current_size = float(size_str)
                    target_size = float(self.new_size.replace('M', '').replace('G', ''))
                    if 'G' in self.new_size:
                        target_size *= 1024

                    if current_size >= target_size * 0.95:  # Allow 5% tolerance
                        checks.append(ValidationCheck(
                            name="lv_size",
                            passed=True,
                            points=6,
                            message=f"LV size is correct: {current_size:.0f}M"
                        ))
                        total_points += 6
                    else:
                        checks.append(ValidationCheck(
                            name="lv_size",
                            passed=False,
                            points=0,
                            max_points=6,
                            message=f"LV too small: {current_size:.0f}M (need {self.new_size})"
                        ))
                except:
                    checks.append(ValidationCheck(
                        name="lv_size",
                        passed=False,
                        points=0,
                        max_points=6,
                        message="Could not determine LV size"
                    ))
        else:
            checks.append(ValidationCheck(
                name="lv_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Logical volume not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class CreateLVMThinPoolTask(BaseTask):
    """Create an LVM thin pool for thin provisioning."""

    def __init__(self):
        super().__init__(
            id="lvm_thinpool_001",
            category="lvm",
            difficulty="hard",
            points=12
        )
        self.vg_name = None
        self.pool_name = None
        self.pool_size = None

    def generate(self, **params):
        """Generate thin pool task."""
        self.vg_name = params.get('vg_name', 'datavg')
        self.pool_name = params.get('pool_name', 'thinpool')
        self.pool_size = params.get('pool_size', '500M')

        self.description = (
            f"Create an LVM thin pool:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Thin pool name: {self.pool_name}\n"
            f"  - Pool size: {self.pool_size}\n"
            f"\n"
            f"Then create a thin logical volume:\n"
            f"  - Name: thinvol1\n"
            f"  - Virtual size: 1G"
        )

        self.hints = [
            f"Create thin pool: lvcreate -T -L {self.pool_size} {self.vg_name}/{self.pool_name}",
            f"Create thin LV: lvcreate -T -V 1G -n thinvol1 {self.vg_name}/{self.pool_name}",
            "List thin pools: lvs -o+pool_lv",
        ]

        return self

    def validate(self):
        """Validate thin pool creation."""
        checks = []
        total_points = 0

        # Check 1: Thin pool exists (6 points)
        result = execute_safe(['lvs', '--noheadings', '-o', 'lv_attr',
                              f'{self.vg_name}/{self.pool_name}'])
        if result.success and 't' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="thinpool_exists",
                passed=True,
                points=6,
                message=f"Thin pool '{self.pool_name}' exists"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="thinpool_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Thin pool '{self.pool_name}' not found"
            ))

        # Check 2: Thin volume exists (6 points)
        result = execute_safe(['lvs', '--noheadings', '-o', 'pool_lv',
                              f'{self.vg_name}/thinvol1'])
        if result.success and self.pool_name in result.stdout:
            checks.append(ValidationCheck(
                name="thinvol_exists",
                passed=True,
                points=6,
                message="Thin volume 'thinvol1' exists in pool"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="thinvol_exists",
                passed=False,
                points=0,
                max_points=6,
                message="Thin volume 'thinvol1' not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ============================================================================
# SWAP MANAGEMENT
# ============================================================================

@TaskRegistry.register("storage")
class ConfigureSwapFileTask(BaseTask):
    """Configure a swap file."""

    def __init__(self):
        super().__init__(
            id="swap_file_001",
            category="storage",
            difficulty="easy",
            points=6
        )
        self.swap_file = None
        self.size_mb = None

    def generate(self, **params):
        """Generate swap file task."""
        self.swap_file = params.get('swap_file', '/swapfile2')
        self.size_mb = params.get('size_mb', 256)

        self.description = (
            f"Configure a swap file:\n"
            f"  - Path: {self.swap_file}\n"
            f"  - Size: {self.size_mb}MB\n"
            f"  - Activate the swap\n"
            f"  - Make persistent in /etc/fstab"
        )

        self.hints = [
            f"Create file: dd if=/dev/zero of={self.swap_file} bs=1M count={self.size_mb}",
            f"Or use: fallocate -l {self.size_mb}M {self.swap_file}",
            f"Set permissions: chmod 600 {self.swap_file}",
            f"Format: mkswap {self.swap_file}",
            f"Activate: swapon {self.swap_file}",
            f"fstab: {self.swap_file} swap swap defaults 0 0",
        ]

        return self

    def validate(self):
        """Validate swap file configuration."""
        checks = []
        total_points = 0

        # Check 1: Swap file exists (2 points)
        if validate_file_exists(self.swap_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=2,
                message=f"Swap file exists: {self.swap_file}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Swap file not found: {self.swap_file}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Swap is active (2 points)
        result = execute_safe(['swapon', '--show'])
        if result.success and self.swap_file in result.stdout:
            checks.append(ValidationCheck(
                name="swap_active",
                passed=True,
                points=2,
                message="Swap is active"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="swap_active",
                passed=False,
                points=0,
                max_points=2,
                message="Swap is not active"
            ))

        # Check 3: fstab entry (2 points)
        if validate_file_contains('/etc/fstab', self.swap_file):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=2,
                message="Swap configured in /etc/fstab"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=2,
                message="No fstab entry for swap"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class ConfigureSwapPartitionTask(BaseTask):
    """Configure swap on an LVM logical volume."""

    def __init__(self):
        super().__init__(
            id="swap_lvm_001",
            category="storage",
            difficulty="exam",
            points=8
        )
        self.vg_name = None
        self.lv_name = None
        self.size = None

    def generate(self, **params):
        """Generate LVM swap task."""
        self.vg_name = params.get('vg_name', 'datavg')
        self.lv_name = params.get('lv_name', 'swaplv')
        self.size = params.get('size', '256M')

        self.description = (
            f"Configure swap on an LVM logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}\n"
            f"  - Size: {self.size}\n"
            f"  - Activate and make persistent"
        )

        self.hints = [
            f"Create LV: lvcreate -L {self.size} -n {self.lv_name} {self.vg_name}",
            f"Format: mkswap /dev/{self.vg_name}/{self.lv_name}",
            f"Activate: swapon /dev/{self.vg_name}/{self.lv_name}",
            f"fstab: /dev/{self.vg_name}/{self.lv_name} swap swap defaults 0 0",
        ]

        return self

    def validate(self):
        """Validate LVM swap configuration."""
        checks = []
        total_points = 0
        device_path = f"/dev/{self.vg_name}/{self.lv_name}"

        # Check 1: LV exists (2 points)
        result = execute_safe(['lvs', f'{self.vg_name}/{self.lv_name}'])
        if result.success:
            checks.append(ValidationCheck(
                name="lv_exists",
                passed=True,
                points=2,
                message=f"Logical volume exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="lv_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Logical volume not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Is swap type (2 points)
        result = execute_safe(['blkid', '-o', 'value', '-s', 'TYPE', device_path])
        if result.success and 'swap' in result.stdout:
            checks.append(ValidationCheck(
                name="is_swap",
                passed=True,
                points=2,
                message="LV is formatted as swap"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="is_swap",
                passed=False,
                points=0,
                max_points=2,
                message="LV is not formatted as swap"
            ))

        # Check 3: Swap active (2 points)
        result = execute_safe(['swapon', '--show'])
        if result.success and self.lv_name in result.stdout:
            checks.append(ValidationCheck(
                name="swap_active",
                passed=True,
                points=2,
                message="Swap is active"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="swap_active",
                passed=False,
                points=0,
                max_points=2,
                message="Swap is not active"
            ))

        # Check 4: fstab entry (2 points)
        if validate_file_contains('/etc/fstab', self.lv_name) or validate_file_contains('/etc/fstab', device_path):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=2,
                message="Swap configured in /etc/fstab"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=2,
                message="No fstab entry for swap"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ============================================================================
# RAID TASKS
# ============================================================================

@TaskRegistry.register("storage")
class CreateRAIDArrayTask(BaseTask):
    """Create a RAID array using mdadm."""

    def __init__(self):
        super().__init__(
            id="raid_create_001",
            category="storage",
            difficulty="hard",
            points=12
        )
        self.raid_level = None
        self.devices = None
        self.md_device = None

    def generate(self, **params):
        """Generate RAID creation task."""
        self.raid_level = params.get('level', 1)
        self.devices = params.get('devices', ['/dev/sdb1', '/dev/sdc1'])
        self.md_device = params.get('md_device', '/dev/md0')

        self.description = (
            f"Create a RAID array:\n"
            f"  - RAID level: {self.raid_level}\n"
            f"  - Devices: {', '.join(self.devices)}\n"
            f"  - MD device: {self.md_device}\n"
            f"  - Create filesystem and mount at /mnt/raid"
        )

        device_str = ' '.join(self.devices)
        self.hints = [
            "Install mdadm: dnf install mdadm",
            f"Create array: mdadm --create {self.md_device} --level={self.raid_level} --raid-devices={len(self.devices)} {device_str}",
            f"Watch sync: cat /proc/mdstat",
            f"Create filesystem: mkfs.ext4 {self.md_device}",
            "Mount: mkdir -p /mnt/raid && mount /dev/md0 /mnt/raid"
        ]

        return self

    def validate(self):
        """Validate RAID array creation."""
        checks = []
        total_points = 0

        # Check 1: MD device exists (4 points)
        result = execute_safe(['mdadm', '--detail', self.md_device])
        if result.success:
            checks.append(ValidationCheck(
                name="md_exists",
                passed=True,
                points=4,
                message=f"RAID device {self.md_device} exists"
            ))
            total_points += 4

            # Check RAID level (3 points)
            if f"raid{self.raid_level}" in result.stdout.lower() or f"Raid Level : raid{self.raid_level}" in result.stdout:
                checks.append(ValidationCheck(
                    name="raid_level",
                    passed=True,
                    points=3,
                    message=f"RAID level is {self.raid_level}"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="raid_level",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"RAID level mismatch"
                ))
        else:
            checks.append(ValidationCheck(
                name="md_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"RAID device {self.md_device} not found"
            ))

        # Check 2: Filesystem exists (3 points)
        result = execute_safe(['blkid', self.md_device])
        if result.success and ('ext4' in result.stdout or 'xfs' in result.stdout):
            checks.append(ValidationCheck(
                name="has_fs",
                passed=True,
                points=3,
                message="Filesystem created on RAID"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="has_fs",
                passed=False,
                points=0,
                max_points=3,
                message="No filesystem on RAID"
            ))

        # Check 3: Mounted (2 points)
        result = execute_safe(['findmnt', '/mnt/raid'])
        if result.success:
            checks.append(ValidationCheck(
                name="mounted",
                passed=True,
                points=2,
                message="RAID is mounted"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mounted",
                passed=False,
                points=0,
                max_points=2,
                message="RAID is not mounted"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class PersistentRAIDTask(BaseTask):
    """Make RAID configuration persistent."""

    def __init__(self):
        super().__init__(
            id="raid_persist_001",
            category="storage",
            difficulty="medium",
            points=10
        )
        self.md_device = None
        self.mountpoint = None

    def generate(self, **params):
        """Generate persistent RAID task."""
        self.md_device = params.get('md_device', '/dev/md0')
        self.mountpoint = params.get('mountpoint', '/mnt/raid')

        self.description = (
            f"Make RAID configuration persistent:\n"
            f"  - RAID device: {self.md_device}\n"
            f"  - Mount point: {self.mountpoint}\n"
            f"  - Save mdadm configuration\n"
            f"  - Add fstab entry for automount"
        )

        self.hints = [
            "Save config: mdadm --detail --scan >> /etc/mdadm.conf",
            "Or: mdadm --examine --scan >> /etc/mdadm.conf",
            "Update initramfs: dracut --regenerate-all --force",
            f"fstab entry using UUID: blkid {self.md_device}",
            f"fstab: UUID=xxx {self.mountpoint} ext4 defaults 0 0"
        ]

        return self

    def validate(self):
        """Validate persistent RAID configuration."""
        checks = []
        total_points = 0

        # Check 1: mdadm.conf has entry (5 points)
        if validate_file_contains('/etc/mdadm.conf', 'ARRAY'):
            checks.append(ValidationCheck(
                name="mdadm_conf",
                passed=True,
                points=5,
                message="RAID config saved in /etc/mdadm.conf"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="mdadm_conf",
                passed=False,
                points=0,
                max_points=5,
                message="No ARRAY entry in /etc/mdadm.conf"
            ))

        # Check 2: fstab entry (5 points)
        if validate_file_contains('/etc/fstab', self.mountpoint):
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=True,
                points=5,
                message=f"Mount entry for {self.mountpoint} in fstab"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=5,
                message="No fstab entry for RAID mount"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class ManageRAIDArrayTask(BaseTask):
    """Monitor and manage a RAID array."""

    def __init__(self):
        super().__init__(
            id="raid_manage_001",
            category="storage",
            difficulty="medium",
            points=8
        )
        self.md_device = None
        self.output_file = None

    def generate(self, **params):
        """Generate RAID management task."""
        self.md_device = params.get('md_device', '/dev/md0')
        self.output_file = params.get('output', '/tmp/raid_status.txt')

        self.description = (
            f"Monitor RAID array status:\n"
            f"  - RAID device: {self.md_device}\n"
            f"  - Save detailed status to: {self.output_file}\n"
            f"  - Include sync status and device health"
        )

        self.hints = [
            f"Get status: mdadm --detail {self.md_device}",
            "Check sync: cat /proc/mdstat",
            "Examine members: mdadm --examine /dev/sdX1",
            f"Save: mdadm --detail {self.md_device} > {self.output_file}"
        ]

        return self

    def validate(self):
        """Validate RAID status output."""
        checks = []
        total_points = 0

        # Check 1: Output file exists (4 points)
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=4,
                message="Status file created"
            ))
            total_points += 4

            # Check content (4 points)
            if validate_file_contains(self.output_file, 'ARRAY') or \
               validate_file_contains(self.output_file, 'Raid Level') or \
               validate_file_contains(self.output_file, 'State'):
                checks.append(ValidationCheck(
                    name="has_content",
                    passed=True,
                    points=4,
                    message="File contains RAID information"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="has_content",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="File missing RAID details"
                ))
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=4,
                message="Status file not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("storage")
class StopRemoveRAIDTask(BaseTask):
    """Stop and remove a RAID array."""

    def __init__(self):
        super().__init__(
            id="raid_remove_001",
            category="storage",
            difficulty="medium",
            points=8
        )
        self.md_device = None

    def generate(self, **params):
        """Generate RAID removal task."""
        self.md_device = params.get('md_device', '/dev/md0')

        self.description = (
            f"Stop and remove a RAID array:\n"
            f"  - RAID device: {self.md_device}\n"
            f"  - Unmount filesystem first\n"
            f"  - Stop the array\n"
            f"  - Zero superblocks on member disks"
        )

        self.hints = [
            "Unmount: umount /mnt/raid",
            f"Stop array: mdadm --stop {self.md_device}",
            "Zero superblocks: mdadm --zero-superblock /dev/sdb1 /dev/sdc1",
            "Remove from mdadm.conf if present",
            "Update initramfs: dracut --regenerate-all --force"
        ]

        return self

    def validate(self):
        """Validate RAID removal."""
        checks = []
        total_points = 0

        # Check: MD device no longer exists
        result = execute_safe(['mdadm', '--detail', self.md_device])
        if not result.success or 'No such file' in result.stderr:
            checks.append(ValidationCheck(
                name="md_removed",
                passed=True,
                points=8,
                message=f"RAID device {self.md_device} removed"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="md_removed",
                passed=False,
                points=0,
                max_points=8,
                message=f"RAID device {self.md_device} still exists"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
