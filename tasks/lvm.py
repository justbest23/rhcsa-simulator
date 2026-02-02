"""
LVM (Logical Volume Management) tasks for RHCSA exam.
"""

import random
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import validate_lv_exists, get_lv_size_mb
from utils.helpers import get_practice_device, get_all_practice_devices, get_practice_lv, get_practice_vg


@TaskRegistry.register("lvm")
class VerifyLVExistsTask(BaseTask):
    """Verify logical volume exists with correct size."""

    def __init__(self):
        super().__init__(
            id="lvm_verify_001",
            category="lvm",
            difficulty="exam",
            points=10
        )
        self.vg_name = None
        self.lv_name = None
        self.lv_size_mb = None

    def generate(self, **params):
        self.vg_name = params.get('vg_name', f'vg_exam{random.randint(1,99)}')
        self.lv_name = params.get('lv_name', f'lv_data{random.randint(1,99)}')
        self.lv_size_mb = params.get('size', random.choice([500, 1000, 2000]))

        self.description = (
            f"Create a logical volume with these specifications:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}\n"
            f"  - Size: {self.lv_size_mb}MB\n"
            f"\n"
            f"Note: Assume VG already exists or create it if needed"
        )

        self.hints = [
            "Use lvcreate command",
            "Format: lvcreate -L <size>M -n <lv_name> <vg_name>",
            "Verify with 'lvs' command"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_exists", True, 5, f"Logical volume exists"))
            total_points += 5

            actual_size = get_lv_size_mb(self.vg_name, self.lv_name)
            tolerance = self.lv_size_mb * 0.05
            if actual_size and abs(actual_size - self.lv_size_mb) <= tolerance:
                checks.append(ValidationCheck("lv_size", True, 5, f"Size correct: ~{actual_size}MB"))
                total_points += 5
            else:
                checks.append(ValidationCheck("lv_size", False, 0, f"Size incorrect: {actual_size}MB (expected {self.lv_size_mb}MB)", max_points=5))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"Logical volume not found", max_points=5))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class CreatePVTask(BaseTask):
    """Create a physical volume."""

    def __init__(self):
        super().__init__(
            id="lvm_pv_create_001",
            category="lvm",
            difficulty="easy",
            points=6
        )
        self.device = None

    def generate(self, **params):
        # Use provided device, or detect an available one
        self.device = params.get('device')
        if not self.device:
            self.device = get_practice_device()
        if not self.device:
            self.device = '/dev/vdb'  # Fallback for display

        self.description = (
            f"Create a physical volume:\n"
            f"  - Device: {self.device}\n"
            f"  - Initialize for LVM use\n"
            f"  - Verify PV is created"
        )

        self.hints = [
            f"Create PV: pvcreate {self.device}",
            "List PVs: pvs or pvdisplay",
            f"Verify: pvs {self.device}",
            "May need to partition device first with fdisk/parted"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        from validators.safe_executor import execute_safe

        # Check: PV exists
        result = execute_safe(['pvs', '--noheadings', self.device])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck("pv_exists", True, 6, f"Physical volume created on {self.device}"))
            total_points += 6
        else:
            checks.append(ValidationCheck("pv_exists", False, 0, f"Physical volume not found on {self.device}", max_points=6))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class CreateVGTask(BaseTask):
    """Create a volume group."""

    def __init__(self):
        super().__init__(
            id="lvm_vg_create_001",
            category="lvm",
            difficulty="medium",
            points=8
        )
        self.vg_name = None
        self.pv_devices = None

    def generate(self, **params):
        self.vg_name = params.get('vg_name', f'vg_data{random.randint(1,99)}')
        self.pv_devices = params.get('devices')
        if not self.pv_devices:
            # Detect available device
            device = get_practice_device()
            self.pv_devices = [device] if device else ['/dev/vdb']
        if isinstance(self.pv_devices, str):
            self.pv_devices = [self.pv_devices]

        devices_str = ' '.join(self.pv_devices)

        self.description = (
            f"Create a volume group:\n"
            f"  - VG name: {self.vg_name}\n"
            f"  - Physical volumes: {devices_str}\n"
            f"  - Use all specified devices\n"
            f"  - Verify VG is active"
        )

        self.hints = [
            f"Create VG: vgcreate {self.vg_name} {devices_str}",
            "List VGs: vgs or vgdisplay",
            f"Verify: vgs {self.vg_name}",
            "Ensure PVs are created first with pvcreate"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        from validators.safe_executor import execute_safe

        # Check: VG exists
        result = execute_safe(['vgs', '--noheadings', self.vg_name])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck("vg_exists", True, 8, f"Volume group '{self.vg_name}' created"))
            total_points += 8
        else:
            checks.append(ValidationCheck("vg_exists", False, 0, f"Volume group '{self.vg_name}' not found", max_points=8))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class CreateLVTask(BaseTask):
    """Create a logical volume with specific size."""

    def __init__(self):
        super().__init__(
            id="lvm_lv_create_001",
            category="lvm",
            difficulty="medium",
            points=10
        )
        self.vg_name = None
        self.lv_name = None
        self.lv_size_mb = None

    def generate(self, **params):
        # Try to detect existing practice LV
        existing_vg, existing_lv = get_practice_lv()
        if existing_vg and existing_lv:
            self.vg_name = params.get('vg_name', existing_vg)
            self.lv_name = params.get('lv_name', existing_lv)
        else:
            self.vg_name = params.get('vg_name', 'vg_practice')
            self.lv_name = params.get('lv_name', 'lv_practice')
        self.lv_size_mb = params.get('size', random.choice([500, 1000, 2000]))

        self.description = (
            f"Create a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - LV name: {self.lv_name}\n"
            f"  - Size: {self.lv_size_mb}MB\n"
            f"  - Verify LV is created and active"
        )

        self.hints = [
            f"Create LV: lvcreate -L {self.lv_size_mb}M -n {self.lv_name} {self.vg_name}",
            "List LVs: lvs or lvdisplay",
            f"Verify: lvs {self.vg_name}/{self.lv_name}",
            "LV device path: /dev/{vg_name}/{lv_name}",
            "Ensure VG exists first"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: LV exists (5 points)
        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_exists", True, 5, f"Logical volume created"))
            total_points += 5

            # Check 2: LV size (5 points)
            actual_size = get_lv_size_mb(self.vg_name, self.lv_name)
            tolerance = self.lv_size_mb * 0.05
            if actual_size and abs(actual_size - self.lv_size_mb) <= tolerance:
                checks.append(ValidationCheck("lv_size", True, 5, f"Size correct: ~{actual_size}MB"))
                total_points += 5
            else:
                checks.append(ValidationCheck("lv_size", False, 0, f"Size incorrect: {actual_size}MB (expected {self.lv_size_mb}MB)", max_points=5))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"Logical volume not found", max_points=5))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class ExtendLVTask(BaseTask):
    """Extend a logical volume."""

    def __init__(self):
        super().__init__(
            id="lvm_extend_001",
            category="lvm",
            difficulty="exam",
            points=12
        )
        self.vg_name = None
        self.lv_name = None
        self.new_size_mb = None
        self.extend_by_mb = None

    def generate(self, **params):
        # Try to detect existing practice LV
        existing_vg, existing_lv = get_practice_lv()
        if existing_vg and existing_lv:
            self.vg_name = params.get('vg_name', existing_vg)
            self.lv_name = params.get('lv_name', existing_lv)
        else:
            self.vg_name = params.get('vg_name', 'vg_practice')
            self.lv_name = params.get('lv_name', 'lv_practice')
        self.extend_by_mb = params.get('extend_by', random.choice([500, 1000]))
        self.new_size_mb = params.get('new_size', random.choice([1500, 2500, 3000]))

        use_extend_by = params.get('use_extend_by', True)

        if use_extend_by:
            task_spec = f"extend by {self.extend_by_mb}MB"
            hint_cmd = f"lvextend -L +{self.extend_by_mb}M /dev/{self.vg_name}/{self.lv_name}"
        else:
            task_spec = f"resize to {self.new_size_mb}MB total"
            hint_cmd = f"lvextend -L {self.new_size_mb}M /dev/{self.vg_name}/{self.lv_name}"

        self.description = (
            f"Extend a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}\n"
            f"  - Task: {task_spec}\n"
            f"  - Ensure LV is extended"
        )

        self.hints = [
            f"Extend LV: {hint_cmd}",
            "Check current size: lvs or lvdisplay",
            "Extend by amount: lvextend -L +<size>M /dev/vg/lv",
            "Resize to total: lvextend -L <size>M /dev/vg/lv",
            "Use all free space: lvextend -l +100%FREE /dev/vg/lv",
            "After extending, resize filesystem with xfs_growfs or resize2fs"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_exists", True, 4, f"LV exists"))
            total_points += 4

            actual_size = get_lv_size_mb(self.vg_name, self.lv_name)
            # Check if LV has been extended (allow some tolerance)
            if actual_size and actual_size >= self.extend_by_mb:
                checks.append(ValidationCheck("lv_extended", True, 8, f"LV size is {actual_size}MB (extended)"))
                total_points += 8
            else:
                checks.append(ValidationCheck("lv_extended", False, 0, f"LV size is {actual_size}MB (may not be extended)", max_points=8))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"LV not found", max_points=4))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class LVMFullWorkflowTask(BaseTask):
    """Complete LVM workflow: Create PV, VG, LV, format, and mount."""

    def __init__(self):
        super().__init__(
            id="lvm_full_workflow_001",
            category="lvm",
            difficulty="exam",
            points=20
        )
        self.device = None
        self.vg_name = None
        self.lv_name = None
        self.lv_size_mb = None
        self.mount_point = None
        self.fstype = None

    def generate(self, **params):
        # Use provided device, or detect an available one
        self.device = params.get('device')
        if not self.device:
            self.device = get_practice_device()
        if not self.device:
            self.device = '/dev/vdb'  # Fallback for display

        self.vg_name = params.get('vg_name', f'vg_exam{random.randint(1,99)}')
        self.lv_name = params.get('lv_name', f'lv_data{random.randint(1,99)}')
        self.lv_size_mb = params.get('size', random.choice([1000, 1500, 2000]))
        self.mount_point = params.get('mount', f'/mnt/lvm{random.randint(1,99)}')
        self.fstype = params.get('fstype', 'xfs')

        self.description = (
            f"Complete LVM setup:\n"
            f"  1. Create PV on {self.device}\n"
            f"  2. Create VG '{self.vg_name}' using the PV\n"
            f"  3. Create LV '{self.lv_name}' ({self.lv_size_mb}MB) in the VG\n"
            f"  4. Format LV with {self.fstype} filesystem\n"
            f"  5. Mount at {self.mount_point}\n"
            f"  6. Configure for persistent mounting (/etc/fstab with UUID)\n"
            f"  \n"
            f"  All steps must be completed successfully."
        )

        self.hints = [
            f"Step 1: pvcreate {self.device}",
            f"Step 2: vgcreate {self.vg_name} {self.device}",
            f"Step 3: lvcreate -L {self.lv_size_mb}M -n {self.lv_name} {self.vg_name}",
            f"Step 4: mkfs.{self.fstype} /dev/{self.vg_name}/{self.lv_name}",
            f"Step 5: mkdir -p {self.mount_point} && mount /dev/{self.vg_name}/{self.lv_name} {self.mount_point}",
            f"Step 6: Add to /etc/fstab with UUID (get with blkid)",
            "Full path: /dev/mapper/{vg_name}-{lv_name}"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0
        from validators.system_validators import get_filesystem_type, get_mounted_devices
        from validators.safe_executor import execute_safe

        # Check 1: PV exists (3 points)
        result = execute_safe(['pvs', '--noheadings', self.device])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck("pv_created", True, 3, "Physical volume created"))
            total_points += 3
        else:
            checks.append(ValidationCheck("pv_created", False, 0, "PV not created", max_points=3))

        # Check 2: VG exists (4 points)
        result = execute_safe(['vgs', '--noheadings', self.vg_name])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck("vg_created", True, 4, f"Volume group '{self.vg_name}' created"))
            total_points += 4
        else:
            checks.append(ValidationCheck("vg_created", False, 0, "VG not created", max_points=4))

        # Check 3: LV exists with correct size (4 points)
        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_created", True, 4, "Logical volume created"))
            total_points += 4
        else:
            checks.append(ValidationCheck("lv_created", False, 0, "LV not created", max_points=4))

        # Check 4: Filesystem formatted (3 points)
        lv_path = f'/dev/{self.vg_name}/{self.lv_name}'
        fstype = get_filesystem_type(lv_path)
        if fstype == self.fstype:
            checks.append(ValidationCheck("fs_formatted", True, 3, f"Filesystem formatted as {self.fstype}"))
            total_points += 3
        else:
            checks.append(ValidationCheck("fs_formatted", False, 0, f"Filesystem not formatted or wrong type", max_points=3))

        # Check 5: Mounted (3 points)
        mounts = get_mounted_devices()
        mounted = any(m['mount_point'] == self.mount_point for m in mounts)
        if mounted:
            checks.append(ValidationCheck("lv_mounted", True, 3, f"Mounted at {self.mount_point}"))
            total_points += 3
        else:
            checks.append(ValidationCheck("lv_mounted", False, 0, "Not mounted", max_points=3))

        # Check 6: Persistent mount (3 points)
        from validators.file_validators import validate_file_contains
        if validate_file_contains('/etc/fstab', self.mount_point):
            checks.append(ValidationCheck("persistent_mount", True, 3, "Entry in /etc/fstab"))
            total_points += 3
        else:
            checks.append(ValidationCheck("persistent_mount", False, 0, "No fstab entry", max_points=3))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
