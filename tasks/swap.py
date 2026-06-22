"""
Swap management tasks for RHCSA EX200 v10 exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from utils.helpers import get_swap_practice_device

logger = logging.getLogger(__name__)


@TaskRegistry.register("swap")
class CreateSwapPartitionTask(BaseTask):
    """Create and activate a swap partition."""

    def __init__(self):
        super().__init__(
            id="swap_partition_001",
            category="swap",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'swap', 'partitioning']
        self.exam_tips = [
            "Use mkswap to format, swapon to activate",
            "Add to /etc/fstab with swap as mount point and fstype",
            "Use UUID in fstab for reliability: UUID=xxx swap swap defaults 0 0",
            "Get UUID with: blkid /dev/device or lsblk -f",
            "Verify swap is active: swapon --show or free -h",
            "Test fstab entry: swapoff -a && swapon -a",
        ]
        self.device = None
        self.size_mb = None

    def generate(self, **params):
        self.size_mb = params.get('size_mb', random.choice([256, 512]))
        self.loop_device = params.get('loop_device') or get_swap_practice_device() or '/dev/sdb'
        # Partition 1 on the loop device (e.g. /dev/loop2p1)
        self.device = params.get('device') or f"{self.loop_device}p1"

        self.description = (
            f"Use {self.loop_device} to create a {self.size_mb}MB swap partition "
            f"and configure it as persistent swap."
        )

        self.hints = [
            f"Use fdisk {self.loop_device} to create a new partition of ~{self.size_mb}MB",
            "Run partprobe after fdisk so the kernel sees the new partition",
            "mkswap formats the partition as swap space",
            "swapon activates the swap partition",
            "Use blkid to get the UUID for a stable /etc/fstab entry",
            "fstab swap entry: UUID=... none swap defaults 0 0",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: Swap is active on the partition (4 pts)
        result = execute_safe(['swapon', '--show'])
        swap_active = result.success and self.device in result.stdout
        if swap_active:
            checks.append(ValidationCheck("swap_active", True, 4, f"Swap active on {self.device}"))
            total_points += 4
        else:
            checks.append(ValidationCheck("swap_active", False, 0,
                f"Swap not active on {self.device} — run: mkswap {self.device} && swapon {self.device}", max_points=4))

        # Check 2: Partition is formatted as swap (4 pts)
        result = execute_safe(['blkid', self.device])
        is_swap = result.success and 'TYPE="swap"' in result.stdout
        if is_swap:
            checks.append(ValidationCheck("swap_formatted", True, 4, f"{self.device} formatted as swap"))
            total_points += 4
        else:
            checks.append(ValidationCheck("swap_formatted", False, 0,
                f"{self.device} not formatted as swap — run: mkswap {self.device}", max_points=4))

        # Check 3: In /etc/fstab (4 pts)
        result = execute_safe(['cat', '/etc/fstab'])
        fstab_ok = False
        if result.success:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 3 and parts[2] == 'swap':
                    if self.device in line:
                        fstab_ok = True
                    elif 'UUID=' in parts[0]:
                        uuid_val = parts[0].split('=')[1]
                        blkid = execute_safe(['blkid', '-U', uuid_val])
                        if blkid.success and self.device in blkid.stdout:
                            fstab_ok = True

        if fstab_ok:
            checks.append(ValidationCheck("fstab_entry", True, 4, "Swap partition in /etc/fstab"))
            total_points += 4
        else:
            checks.append(ValidationCheck("fstab_entry", False, 0,
                f"No fstab entry for swap on {self.device} — add UUID or device path with type 'swap'", max_points=4))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("swap")
class CreateSwapFileTask(BaseTask):
    """Create and activate a swap file."""

    def __init__(self):
        super().__init__(
            id="swap_file_001",
            category="swap",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'swap', 'filesystems']
        self.exam_tips = [
            "Create swap file: dd if=/dev/zero of=/swapfile bs=1M count=SIZE or fallocate -l SIZE /swapfile",
            "CRITICAL: Set permissions to 600 (chmod 600 /swapfile) before mkswap",
            "Format: mkswap /swapfile, then activate: swapon /swapfile",
            "Add to fstab: /swapfile swap swap defaults 0 0 (no UUID for files)",
            "Verify: swapon --show, free -h, or cat /proc/swaps",
            "Swap file is easier than partition (no repartitioning needed)",
        ]
        self.swap_file = None
        self.size_mb = None

    def generate(self, **params):
        self.size_mb = params.get('size_mb', random.choice([256, 512, 1024]))
        self.swap_file = params.get('swap_file', random.choice([
            '/swapfile', '/var/swap', '/swap.img'
        ]))

        self.description = (
            f"Create a {self.size_mb}MB persistent swap file at {self.swap_file}."
        )

        self.hints = [
            "fallocate or dd can create a fixed-size file",
            "Swap files must have permissions 600 before mkswap will accept them",
            "fstab entry for a swap file uses the file path directly, not a UUID",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: File exists (2 pts)
        result = execute_safe(['test', '-f', self.swap_file])
        if result.success:
            checks.append(ValidationCheck("file_exists", True, 2, f"{self.swap_file} exists"))
            total_points += 2
        else:
            checks.append(ValidationCheck("file_exists", False, 0, f"{self.swap_file} not found", max_points=2))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: Correct permissions (2 pts)
        result = execute_safe(['stat', '-c', '%a', self.swap_file])
        if result.success and result.stdout.strip() == '600':
            checks.append(ValidationCheck("permissions", True, 2, "Permissions are 600"))
            total_points += 2
        else:
            checks.append(ValidationCheck("permissions", False, 0, f"Permissions should be 600, got {result.stdout.strip()}", max_points=2))

        # Check 3: Swap active (3 pts)
        result = execute_safe(['swapon', '--show'])
        if result.success and self.swap_file in result.stdout:
            checks.append(ValidationCheck("swap_active", True, 3, "Swap file is active"))
            total_points += 3
        else:
            checks.append(ValidationCheck("swap_active", False, 0, "Swap file not active", max_points=3))

        # Check 4: In fstab (3 pts)
        result = execute_safe(['cat', '/etc/fstab'])
        fstab_ok = result.success and self.swap_file in result.stdout and 'swap' in result.stdout
        if fstab_ok:
            checks.append(ValidationCheck("fstab_entry", True, 3, "Swap file in /etc/fstab"))
            total_points += 3
        else:
            checks.append(ValidationCheck("fstab_entry", False, 0, "Swap file not in /etc/fstab", max_points=3))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("swap")
class SetSwappinessTask(BaseTask):
    """Configure vm.swappiness sysctl parameter."""

    def __init__(self):
        super().__init__(
            id="swap_swappiness_001",
            category="swap",
            difficulty="medium",
            points=8
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'swap', 'tuning', 'sysctl']
        self.exam_tips = [
            "vm.swappiness controls how aggressively kernel swaps (0-100, default 60)",
            "Lower value (10-20) = less swapping, higher value (80+) = more swapping",
            "Runtime: sysctl vm.swappiness=VALUE or echo VALUE > /proc/sys/vm/swappiness",
            "Persistent: Add 'vm.swappiness=VALUE' to /etc/sysctl.d/99-swappiness.conf",
            "Apply persistent config: sysctl -p /etc/sysctl.d/99-swappiness.conf",
            "Verify: sysctl vm.swappiness or cat /proc/sys/vm/swappiness",
        ]
        self.swappiness = None

    def generate(self, **params):
        self.swappiness = params.get('swappiness', random.choice([10, 20, 30, 40, 60, 80]))

        self.description = (
            f"Set vm.swappiness to {self.swappiness}, applied immediately and persistently."
        )

        self.hints = [
            "sysctl sets kernel parameters at runtime",
            "Persistent sysctl settings live in /etc/sysctl.d/ or /etc/sysctl.conf",
            "sysctl -p reloads a config file without rebooting",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: Current runtime value (4 pts)
        result = execute_safe(['cat', '/proc/sys/vm/swappiness'])
        if result.success and result.stdout.strip() == str(self.swappiness):
            checks.append(ValidationCheck("runtime_value", True, 4, f"vm.swappiness = {self.swappiness}"))
            total_points += 4
        else:
            actual = result.stdout.strip() if result.success else 'unknown'
            checks.append(ValidationCheck("runtime_value", False, 0, f"Expected {self.swappiness}, got {actual}", max_points=4))

        # Check 2: Persistent config (4 pts)
        persistent = False
        for conf_path in ['/etc/sysctl.d/', '/etc/sysctl.conf']:
            if conf_path.endswith('/'):
                result = execute_safe(['grep', '-r', f'vm.swappiness={self.swappiness}', conf_path])
            else:
                result = execute_safe(['grep', f'vm.swappiness={self.swappiness}', conf_path])
            if result.success and result.stdout.strip():
                persistent = True
                break

        if persistent:
            checks.append(ValidationCheck("persistent_config", True, 4, "Swappiness configured persistently"))
            total_points += 4
        else:
            checks.append(ValidationCheck("persistent_config", False, 0, "Swappiness not in sysctl.d config", max_points=4))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
