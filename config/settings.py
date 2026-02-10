"""
Global configuration settings for RHCSA Simulator.
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

# Exam configuration
DEFAULT_EXAM_DURATION = 150  # minutes (2.5 hours)
DEFAULT_EXAM_TASKS = 15
EXAM_PASS_THRESHOLD = 0.70  # 70% to pass

# Task configuration
DIFFICULTY_LEVELS = ["easy", "medium", "exam", "hard"]
TASK_CATEGORIES = [
    "essential_tools",
    "users_groups",
    "permissions",
    "lvm",
    "filesystems",
    "networking",
    "selinux",
    "services",
    "boot",
    "processes",
    "scheduling",
    "containers",
    "scripting",
    "packages",
    "storage",
    "ssh",
    "time_services",
    "partitioning",
    "network_storage"
]

# Practice mode configuration
DEFAULT_PRACTICE_TASKS = 5
SHOW_HINTS_DEFAULT = True
IMMEDIATE_FEEDBACK_DEFAULT = True

# Validation configuration
COMMAND_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

# Point values by difficulty
POINTS_BY_DIFFICULTY = {
    "easy": (3, 6),      # Range: 3-6 points
    "exam": (5, 12),     # Range: 5-12 points
    "hard": (10, 20)     # Range: 10-20 points
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
    'ip', 'nmcli', 'hostnamectl', 'hostname', 'ss', 'ping', 'teamdctl',

    # Firewall info
    'firewall-cmd',

    # SELinux info
    'getenforce', 'getsebool', 'semanage', 'sestatus', 'matchpathcon',

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

    # Time services (read-only)
    'timedatectl', 'chronyc',

    # Network storage (read-only)
    'showmount', 'exportfs',

    # Partitioning (read-only - query only)
    'parted', 'fdisk', 'gdisk', 'partprobe',

    # RAID (read-only)
    'mdadm',

    # Stratis (read-only)
    'stratis',

    # Shell/scripting (read-only)
    'bash', 'test', 'which', 'type',

    # Miscellaneous
    'grep', 'awk', 'sed', 'cut', 'sort', 'uniq', 'wc', 'date'
}

# Dangerous patterns to block (security)
DANGEROUS_PATTERNS = [
    r';\s*rm\s+-rf',          # Command injection - rm -rf
    r'\|\s*sh',                # Pipe to shell
    r'\|\s*bash',              # Pipe to bash
    r'`.*`',                   # Command substitution (backticks)
    r'\$\(',                   # Command substitution $(...)
    r'>\s*/dev/',              # Device redirection
    r'>\s*/etc/',              # System config redirection
    r'dd\s+.*of=/dev/',        # Dangerous dd operations
    r'mkfs',                   # Filesystem creation (not read-only)
]

# Logging configuration
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "rhcsa_simulator.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Display configuration
USE_COLOR = True  # ANSI color codes for terminal output
DISPLAY_WIDTH = 80  # Characters
SHOW_PROGRESS_BAR = True

# Timer configuration
TIMER_WARNING_MINUTES = 30  # Warn when this many minutes remain
TIMER_CHECK_INTERVAL = 60  # Check timer every N seconds

# Result file configuration
RESULT_FILE_PREFIX = "exam_result_"
RESULT_FILE_SUFFIX = ".json"
MAX_STORED_RESULTS = 100  # Maximum number of results to keep

# RHCSA objectives mapping (for reference)
RHCSA_OBJECTIVES = {
    "essential_tools": "Understand and use essential tools",
    "users_groups": "Manage users and groups",
    "permissions": "Manage security (permissions, ACLs)",
    "lvm": "Configure local storage (LVM)",
    "filesystems": "Create and configure file systems",
    "networking": "Deploy, configure, and maintain systems (networking)",
    "selinux": "Manage security (SELinux)",
    "services": "Deploy, configure, and maintain systems (services)",
    "boot": "Manage system boot process",
    "processes": "Manage processes",
    "scheduling": "Schedule tasks",
    "containers": "Manage containers"
}

# Version
VERSION = "3.0.0"
APP_NAME = "RHCSA Mock Exam Simulator"
