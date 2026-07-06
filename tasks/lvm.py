"""
LVM (Logical Volume Management) tasks for RHCSA exam.
"""

import random
import string
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import validate_lv_exists, get_lv_size_mb
from validators.safe_executor import execute_safe
from utils.helpers import get_practice_device, get_all_practice_devices, get_practice_lv, get_practice_vg


def _uid(n=4):
    """Short random suffix so concurrent scratch VGs/LVs never share a name."""
    return ''.join(random.choices(string.digits, k=n))


def _scratch_setup(task, device, vg, lv=None, lv_mb=150, fstype=None):
    """Provision a practice VG (and optional LV) on `device` for a task that
    would otherwise assume pre-existing LVM. Records fault state for crash
    recovery. Returns (ok, message)."""
    import subprocess as _sp
    from tasks.troubleshooting import save_fault_state
    if not device:
        return False, "No practice device available — run 'Setup → 1' first"
    r = _sp.run(['pvcreate', '-ff', '-y', device], capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"pvcreate {device} failed: {r.stderr.strip()}"
    r = _sp.run(['vgcreate', vg, device], capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"vgcreate {vg} failed: {r.stderr.strip()}"
    if lv:
        r = _sp.run(['lvcreate', '-L', f'{lv_mb}M', '-n', lv, vg], capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"lvcreate {lv} failed: {r.stderr.strip()}"
        if fstype == 'ext4':
            _sp.run(['mkfs.ext4', '-F', f'/dev/{vg}/{lv}'], capture_output=True)
        elif fstype == 'xfs':
            _sp.run(['mkfs.xfs', '-f', f'/dev/{vg}/{lv}'], capture_output=True)
    save_fault_state(task.id, {'vg': vg, 'dev': device})
    return True, f"Provisioned {vg}" + (f"/{lv}" if lv else "")


def _scratch_teardown(task, vg, device):
    """Tear down a scratch VG/device created by _scratch_setup."""
    import subprocess as _sp
    from tasks.troubleshooting import clear_fault_state
    if vg:
        _sp.run(['lvremove', '-ff', vg], capture_output=True)
        _sp.run(['vgchange', '-an', vg], capture_output=True)
        _sp.run(['vgremove', '-ff', vg], capture_output=True)
    if device:
        _sp.run(['pvremove', '-ff', '-y', device], capture_output=True)
        _sp.run(['wipefs', '-a', device], capture_output=True)
    clear_fault_state(task.id)
    return True, f"Removed {vg}"


@TaskRegistry.register("lvm")
class VerifyLVExistsTask(BaseTask):
    """Verify logical volume exists with correct size."""

    disk_slots = 1

    def __init__(self):
        super().__init__(
            id="lvm_verify_001",
            category="lvm",
            difficulty="exam",
            points=10
        )
        self.task_order = 36
        self.tags = ['lvm-basics']
        self.exam_tips = [
            "Use 'lvs' or 'lvdisplay' to verify logical volume exists",
            "LV size may vary slightly due to extent alignment",
            "Path format: /dev/vg_name/lv_name or /dev/mapper/vg_name-lv_name",
        ]
        self.device = None
        self.vg_name = None
        self.lv_name = None
        self.lv_size_mb = None

    def generate(self, **params):
        # Name the target disk in the question — the candidate builds the VG
        # from scratch here, and without a named device they'd have to guess
        # which practice disk is safe to consume (see also exam device pool).
        self.device = params.get('device') or get_practice_device() or '/dev/loop0'
        self.vg_name = params.get('vg_name', f'vg_exam{random.randint(1,99)}')
        self.lv_name = params.get('lv_name', f'lv_data{random.randint(1,99)}')
        self.lv_size_mb = params.get('size', random.choice([300, 350, 400]))

        self.description = (
            f"Create a {self.lv_size_mb}MB logical volume named '{self.lv_name}' "
            f"in volume group '{self.vg_name}'. Create the VG first if it does "
            f"not exist, using the disk {self.device}."
        )

        self.hints = [
            f"pvcreate {self.device}",
            f"vgcreate {self.vg_name} {self.device}",
            "lvcreate creates a logical volume in an existing VG",
            "Use -L for size in MB and -n for the LV name",
            "Verify with: lvs and pvs",
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
                checks.append(ValidationCheck("lv_size", True, 3, f"Size correct: ~{actual_size}MB"))
                total_points += 3
            else:
                checks.append(ValidationCheck("lv_size", False, 0, f"Size incorrect: {actual_size}MB (expected {self.lv_size_mb}MB)", max_points=3))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"Logical volume not found", max_points=5))

        # VG built on the disk the question assigned (a partition on it counts)
        result = execute_safe(['pvs', '--noheadings', '-o', 'pv_name,vg_name'])
        on_device = False
        if result.success:
            for line in result.stdout.splitlines():
                parts = line.split()
                if (len(parts) >= 2 and parts[1] == self.vg_name
                        and parts[0].startswith(self.device)):
                    on_device = True
        if on_device:
            checks.append(ValidationCheck("vg_on_assigned_disk", True, 2,
                          f"VG uses the assigned disk {self.device}"))
            total_points += 2
        else:
            checks.append(ValidationCheck("vg_on_assigned_disk", False, 0,
                          f"VG does not use the assigned disk {self.device}",
                          max_points=2))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class CreatePVTask(BaseTask):
    """Create a physical volume."""

    disk_slots = 1

    def __init__(self):
        super().__init__(
            id="lvm_pv_create_001",
            category="lvm",
            difficulty="easy",
            points=6
        )
        self.task_order = 10
        self.tags = ['lvm-basics']
        self.exam_tips = [
            "Use 'pvcreate' to initialize a partition or disk for LVM use",
            "Verify with 'pvs' or 'pvdisplay' commands",
            "May need to create a partition first using fdisk or parted with type 8e (LVM)",
        ]
        self.requires_persistence = True
        self.device = None

    def generate(self, **params):
        # Use provided device, or detect an available one
        self.device = params.get('device')
        if not self.device:
            self.device = get_practice_device()
        if not self.device:
            self.device = '/dev/vdb'  # Fallback for display

        self.description = (
            f"Initialize {self.device} as a physical volume for LVM use."
        )

        self.hints = [
            "pvcreate initializes a block device as an LVM physical volume",
            "Verify with: pvs",
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

    disk_slots = 1

    def __init__(self):
        super().__init__(
            id="lvm_vg_create_001",
            category="lvm",
            difficulty="medium",
            points=8
        )
        self.task_order = 20
        self.tags = ['lvm-basics']
        self.exam_tips = [
            "Use 'vgcreate' to create a volume group from one or more physical volumes",
            "Physical volumes must be initialized with pvcreate first",
            "Verify with 'vgs' or 'vgdisplay' to see VG size and free space",
        ]
        self.requires_persistence = True
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
            f"Create volume group '{self.vg_name}' using {devices_str}. "
            f"Initialize the device as a PV first if needed."
        )

        self.hints = [
            "vgcreate takes a VG name followed by one or more PV devices",
            "PVs must be initialized with pvcreate first",
            "Verify with: vgs",
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

    disk_slots = 1
    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="lvm_lv_create_001",
            category="lvm",
            difficulty="medium",
            points=10
        )
        self.task_order = 30
        self.tags = ['lvm-basics']
        self.exam_tips = [
            "Use 'lvcreate -L <size>M -n <name> <vg_name>' to create a logical volume",
            "Can also use -l option to specify size in extents or percentage",
            "Verify with 'lvs' or 'lvdisplay' commands",
            "LV device appears at /dev/vg_name/lv_name",
        ]
        self.requires_persistence = True
        self.device = None
        self.vg_name = None
        self.lv_name = None
        self.lv_size_mb = None

    def generate(self, **params):
        # Self-contained: a scratch VG is provisioned on an allocated device at
        # exam time; the candidate creates the LV inside it.
        self.device = params.get('device') or get_practice_device() or '/dev/loop0'
        uid = _uid()
        self.vg_name = params.get('vg_name', f'vg_prac{uid}')
        self.lv_name = params.get('lv_name', f'lv_data{uid}')
        self.lv_size_mb = params.get('size', random.choice([300, 350, 400]))

        self.description = (
            f"Create a {self.lv_size_mb}MB logical volume named '{self.lv_name}' "
            f"in volume group '{self.vg_name}'."
        )

        self.hints = [
            "lvcreate creates a logical volume in an existing VG",
            "Use -L for size in MB and -n for the LV name",
            "LV device path: /dev/<vg_name>/<lv_name>",
            "Verify with: lvs or lvdisplay",
        ]

        return self

    def inject_fault(self):
        return _scratch_setup(self, self.device, self.vg_name)

    def restore_fault(self):
        return _scratch_teardown(self, self.vg_name, self.device)

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

    disk_slots = 1
    has_fault_injection = True
    _INITIAL_MB = 100

    def __init__(self):
        super().__init__(
            id="lvm_extend_001",
            category="lvm",
            difficulty="exam",
            points=12
        )
        self.task_order = 50
        self.tags = ['lvm-extend', 'exam-critical']
        self.exam_tips = [
            "Use 'lvextend -L +<size>M' to extend by amount, or -L <size>M for total size",
            "Use -l +100%FREE to use all remaining VG space",
            "After extending LV, must resize the filesystem: xfs_growfs for XFS, resize2fs for ext4",
            "Can combine steps with 'lvextend -r' to resize filesystem automatically",
            "Common exam task - practice both extending LV and filesystem",
        ]
        self.requires_persistence = True
        self.device = None
        self.vg_name = None
        self.lv_name = None
        self.target_mb = None
        self.extend_by_mb = None

    def generate(self, **params):
        # Self-contained: provision a small scratch LV that the candidate extends.
        self.device = params.get('device') or get_practice_device() or '/dev/loop0'
        uid = _uid()
        self.vg_name = params.get('vg_name', f'vg_prac{uid}')
        self.lv_name = params.get('lv_name', f'lv_data{uid}')
        self.extend_by_mb = params.get('extend_by', random.choice([100, 150]))
        self.target_mb = self._INITIAL_MB + self.extend_by_mb

        self.description = (
            f"Extend a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}  (currently {self._INITIAL_MB}MB)\n"
            f"  - Task: extend by {self.extend_by_mb}MB (to ~{self.target_mb}MB)\n"
            f"  - Ensure LV is extended"
        )

        self.hints = [
            f"Extend LV: lvextend -L +{self.extend_by_mb}M /dev/{self.vg_name}/{self.lv_name}",
            "Check current size: lvs or lvdisplay",
            "Extend by amount: lvextend -L +<size>M /dev/vg/lv",
            "Use all free space: lvextend -l +100%FREE /dev/vg/lv",
            "After extending, resize filesystem with xfs_growfs or resize2fs"
        ]

        return self

    def inject_fault(self):
        return _scratch_setup(self, self.device, self.vg_name,
                              lv=self.lv_name, lv_mb=self._INITIAL_MB)

    def restore_fault(self):
        return _scratch_teardown(self, self.vg_name, self.device)

    def validate(self):
        checks = []
        total_points = 0

        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_exists", True, 4, f"LV exists"))
            total_points += 4

            actual_size = get_lv_size_mb(self.vg_name, self.lv_name)
            # Require the LV to have actually grown toward the target size.
            if actual_size and actual_size >= self.target_mb * 0.95:
                checks.append(ValidationCheck("lv_extended", True, 8, f"LV size is {actual_size}MB (extended)"))
                total_points += 8
            else:
                checks.append(ValidationCheck("lv_extended", False, 0, f"LV size is {actual_size}MB (expected ~{self.target_mb}MB)", max_points=8))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"LV not found", max_points=4))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class LVMFullWorkflowTask(BaseTask):
    """Complete LVM workflow: Create PV, VG, LV, format, and mount."""

    disk_slots = 1

    def __init__(self):
        super().__init__(
            id="lvm_full_workflow_001",
            category="lvm",
            difficulty="exam",
            points=20
        )
        self.task_order = 35
        self.tags = ['lvm-workflow', 'exam-critical', 'fstab']
        self.exam_tips = [
            "Complete LVM workflow: pvcreate → vgcreate → lvcreate → mkfs → mount → fstab",
            "Use UUID in /etc/fstab for persistent mounting (get with blkid)",
            "Test fstab with 'mount -a' before rebooting",
            "XFS is default filesystem in RHEL 10, but ext4 also commonly used",
            "This is a common multi-step exam task worth significant points",
        ]
        self.requires_persistence = True
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
        # RHEL 10 mkfs.xfs refuses filesystems <= 300MB, so keep XFS sizes above
        # that. Loop practice disks are 500MB, so 350-450MB fits comfortably.
        self.fstype = params.get('fstype', 'xfs')
        default_sizes = [350, 400, 450] if self.fstype == 'xfs' else [200, 300, 400]
        self.lv_size_mb = params.get('size', random.choice(default_sizes))
        self.mount_point = params.get('mount', f'/mnt/lvm{random.randint(1,99)}')

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
            f"The LVM stack is: physical volume → volume group → logical volume → filesystem → mount",
            f"pvcreate initializes {self.device} as a PV; vgcreate builds a VG on top of it",
            f"lvcreate -L <size>M -n <name> <vg> creates a logical volume",
            f"Format with mkfs.{self.fstype}, then mount and add to /etc/fstab using UUID",
            f"Test persistence: mount -a (should not error after fstab edit)",
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

        # Check 6: Persistent mount (3 points) — require a real source field, not
        # just the mount point appearing somewhere (a broken "UUID= <mp>" line
        # must NOT pass).
        fstab_ok = False
        try:
            with open('/etc/fstab') as f:
                for line in f:
                    s = line.split('#', 1)[0].split()
                    if len(s) >= 2 and s[1] == self.mount_point:
                        source = s[0]
                        if source and source not in ('UUID=', 'LABEL='):
                            fstab_ok = True
                            break
        except OSError:
            pass
        if fstab_ok:
            checks.append(ValidationCheck("persistent_mount", True, 3, "Valid entry in /etc/fstab"))
            total_points += 3
        else:
            checks.append(ValidationCheck("persistent_mount", False, 0, "No valid fstab entry", max_points=3))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class ExtendVGTask(BaseTask):
    """
    Fault-injection: creates vg_practice on loop0 at start, uses loop1
    (or sda) as the device to add. User must pvcreate + vgextend.
    """

    disk_slots = 2

    has_fault_injection = True
    _VG = 'vg_practice'

    def __init__(self):
        super().__init__(
            id="lvm_vg_extend_001",
            category="lvm",
            difficulty="exam",
            points=10
        )
        self.task_order = 40
        self.tags = ['lvm-extend', 'fault-injection']
        self.exam_tips = [
            "pvcreate initializes a disk/device as a physical volume.",
            "vgextend <vg> <device> adds a PV to an existing VG.",
            "vgs shows VG size — verify it increased after vgextend.",
            "Free space in the VG can then be used with lvcreate or lvextend.",
        ]
        self.requires_persistence = True
        self.vg_name = self._VG
        self.base_device = None   # device the VG is built on (injected)
        self.new_device = None    # device user must add

    def generate(self, **params):
        from utils.helpers import (device_allocation_active, allocate_practice_device,
                                    get_loop_devices)
        self.vg_name = params.get('vg_name', f'vg_ext{_uid()}')

        # Needs two distinct devices: one to build the VG on, one to add.
        if device_allocation_active():
            self.base_device = params.get('base_device') or allocate_practice_device() or '/dev/loop0'
            self.new_device = params.get('new_device') or allocate_practice_device() or '/dev/loop1'
        else:
            loops = get_loop_devices()
            if len(loops) >= 2:
                self.base_device, self.new_device = loops[0], loops[1]
            elif len(loops) == 1:
                self.base_device, self.new_device = loops[0], '/dev/sda'
            else:
                self.base_device, self.new_device = '/dev/loop0', '/dev/loop1'

        self.description = (
            f"Extend a volume group:\n"
            f"  - Volume group: {self.vg_name}  (already exists)\n"
            f"  - Add new physical volume from: {self.new_device}\n"
            f"  - Initialize the new device as a PV first\n"
            f"  - Extend the VG to include the new PV\n"
            f"  - Verify the VG size has increased"
        )
        self.hints = [
            "Confirm the VG exists before extending: vgs",
            "A new device must be initialized as a PV before it can join a VG",
            f"Add the new PV to the existing VG using vgextend",
            "Verify the VG grew: vgs (check the VSize column)",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        vg = self.vg_name
        dev = self.base_device

        r = _sp.run(['pvcreate', '-ff', '-y', dev], capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"pvcreate {dev} failed: {r.stderr.strip()}"

        r = _sp.run(['vgcreate', vg, dev], capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"vgcreate {vg} failed: {r.stderr.strip()}"

        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'vg': vg, 'base_dev': dev, 'new_dev': self.new_device})
        return True, f"Created {vg} on {dev}; user must add {self.new_device}"

    def restore_fault(self):
        import subprocess as _sp
        from tasks.troubleshooting import load_fault_state, clear_fault_state

        state = load_fault_state(self.id)
        info = state.get('restore_info', {}) if state else {}
        vg = info.get('vg', self.vg_name)
        base_dev = info.get('base_dev', self.base_device)
        new_dev = info.get('new_dev', self.new_device)

        # Remove any LVs first
        _sp.run(['lvremove', '-ff', vg], capture_output=True)
        _sp.run(['vgchange', '-an', vg], capture_output=True)
        _sp.run(['vgremove', '-ff', vg], capture_output=True)
        for dev in filter(None, [base_dev, new_dev]):
            _sp.run(['pvremove', '-ff', '-y', dev], capture_output=True)
            _sp.run(['wipefs', '-a', dev], capture_output=True)

        clear_fault_state(self.id)
        return True, f"Removed {vg} and cleaned up PVs"

    def validate(self):
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: PV exists on new device (4 points)
        result = execute_safe(['pvs', '--noheadings', self.new_device])
        if result.success and result.stdout.strip():
            checks.append(ValidationCheck("pv_exists", True, 4, f"PV created on {self.new_device}"))
            total_points += 4
        else:
            checks.append(ValidationCheck("pv_exists", False, 0, f"PV not found on {self.new_device}", max_points=4))

        # Check 2: PV is part of VG (6 points)
        result = execute_safe(['pvs', '--noheadings', '-o', 'vg_name', self.new_device])
        if result.success and self.vg_name in result.stdout:
            checks.append(ValidationCheck("pv_in_vg", True, 6, f"Device added to {self.vg_name}"))
            total_points += 6
        else:
            checks.append(ValidationCheck("pv_in_vg", False, 0, f"Device not part of {self.vg_name}", max_points=6))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class RemoveLVTask(BaseTask):
    """Remove a logical volume safely."""

    disk_slots = 1
    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="lvm_lv_remove_001",
            category="lvm",
            difficulty="medium",
            points=8
        )
        self.task_order = 60
        self.tags = ['lvm-management']
        self.exam_tips = [
            "Must unmount LV before removing: 'umount /dev/vg/lv'",
            "Remove fstab entry to prevent boot errors",
            "Use 'lvremove /dev/vg/lv' or 'lvremove -f' to force",
            "Verify removal with 'lvs' command",
        ]
        self.requires_persistence = True
        self.device = None
        self.vg_name = None
        self.lv_name = None

    def generate(self, **params):
        # Self-contained: provision a scratch VG+LV the candidate must remove.
        self.device = params.get('device') or get_practice_device() or '/dev/loop0'
        uid = _uid()
        self.vg_name = params.get('vg_name', f'vg_test{uid}')
        self.lv_name = params.get('lv_name', f'lv_remove{uid}')

        self.description = (
            f"Remove a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume to remove: {self.lv_name}\n"
            f"  - Ensure LV is unmounted first\n"
            f"  - Remove the fstab entry if exists\n"
            f"  - Safely remove the logical volume"
        )

        self.hints = [
            f"Unmount first: umount /dev/{self.vg_name}/{self.lv_name}",
            "Edit /etc/fstab to remove any entry for this LV",
            f"Remove LV: lvremove /dev/{self.vg_name}/{self.lv_name}",
            "Use -f flag to force removal: lvremove -f ...",
            "Verify removal: lvs"
        ]

        return self

    def inject_fault(self):
        return _scratch_setup(self, self.device, self.vg_name,
                              lv=self.lv_name, lv_mb=100)

    def restore_fault(self):
        return _scratch_teardown(self, self.vg_name, self.device)

    def validate(self):
        checks = []
        total_points = 0

        # Check: LV should NOT exist
        if not validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_removed", True, 8, f"Logical volume successfully removed"))
            total_points += 8
        else:
            checks.append(ValidationCheck("lv_removed", False, 0, f"Logical volume still exists", max_points=8))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("lvm")
class ReduceLVTask(BaseTask):
    """Reduce a logical volume (ext4 only - XFS cannot shrink)."""

    disk_slots = 1
    has_fault_injection = True
    _INITIAL_MB = 350

    def __init__(self):
        super().__init__(
            id="lvm_lv_reduce_001",
            category="lvm",
            difficulty="hard",
            points=15
        )
        self.task_order = 60
        self.tags = ['lvm-advanced']
        self.exam_tips = [
            "CRITICAL: XFS filesystems CANNOT be reduced - only ext4/ext3 support shrinking",
            "Always resize filesystem BEFORE reducing LV to avoid data loss",
            "Workflow: unmount → e2fsck -f → resize2fs → lvreduce → remount",
            "Reducing LVs is risky and rarely tested on exam - extending is much more common",
        ]
        self.requires_persistence = True
        self.device = None
        self.vg_name = None
        self.lv_name = None
        self.new_size_mb = None

    def generate(self, **params):
        # Self-contained: provision an ext4 LV (larger than target) to reduce.
        self.device = params.get('device') or get_practice_device() or '/dev/loop0'
        uid = _uid()
        self.vg_name = params.get('vg_name', f'vg_prac{uid}')
        self.lv_name = params.get('lv_name', f'lv_data{uid}')
        self.new_size_mb = params.get('new_size', random.choice([100, 150, 200]))

        self.description = (
            f"Reduce a logical volume:\n"
            f"  - Volume group: {self.vg_name}\n"
            f"  - Logical volume: {self.lv_name}\n"
            f"  - Reduce to: {self.new_size_mb}MB\n"
            f"  - NOTE: Filesystem must be ext4 (XFS cannot shrink)\n"
            f"  - Unmount, resize filesystem, then reduce LV\n"
            f"  - Remount after completion"
        )

        self.hints = [
            f"Unmount: umount /dev/{self.vg_name}/{self.lv_name}",
            f"Check filesystem: e2fsck -f /dev/{self.vg_name}/{self.lv_name}",
            f"Resize filesystem first: resize2fs /dev/{self.vg_name}/{self.lv_name} {self.new_size_mb}M",
            f"Then reduce LV: lvreduce -L {self.new_size_mb}M /dev/{self.vg_name}/{self.lv_name}",
            "WARNING: Always resize filesystem BEFORE reducing LV!",
            "XFS cannot be shrunk - only ext4/ext3 support this"
        ]

        return self

    def inject_fault(self):
        return _scratch_setup(self, self.device, self.vg_name,
                              lv=self.lv_name, lv_mb=self._INITIAL_MB, fstype='ext4')

    def restore_fault(self):
        return _scratch_teardown(self, self.vg_name, self.device)

    def validate(self):
        checks = []
        total_points = 0

        if validate_lv_exists(self.vg_name, self.lv_name):
            checks.append(ValidationCheck("lv_exists", True, 5, f"LV exists"))
            total_points += 5

            actual_size = get_lv_size_mb(self.vg_name, self.lv_name)
            tolerance = self.new_size_mb * 0.1
            if actual_size and abs(actual_size - self.new_size_mb) <= tolerance:
                checks.append(ValidationCheck("lv_reduced", True, 10, f"LV reduced to ~{actual_size}MB"))
                total_points += 10
            else:
                checks.append(ValidationCheck("lv_reduced", False, 0, f"LV size is {actual_size}MB (expected {self.new_size_mb}MB)", max_points=10))
        else:
            checks.append(ValidationCheck("lv_exists", False, 0, f"LV not found", max_points=5))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
