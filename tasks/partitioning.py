"""
Disk partitioning tasks for RHCSA exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from utils.helpers import get_practice_device


logger = logging.getLogger(__name__)


def _get_safe_practice_disk():
    """Get a safe disk for partitioning practice."""
    device = get_practice_device()
    if device:
        return device
    return '/dev/sdb'  # Fallback


@TaskRegistry.register("partitioning")
class CreatePartitionTask(BaseTask):
    """Create a partition using fdisk or parted."""

    def __init__(self):
        super().__init__(
            id="part_create_001",
            category="partitioning",
            difficulty="medium",
            points=10
        )
        self.device = None
        self.size_mb = None
        self.partition_type = None

    def generate(self, **params):
        """Generate partition creation task."""
        self.device = params.get('device') or _get_safe_practice_disk()
        self.size_mb = params.get('size', random.choice([500, 1000, 2000]))
        self.partition_type = params.get('type', 'primary')

        self.description = (
            f"Create a new partition:\n"
            f"  - Device: {self.device}\n"
            f"  - Size: {self.size_mb}MB\n"
            f"  - Type: {self.partition_type}\n"
            f"  - Use fdisk or parted"
        )

        self.hints = [
            f"Using fdisk: fdisk {self.device}",
            "  n = new partition, p = primary, w = write",
            f"Using parted: parted {self.device} mkpart {self.partition_type} ext4 0% {self.size_mb}MiB",
            f"Verify: lsblk {self.device}",
            "Update kernel: partprobe"
        ]

        return self

    def validate(self):
        """Validate partition creation."""
        checks = []
        total_points = 0

        # Check if device has partitions
        result = execute_safe(['lsblk', '-ln', '-o', 'NAME,SIZE,TYPE', self.device])
        if result.success:
            lines = result.stdout.strip().split('\n')
            partitions = [l for l in lines if 'part' in l]

            if partitions:
                checks.append(ValidationCheck(
                    name="partition_exists",
                    passed=True,
                    points=6,
                    message=f"Found {len(partitions)} partition(s) on {self.device}"
                ))
                total_points += 6

                # Check size approximately
                for part_line in partitions:
                    parts = part_line.split()
                    if len(parts) >= 2:
                        size_str = parts[1]
                        # Rough size check
                        if 'M' in size_str or 'G' in size_str:
                            checks.append(ValidationCheck(
                                name="partition_size",
                                passed=True,
                                points=4,
                                message=f"Partition created with size {size_str}"
                            ))
                            total_points += 4
                            break
            else:
                checks.append(ValidationCheck(
                    name="partition_exists",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"No partitions found on {self.device}"
                ))
        else:
            checks.append(ValidationCheck(
                name="partition_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Could not check device {self.device}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("partitioning")
class CreateGPTPartitionTask(BaseTask):
    """Create GPT partition table and partitions."""

    def __init__(self):
        super().__init__(
            id="part_gpt_001",
            category="partitioning",
            difficulty="medium",
            points=12
        )
        self.device = None
        self.partition_name = None

    def generate(self, **params):
        """Generate GPT partition task."""
        self.device = params.get('device') or _get_safe_practice_disk()
        self.partition_name = params.get('name', 'data')

        self.description = (
            f"Create GPT partition table:\n"
            f"  - Device: {self.device}\n"
            f"  - Create GPT label (partition table)\n"
            f"  - Create one partition named '{self.partition_name}'\n"
            f"  - Use parted command"
        )

        self.hints = [
            f"Create GPT label: parted {self.device} mklabel gpt",
            f"Create partition: parted {self.device} mkpart {self.partition_name} ext4 0% 100%",
            "Or interactive: parted {device}",
            f"Verify: parted {self.device} print",
            "GPT supports >2TB disks and more partitions"
        ]

        return self

    def validate(self):
        """Validate GPT partition table."""
        checks = []
        total_points = 0

        # Check 1: GPT label exists
        result = execute_safe(['parted', '-s', self.device, 'print'])
        if result.success:
            if 'gpt' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name="gpt_label",
                    passed=True,
                    points=6,
                    message="GPT partition table exists"
                ))
                total_points += 6
            elif 'msdos' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name="gpt_label",
                    passed=False,
                    points=0,
                    max_points=6,
                    message="Disk has MBR, not GPT"
                ))
            else:
                checks.append(ValidationCheck(
                    name="gpt_label",
                    passed=False,
                    points=0,
                    max_points=6,
                    message="No partition table found"
                ))

            # Check 2: Has partition
            if 'Number' in result.stdout and any(c.isdigit() for c in result.stdout):
                checks.append(ValidationCheck(
                    name="has_partition",
                    passed=True,
                    points=6,
                    message="Partition exists on GPT disk"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="has_partition",
                    passed=False,
                    points=0,
                    max_points=6,
                    message="No partitions created"
                ))
        else:
            checks.append(ValidationCheck(
                name="gpt_label",
                passed=False,
                points=0,
                max_points=6,
                message=f"Could not read {self.device}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("partitioning")
class DeletePartitionTask(BaseTask):
    """Delete a partition."""

    def __init__(self):
        super().__init__(
            id="part_delete_001",
            category="partitioning",
            difficulty="medium",
            points=8
        )
        self.device = None
        self.partition_number = None

    def generate(self, **params):
        """Generate partition deletion task."""
        self.device = params.get('device') or _get_safe_practice_disk()
        self.partition_number = params.get('partition', 1)

        partition_dev = f"{self.device}{self.partition_number}"
        if 'nvme' in self.device:
            partition_dev = f"{self.device}p{self.partition_number}"

        self.description = (
            f"Delete a partition:\n"
            f"  - Device: {self.device}\n"
            f"  - Partition number: {self.partition_number}\n"
            f"  - Ensure partition is unmounted first\n"
            f"  - Use fdisk or parted"
        )

        self.hints = [
            f"Unmount first: umount {partition_dev}",
            f"Using fdisk: fdisk {self.device}, then d, then w",
            f"Using parted: parted {self.device} rm {self.partition_number}",
            "Update kernel: partprobe",
            f"Verify: lsblk {self.device}"
        ]

        return self

    def validate(self):
        """Validate partition deletion."""
        checks = []
        total_points = 0

        partition_dev = f"{self.device}{self.partition_number}"
        if 'nvme' in self.device:
            partition_dev = f"{self.device}p{self.partition_number}"

        # Check if partition still exists
        result = execute_safe(['lsblk', '-ln', '-o', 'NAME', self.device])
        if result.success:
            partition_name = partition_dev.split('/')[-1]
            if partition_name not in result.stdout:
                checks.append(ValidationCheck(
                    name="partition_deleted",
                    passed=True,
                    points=8,
                    message=f"Partition {self.partition_number} deleted"
                ))
                total_points += 8
            else:
                checks.append(ValidationCheck(
                    name="partition_deleted",
                    passed=False,
                    points=0,
                    max_points=8,
                    message=f"Partition {self.partition_number} still exists"
                ))
        else:
            checks.append(ValidationCheck(
                name="partition_deleted",
                passed=False,
                points=0,
                max_points=8,
                message="Could not verify partition status"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("partitioning")
class PartitionForLVMTask(BaseTask):
    """Create a partition with LVM type."""

    def __init__(self):
        super().__init__(
            id="part_lvm_001",
            category="partitioning",
            difficulty="medium",
            points=10
        )
        self.device = None
        self.size_mb = None

    def generate(self, **params):
        """Generate LVM partition task."""
        self.device = params.get('device') or _get_safe_practice_disk()
        self.size_mb = params.get('size', 1000)

        self.description = (
            f"Create a partition for LVM:\n"
            f"  - Device: {self.device}\n"
            f"  - Size: {self.size_mb}MB\n"
            f"  - Set partition type to LVM (8e for MBR, 8e00 for GPT)\n"
            f"  - This partition will be used for LVM physical volume"
        )

        self.hints = [
            f"Using fdisk: fdisk {self.device}",
            "  n = new partition, t = change type, 8e = Linux LVM",
            f"Using parted: parted {self.device} mkpart primary 0% {self.size_mb}MiB",
            f"Set LVM flag: parted {self.device} set 1 lvm on",
            "Verify: fdisk -l {device} or parted {device} print"
        ]

        return self

    def validate(self):
        """Validate LVM partition."""
        checks = []
        total_points = 0

        # Check if partition exists
        result = execute_safe(['lsblk', '-ln', '-o', 'NAME,TYPE', self.device])
        if result.success and 'part' in result.stdout:
            checks.append(ValidationCheck(
                name="partition_exists",
                passed=True,
                points=5,
                message="Partition exists"
            ))
            total_points += 5

            # Check LVM type
            result2 = execute_safe(['fdisk', '-l', self.device])
            if result2.success and ('Linux LVM' in result2.stdout or 'lvm' in result2.stdout.lower()):
                checks.append(ValidationCheck(
                    name="lvm_type",
                    passed=True,
                    points=5,
                    message="Partition type is LVM"
                ))
                total_points += 5
            else:
                # Check with parted
                result3 = execute_safe(['parted', '-s', self.device, 'print'])
                if result3.success and 'lvm' in result3.stdout.lower():
                    checks.append(ValidationCheck(
                        name="lvm_type",
                        passed=True,
                        points=5,
                        message="Partition has LVM flag"
                    ))
                    total_points += 5
                else:
                    checks.append(ValidationCheck(
                        name="lvm_type",
                        passed=False,
                        points=0,
                        max_points=5,
                        message="Partition type is not LVM"
                    ))
        else:
            checks.append(ValidationCheck(
                name="partition_exists",
                passed=False,
                points=0,
                max_points=5,
                message="No partition found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("partitioning")
class ViewPartitionTableTask(BaseTask):
    """View and understand partition table."""

    def __init__(self):
        super().__init__(
            id="part_view_001",
            category="partitioning",
            difficulty="easy",
            points=6
        )
        self.device = None
        self.output_file = None

    def generate(self, **params):
        """Generate view partition task."""
        self.device = params.get('device') or _get_safe_practice_disk()
        self.output_file = params.get('output', '/tmp/partition_info.txt')

        self.description = (
            f"View partition information:\n"
            f"  - Device: {self.device}\n"
            f"  - Save partition table info to: {self.output_file}\n"
            f"  - Include partition type (GPT or MBR)\n"
            f"  - Include all partition details"
        )

        self.hints = [
            f"Using fdisk: fdisk -l {self.device} > {self.output_file}",
            f"Using parted: parted {self.device} print > {self.output_file}",
            f"Using lsblk: lsblk -o NAME,SIZE,TYPE,FSTYPE {self.device}",
            "Combine: fdisk -l {device} && parted {device} print"
        ]

        return self

    def validate(self):
        """Validate partition info output."""
        checks = []
        total_points = 0

        from validators.file_validators import validate_file_exists

        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=3,
                message="Output file created"
            ))
            total_points += 3

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    if self.device in content or 'Disk' in content or 'Partition' in content:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=True,
                            points=3,
                            message="File contains partition information"
                        ))
                        total_points += 3
                    else:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=False,
                            points=0,
                            max_points=3,
                            message="File doesn't contain partition info"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="has_content",
                    passed=False,
                    points=0,
                    max_points=3,
                    message="Could not read file"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=3,
                message="Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
