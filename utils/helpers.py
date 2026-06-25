"""
Helper utility functions for RHCSA Simulator.
"""

import logging
import os
import sys
import uuid
from datetime import timedelta

logger = logging.getLogger(__name__)


def check_root():
    """
    Check if the script is running with root privileges.

    Returns:
        bool: True if running as root, False otherwise
    """
    return os.geteuid() == 0


def require_root():
    """
    Require root privileges to continue. Exit if not root.
    """
    if not check_root():
        print("Error: This application requires root privileges.")
        print("Please run with: sudo rhcsa-simulator")
        sys.exit(1)


def generate_id(prefix=""):
    """
    Generate a unique ID with optional prefix.

    Args:
        prefix (str): Optional prefix for the ID

    Returns:
        str: Unique ID string
    """
    unique_id = str(uuid.uuid4())[:8]
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def format_time(seconds):
    """
    Format seconds into human-readable time string.

    Args:
        seconds (int): Number of seconds

    Returns:
        str: Formatted time string (e.g., "2h 30m 15s")
    """
    if seconds < 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_timedelta(td):
    """
    Format a timedelta into human-readable string.

    Args:
        td (timedelta): Time delta object

    Returns:
        str: Formatted time string
    """
    total_seconds = int(td.total_seconds())
    return format_time(total_seconds)


def parse_percentage(value):
    """
    Parse a percentage value from various formats.

    Args:
        value: String or number representing a percentage

    Returns:
        float: Percentage as decimal (0.0-1.0)
    """
    if isinstance(value, (int, float)):
        if value > 1:
            return value / 100.0
        return float(value)

    if isinstance(value, str):
        value = value.strip().rstrip('%')
        try:
            num = float(value)
            if num > 1:
                return num / 100.0
            return num
        except ValueError:
            return 0.0

    return 0.0


def confirm_action(prompt, default=False):
    """
    Ask user for confirmation.

    Args:
        prompt (str): Confirmation prompt
        default (bool): Default value if user just presses Enter

    Returns:
        bool: True if user confirms, False otherwise
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        response = input(prompt + suffix).strip().lower()
        if response == '':
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please answer 'y' or 'n'")


def get_terminal_width():
    """
    Get the current terminal width.

    Returns:
        int: Terminal width in characters (default 80)
    """
    try:
        import shutil
        return shutil.get_terminal_size((80, 20)).columns
    except:
        return 80


def truncate_string(text, max_length, suffix="..."):
    """
    Truncate a string to maximum length.

    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        suffix (str): Suffix to add if truncated

    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def pluralize(count, singular, plural=None):
    """
    Return singular or plural form based on count.

    Args:
        count (int): Count value
        singular (str): Singular form
        plural (str): Plural form (default: singular + 's')

    Returns:
        str: Appropriate form
    """
    if plural is None:
        plural = singular + 's'
    return singular if count == 1 else plural


def format_list(items, conjunction="and"):
    """
    Format a list of items as a comma-separated string with conjunction.

    Args:
        items (list): List of items
        conjunction (str): Conjunction word (default: "and")

    Returns:
        str: Formatted string
    """
    if not items:
        return ""
    if len(items) == 1:
        return str(items[0])
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return ", ".join(str(item) for item in items[:-1]) + f", {conjunction} {items[-1]}"


def safe_divide(numerator, denominator, default=0.0):
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division by zero

    Returns:
        float: Division result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except:
        return default


def clamp(value, min_val, max_val):
    """
    Clamp a value between minimum and maximum.

    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


# =============================================================================
# Practice Device Configuration
# =============================================================================

PRACTICE_DEVICE_CONFIG = '/var/lib/rhcsa-simulator/practice_devices.conf'


def get_practice_device_config():
    """
    Read the saved practice device configuration.
    Returns dict with keys 'mode' ('loop' or 'real') and 'devices' (list).
    Returns None if no config saved.
    """
    if not os.path.exists(PRACTICE_DEVICE_CONFIG):
        return None
    try:
        import json
        with open(PRACTICE_DEVICE_CONFIG) as f:
            return json.load(f)
    except Exception:
        return None


def save_practice_device_config(mode, devices):
    """
    Save the practice device selection to disk.
    mode: 'loop' or 'real'
    devices: list of device paths
    """
    import json
    os.makedirs(os.path.dirname(PRACTICE_DEVICE_CONFIG), exist_ok=True)
    with open(PRACTICE_DEVICE_CONFIG, 'w') as f:
        json.dump({'mode': mode, 'devices': devices}, f)


def wipe_disk(device):
    """
    Completely wipe a disk: deactivate swap/LVM on all partitions,
    remove filesystem signatures, zero out the partition table, and
    tell the kernel to re-read the disk. Leaves a completely raw device.
    Returns (success, list_of_messages).
    """
    import subprocess

    msgs = []

    # 1. Find all partitions on this disk
    part_result = subprocess.run(
        ['lsblk', '-no', 'NAME', device],
        capture_output=True, text=True, timeout=10
    )
    all_parts = []
    for line in part_result.stdout.strip().splitlines():
        name = line.strip()
        if not name:
            continue
        path = f"/dev/{name}" if not name.startswith('/') else name
        if path != device:
            all_parts.append(path)

    # 2. Deactivate swap and LVM on partitions and the disk itself
    for dev in all_parts + [device]:
        subprocess.run(['swapoff', dev], capture_output=True, timeout=10)
        subprocess.run(['pvremove', '-ff', '-y', dev], capture_output=True, timeout=10)
        # Unmount if somehow mounted
        subprocess.run(['umount', '-f', dev], capture_output=True, timeout=10)

    # 3. Deactivate any VGs that might now have missing PVs
    subprocess.run(['vgscan', '--cache'], capture_output=True, timeout=10)

    # 4. Remove all filesystem/LVM/swap signatures from disk and partitions
    for dev in all_parts + [device]:
        subprocess.run(['wipefs', '-a', dev], capture_output=True, timeout=10)

    # 5. Zero out the first and last few MB to destroy partition tables (MBR + GPT)
    try:
        size_result = subprocess.run(
            ['blockdev', '--getsize64', device],
            capture_output=True, text=True, timeout=10
        )
        disk_bytes = int(size_result.stdout.strip())
        # Zero first 2MB (MBR + GPT header)
        subprocess.run(
            ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 'count=2', 'oflag=direct'],
            capture_output=True, timeout=30
        )
        # Zero last 1MB (GPT backup header)
        skip_mb = disk_bytes // (1024 * 1024) - 1
        subprocess.run(
            ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 'count=1',
             f'seek={skip_mb}', 'oflag=direct'],
            capture_output=True, timeout=30
        )
        msgs.append(f"Partition table wiped on {device}")
    except Exception as e:
        msgs.append(f"Warning: could not zero partition table on {device}: {e}")

    # 6. Tell kernel to re-read
    subprocess.run(['partprobe', device], capture_output=True, timeout=10)
    subprocess.run(['udevadm', 'settle'], capture_output=True, timeout=15)

    msgs.append(f"{device} is now a clean raw device")
    return True, msgs


def list_all_block_devices():
    """
    Return info on all block devices, excluding CD-ROMs and floppies.
    Does NOT filter out system disks — let the user decide.
    Returns list of dicts: {device, size, has_partitions, mounted, is_system}.
    """
    import subprocess

    result = subprocess.run(
        ['lsblk', '-dpno', 'NAME,SIZE,TYPE'],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return []

    # Find which physical disk(s) back the / mountpoint.
    # Walk lsblk tree: dm-* devices (LVM) list their underlying disk via PKNAME.
    # We collect every device that is an ancestor of the / mountpoint.
    tree_result = subprocess.run(
        ['lsblk', '-no', 'NAME,PKNAME,MOUNTPOINT'],
        capture_output=True, text=True, timeout=10
    )
    # Build parent map: name -> pkname
    parent = {}
    root_devs = set()
    for line in tree_result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            pkname = parts[1] if parts[1] != name else None
            mnt = parts[2] if len(parts) >= 3 else ''
            parent[name] = pkname
            if mnt == '/':
                root_devs.add(name)

    # Walk up the parent chain from each root device to find the physical disk
    system_disks = set()
    for dev in root_devs:
        cur = dev
        while cur:
            nxt = parent.get(cur)
            if not nxt:
                system_disks.add(f"/dev/{cur}")
                break
            cur = nxt

    devices = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, size, dtype = parts[0], parts[1], parts[2]
        if dtype != 'disk':
            continue
        if any(x in device for x in ['sr', 'fd', 'cdrom']):
            continue

        part_result = subprocess.run(
            ['lsblk', '-no', 'NAME', device],
            capture_output=True, text=True, timeout=5
        )
        children = [l.strip() for l in part_result.stdout.strip().splitlines() if l.strip()]
        has_partitions = len(children) > 1

        mount_result = subprocess.run(
            ['lsblk', '-no', 'MOUNTPOINT', device],
            capture_output=True, text=True, timeout=5
        )
        all_mounts = [m.strip() for m in mount_result.stdout.strip().splitlines() if m.strip()]
        # Only real filesystem paths count as "mounted" — [SWAP] does not
        fs_mounts = [m for m in all_mounts if m.startswith('/')]
        has_swap = any(m == '[SWAP]' for m in all_mounts)

        devices.append({
            'device': device,
            'size': size,
            'has_partitions': has_partitions,
            'mounted': bool(fs_mounts),
            'has_swap': has_swap,
            'is_system': device in system_disks,
        })

    return devices


# =============================================================================
# LVM Practice Device Helpers
# =============================================================================

def get_available_block_devices():
    """
    Get list of available unused block devices.
    Prioritizes completely empty disks (no partitions) for practice.

    Returns:
        list: List of device paths (e.g., ['/dev/sdd', '/dev/vdb'])
    """
    import subprocess

    try:
        result = subprocess.run(
            ['lsblk', '-dpno', 'NAME,TYPE,SIZE'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            return []

        empty_disks = []
        unused_disks = []

        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                device = parts[0]
                dtype = parts[1]

                if dtype != 'disk':
                    continue

                # Skip known system disks
                if any(x in device for x in ['vda', 'sda', 'nvme0n1', 'xvda']):
                    continue

                # Skip CD-ROM/removable
                if 'sr' in device or 'fd' in device:
                    continue

                # Check if disk has any partitions
                part_result = subprocess.run(
                    ['lsblk', '-no', 'NAME', device],
                    capture_output=True, text=True, timeout=5
                )
                children = [l.strip() for l in part_result.stdout.strip().splitlines() if l.strip()]
                has_partitions = len(children) > 1

                if not has_partitions:
                    # Completely empty disk - check not a PV
                    pv_check = subprocess.run(
                        ['pvs', '--noheadings', '-o', 'pv_name'],
                        capture_output=True, text=True, timeout=5
                    )
                    if device not in pv_check.stdout:
                        empty_disks.append(device)
                else:
                    # Has partitions - check if used by LVM
                    pv_check = subprocess.run(
                        ['pvs', '--noheadings', '-o', 'pv_name'],
                        capture_output=True, text=True, timeout=5
                    )
                    disk_basename = device.split('/')[-1]
                    if disk_basename not in pv_check.stdout:
                        mount_check = subprocess.run(
                            ['lsblk', '-no', 'MOUNTPOINT', device],
                            capture_output=True, text=True, timeout=5
                        )
                        mounts = [m for m in mount_check.stdout.strip().splitlines() if m.strip()]
                        if not mounts:
                            unused_disks.append(device)

        return empty_disks + unused_disks
    except Exception as e:
        return []




def get_loop_devices():
    """
    Get list of loop devices created for LVM practice.

    Returns:
        list: List of loop device paths
    """
    import subprocess
    import os

    loop_dir = '/var/lib/rhcsa-simulator/loops'
    if not os.path.exists(loop_dir):
        return []

    devices = []
    try:
        result = subprocess.run(
            ['losetup', '-a'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if line and loop_dir in line:
                device = line.split(':')[0]
                devices.append(device)
    except:
        pass

    return devices


def get_swap_practice_device():
    """
    Return the device to use for swap partition practice.
    - Real disk mode: returns the configured real disk (student partitions it with fdisk)
    - Loop mode: returns the loop device backed by disk2.img (3rd practice disk)
    """
    import subprocess
    import os

    cfg = get_practice_device_config()

    if cfg and cfg['mode'] == 'real' and cfg.get('devices'):
        # Real disk — student uses fdisk on it to create a swap partition
        return cfg['devices'][-1]

    # Loop mode: find disk2.img
    disk2_img = '/var/lib/rhcsa-simulator/loops/disk2.img'
    if os.path.exists(disk2_img):
        try:
            result = subprocess.run(
                ['losetup', '-j', disk2_img],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.split(':')[0].strip()
        except Exception:
            pass

    # Fallback: last loop device we own
    devices = get_loop_devices()
    if devices:
        return devices[-1]
    return None


def create_practice_devices(count=3, size_mb=500):
    """
    Create loop devices for LVM practice.

    Args:
        count: Number of devices to create (default: 2)
        size_mb: Size of each device in MB (default: 500)

    Returns:
        list: List of created loop device paths
    """
    import subprocess
    import os

    loop_dir = '/var/lib/rhcsa-simulator/loops'
    os.makedirs(loop_dir, exist_ok=True)

    created_devices = []

    for i in range(count):
        img_file = f'{loop_dir}/disk{i}.img'

        # Create sparse file
        try:
            # Remove if exists
            if os.path.exists(img_file):
                # Check if already attached
                result = subprocess.run(
                    ['losetup', '-j', img_file],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    # Already attached, get the device
                    device = result.stdout.split(':')[0]
                    created_devices.append(device)
                    continue

            # Create new sparse file
            subprocess.run(
                ['dd', 'if=/dev/zero', f'of={img_file}', 'bs=1M', f'count={size_mb}'],
                capture_output=True, timeout=60
            )

            # Attach to loop device
            result = subprocess.run(
                ['losetup', '-f', '--show', img_file],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                device = result.stdout.strip()
                created_devices.append(device)
        except Exception as e:
            print(f"Error creating practice device: {e}")

    return created_devices


def cleanup_practice_devices():
    """
    Clean up practice devices based on the saved configuration.
    - Loop mode: deactivate swap, remove LVM, detach loops, delete images.
    - Real disk mode: remove LVM structures from configured disks (does NOT
      wipe partition tables — user's data, user's responsibility).
    Also removes the practice device config file.
    """
    import subprocess
    import os

    loop_dir = '/var/lib/rhcsa-simulator/loops'
    cfg = get_practice_device_config()

    try:
        if cfg and cfg['mode'] == 'real':
            # Wipe all practice disks completely (partition table + data)
            for device in cfg.get('devices', []):
                wipe_disk(device)
        else:
            # Loop mode cleanup
            devices = get_loop_devices()
            swap_dev = get_swap_practice_device()
            if swap_dev and swap_dev not in devices:
                devices.append(swap_dev)

            for device in devices:
                subprocess.run(['swapoff', device], capture_output=True, timeout=10)
                subprocess.run(['pvremove', '-ff', '-y', device],
                               capture_output=True, timeout=10)
                subprocess.run(['losetup', '-d', device],
                               capture_output=True, timeout=10)

            if os.path.exists(loop_dir):
                for f in os.listdir(loop_dir):
                    if f.endswith('.img'):
                        os.remove(os.path.join(loop_dir, f))

        # Remove config so next run starts fresh
        if os.path.exists(PRACTICE_DEVICE_CONFIG):
            os.remove(PRACTICE_DEVICE_CONFIG)

        return True
    except Exception as e:
        print(f"Error cleaning up: {e}")
        return False


def get_practice_device():
    """
    Get a device suitable for LVM practice.
    Uses DeviceManager for smart detection (handles system disks, caching,
    and disks with existing practice LVM), then falls back to loop devices.

    Returns:
        str: Device path or None if none available
    """
    # Use DeviceManager for smart detection (skips system disks, caches result,
    # recognizes disks with existing practice PVs/VGs)
    # Check saved config first
    cfg = get_practice_device_config()
    if cfg and cfg.get('devices'):
        if cfg['mode'] == 'loop':
            # Re-attach loop devices if needed
            loop_devices = get_loop_devices()
            if loop_devices:
                return loop_devices[0]
            # Images may still exist but not attached — recreate
            created = create_practice_devices(count=3, size_mb=500)
            if created:
                return created[0]
        else:
            # Real disk mode — return first configured device
            return cfg['devices'][0]

    # No config: fall back to loop devices if any exist
    loop_devices = get_loop_devices()
    if loop_devices:
        return loop_devices[0]

    return None


def get_all_practice_devices():
    """
    Get all devices configured for LVM/partition practice.
    Respects the saved practice device config.
    """
    cfg = get_practice_device_config()
    if cfg and cfg.get('devices'):
        if cfg['mode'] == 'loop':
            return get_loop_devices()
        else:
            return cfg['devices']

    # No config — return whatever loop devices are attached
    return get_loop_devices()


def get_practice_lv():
    """
    Get an existing non-system LV suitable for practice (extend tasks).
    Returns tuple of (vg_name, lv_name) or (None, None) if none found.
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ['lvs', '--noheadings', '-o', 'vg_name,lv_name'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return None, None
        
        # System VGs to skip
        system_vgs = ['rl', 'rl00', 'rhel', 'centos', 'fedora']
        
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                vg_name = parts[0]
                lv_name = parts[1]
                # Skip system VGs
                if vg_name not in system_vgs:
                    return vg_name, lv_name
        
        return None, None
    except Exception:
        return None, None


def get_practice_vg():
    """
    Get an existing non-system VG suitable for practice.
    Returns vg_name or None if none found.
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ['vgs', '--noheadings', '-o', 'vg_name,vg_free'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        # System VGs to skip
        system_vgs = ['rl', 'rl00', 'rhel', 'centos', 'fedora']
        
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 1:
                vg_name = parts[0]
                if vg_name not in system_vgs:
                    return vg_name

        return None
    except Exception:
        return None


def populate_dnf_history(target_transactions=12, progress_callback=None):
    """
    Build up DNF transaction history by installing and removing lightweight
    packages in cycles. Only installs packages not currently present so it
    never removes something the user already had.

    Returns the number of install/remove cycles completed.
    """
    import subprocess
    import logging

    logger = logging.getLogger(__name__)

    # Small packages available in RHEL 10 BaseOS/AppStream
    candidates = [
        'tree', 'dos2unix', 'bc', 'mtr', 'strace',
        'lsof', 'pv', 'words', 'screen', 'nmap',
        'zip', 'ltrace', 'telnet', 'whois', 'jq',
    ]

    cycles = 0

    for pkg in candidates:
        if cycles >= target_transactions:
            break

        # Skip if already installed — never touch pre-existing packages
        check = subprocess.run(['rpm', '-q', pkg], capture_output=True)
        if check.returncode == 0:
            logger.debug(f"Skipping {pkg} (already installed)")
            continue

        if progress_callback:
            progress_callback(f"Installing {pkg}...")

        install = subprocess.run(
            ['dnf', 'install', '-y', '--quiet', pkg],
            capture_output=True, text=True, timeout=120
        )
        if install.returncode != 0:
            logger.debug(f"Could not install {pkg}: {install.stderr[:200]}")
            continue

        if progress_callback:
            progress_callback(f"Removing {pkg}...")

        subprocess.run(
            ['dnf', 'remove', '-y', '--quiet', pkg],
            capture_output=True, text=True, timeout=120
        )
        cycles += 1
        logger.info(f"DNF history cycle: {pkg} installed+removed")

    return cycles
