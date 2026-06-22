"""
Global configuration settings for RHCSA EX200 v10 Simulator v4.0.0
"""

import os
from pathlib import Path

# Installation paths
INSTALL_DIR = Path("/opt/rhcsa-simulator")
CONFIG_DIR = INSTALL_DIR / "config"
DATA_DIR = INSTALL_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"

# Development mode (use local paths if not installed)
if not INSTALL_DIR.exists():
    INSTALL_DIR = Path(__file__).parent.parent
    CONFIG_DIR = INSTALL_DIR / "config"
    DATA_DIR = INSTALL_DIR / "data"
    RESULTS_DIR = DATA_DIR / "results"

# Create data directories if they don't exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database path
DB_PATH = DATA_DIR / "rhcsa_simulator.db"

# Exam configuration - v10 aligned
DEFAULT_EXAM_DURATION = 180  # minutes (3 hours - real exam)
DEFAULT_EXAM_TASKS = 12  # range 10-15 on real exam
EXAM_TASK_RANGE = (10, 15)
MAX_EXAM_SCORE = 300  # matches real exam
EXAM_PASS_THRESHOLD = 0.70  # 70% to pass

# Reboot simulation
REBOOT_SIMULATION = True

# Task configuration
DIFFICULTY_LEVELS = ["easy", "medium", "exam", "hard"]
TASK_CATEGORIES = [
    "users_groups",
    "permissions",
    "essential_tools",
    "lvm",
    "filesystems",
    "networking",
    "ssh",
    "selinux",
    "services",
    "processes",
    "time_services",
    "troubleshooting",
    "boot",
    "scheduling",
    "scripting",
    "packages",
    "partitioning",
    "network_storage",
    "repos",
    "flatpak",
    "boot_recovery",
    "journalctl",
    "systemd_timers",
    "firewall",
    "swap",
]

# EX200 v10 Exam Domains (1-8)
EXAM_DOMAINS = {
    1: "Software Management",
    2: "System Setup & Boot",
    3: "Users, Groups & Permissions",
    4: "Storage & Filesystems",
    5: "Network & DNS",
    6: "Systemd, Services & Processes",
    7: "Security - SELinux & Firewall",
    8: "Automation & Scripting",
}

# Map categories to domains
CATEGORY_TO_DOMAIN = {
    "packages": 1, "repos": 1, "flatpak": 1,
    "boot": 2, "boot_recovery": 2, "journalctl": 2,
    "users_groups": 3, "permissions": 3, "essential_tools": 3,
    "partitioning": 4, "lvm": 4, "filesystems": 4, "swap": 4, "network_storage": 4,
    "networking": 5, "ssh": 5,
    "services": 6, "systemd_timers": 6, "processes": 6, "time_services": 6, "troubleshooting": 6,
    "selinux": 7, "firewall": 7,
    "scheduling": 8, "scripting": 8,
}

# Practice mode configuration
DEFAULT_PRACTICE_TASKS = 5
SHOW_HINTS_DEFAULT = True
IMMEDIATE_FEEDBACK_DEFAULT = True

# Validation configuration
COMMAND_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

# Point values by difficulty
POINTS_BY_DIFFICULTY = {
    "easy": (3, 8),
    "medium": (8, 12),
    "exam": (10, 20),
    "hard": (15, 20),
}

# Safe commands whitelist for validation (read-only operations)
SAFE_VALIDATION_COMMANDS = {
    # User management (read-only)
    'id', 'getent', 'groups', 'whoami',

    # Filesystem info
    'df', 'mount', 'lsblk', 'blkid', 'findmnt', 'xfs_info', 'tune2fs',
    'dumpe2fs', 'file', 'swapon', 'free',

    # LVM info
    'pvs', 'vgs', 'lvs', 'pvdisplay', 'vgdisplay', 'lvdisplay',

    # File/directory operations (read-only)
    'ls', 'stat', 'getfacl', 'cat', 'head', 'tail', 'find',

    # Network info
    'ip', 'nmcli', 'hostnamectl', 'hostname', 'ss', 'ping',

    # Firewall info
    'firewall-cmd',

    # SELinux info
    'getenforce', 'getsebool', 'semanage', 'sestatus', 'matchpathcon',
    'ausearch', 'audit2why', 'sealert',

    # Service/systemd info
    'systemctl', 'journalctl',

    # Process info
    'ps', 'top', 'pgrep', 'pidof',

    # Scheduling
    'crontab', 'atq', 'at',

    # Containers
    'podman',

    # Package management (read-only)
    'rpm', 'dnf', 'yum',

    # Flatpak (read-only)
    'flatpak',

    # Time services (read-only)
    'timedatectl', 'chronyc',

    # Network storage (read-only)
    'showmount', 'exportfs',

    # Partitioning (read-only - query only)
    'parted', 'fdisk', 'gdisk', 'partprobe',

    # Shell/scripting (read-only)
    'bash', 'test', 'which', 'type',

    # Boot analysis
    'systemd-analyze', 'grubby',

    # Miscellaneous
    'grep', 'awk', 'sed', 'cut', 'sort', 'uniq', 'wc', 'date',
    'chage', 'passwd',
}

# Dangerous patterns to block (security)
DANGEROUS_PATTERNS = [
    r';\s*rm\s+-rf',
    r'\|\s*sh',
    r'\|\s*bash',
    r'`.*`',
    r'\$\(',
    r'>\s*/dev/',
    r'>\s*/etc/',
    r'dd\s+.*of=/dev/',
    r'mkfs',
]

# Logging configuration
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "rhcsa_simulator.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Display configuration
USE_COLOR = True
DISPLAY_WIDTH = 80
SHOW_PROGRESS_BAR = True

# Timer configuration
TIMER_WARNING_MINUTES = 30
TIMER_CHECK_INTERVAL = 60

# Result file configuration
RESULT_FILE_PREFIX = "exam_result_"
RESULT_FILE_SUFFIX = ".json"
MAX_STORED_RESULTS = 100

# Version
VERSION = "4.0.0"
APP_NAME = "RHCSA EX200 v10 Exam Simulator"
