"""
EX200 v10 Exam Objectives - Formal domain definitions with weights and mapped categories.
"""

EXAM_OBJECTIVES = {
    1: {
        "name": "Software Management",
        "weight": 12,
        "objectives": [
            "Install and update software packages using dnf",
            "Configure package repositories (BaseOS, AppStream, third-party)",
            "Manage RPM packages (query, verify, install)",
            "Work with package module streams",
            "Install and manage Flatpak applications and repositories",
            "Manage package groups and environments",
        ],
        "categories": ["packages", "repos", "flatpak", "modules"],
    },
    2: {
        "name": "System Setup & Boot",
        "weight": 11,
        "objectives": [
            "Set default boot target (multi-user, graphical)",
            "Configure GRUB2 boot loader parameters",
            "Reset root password using rd.break",
            "Boot into emergency and rescue targets",
            "Analyze and troubleshoot boot issues",
            "Configure persistent journal logging",
            "Use journalctl to filter and analyze logs",
        ],
        "categories": ["boot", "boot_recovery", "journalctl"],
    },
    3: {
        "name": "Users, Groups & Permissions",
        "weight": 12,
        "objectives": [
            "Create, delete, and modify local user accounts",
            "Create and manage groups",
            "Configure password aging policies",
            "Configure sudo access for users and groups",
            "Set file and directory permissions (chmod)",
            "Set file ownership (chown, chgrp)",
            "Configure and manage ACLs (setfacl, getfacl)",
            "Set special permissions (SGID, SUID, sticky bit)",
            "Configure umask for default permissions",
        ],
        "categories": ["users_groups", "permissions"],
    },
    4: {
        "name": "Storage & Filesystems",
        "weight": 15,
        "objectives": [
            "Create MBR and GPT partitions",
            "Create and manage LVM (PV, VG, LV)",
            "Extend and resize logical volumes",
            "Create ext4, XFS, and VFAT filesystems",
            "Mount filesystems persistently via /etc/fstab",
            "Mount filesystems with specific options",
            "Configure swap space (partition and file)",
            "Mount NFS shares persistently",
            "Configure autofs for on-demand mounting",
        ],
        "categories": ["partitioning", "lvm", "filesystems", "swap", "network_storage"],
    },
    5: {
        "name": "Network & DNS",
        "weight": 10,
        "objectives": [
            "Configure static and dynamic network connections using nmcli",
            "Set system hostname",
            "Configure DNS resolution (/etc/resolv.conf, nmcli)",
            "Configure /etc/hosts for name resolution",
            "Add static routes",
            "Troubleshoot network connectivity",
            "Configure IPv6 addresses",
        ],
        "categories": ["networking"],
    },
    6: {
        "name": "Systemd, Services & Processes",
        "weight": 12,
        "objectives": [
            "Start, stop, enable, and disable services",
            "Mask and unmask services",
            "View service status and logs",
            "Create and manage systemd timers",
            "Configure timer-based recurring tasks",
            "Manage running processes (kill, nice, renice)",
        ],
        "categories": ["services", "systemd_timers"],
    },
    7: {
        "name": "Security - SELinux & Firewall",
        "weight": 14,
        "objectives": [
            "Set SELinux enforcing and permissive modes",
            "Set SELinux file contexts and restore defaults",
            "Configure SELinux booleans",
            "Configure SELinux port contexts",
            "Diagnose and troubleshoot SELinux denials (audit2why, sealert)",
            "Configure firewalld zones, services, and ports",
            "Add rich rules and port forwarding",
            "Make firewall rules permanent",
        ],
        "categories": ["selinux", "firewall"],
    },
    8: {
        "name": "Automation & Scripting",
        "weight": 10,
        "objectives": [
            "Schedule recurring tasks with cron",
            "Schedule one-time tasks with at",
            "Write correct cron expressions",
            "Restrict cron access for users",
            "Write basic bash scripts with conditionals and loops",
            "Write scripts with command-line arguments",
            "Use exit codes in scripts",
        ],
        "categories": ["scheduling", "scripting"],
    },
    9: {
        "name": "Container Management",
        "weight": 4,
        "objectives": [
            "Pull and manage container images with Podman",
            "Run containers with port mappings",
            "Inspect and manage running containers",
            "Configure containers to start automatically (systemd)",
            "Run rootless containers",
        ],
        "categories": ["containers"],
    },
}


def get_domain_weight(domain_number):
    """Get the weight percentage for a domain."""
    return EXAM_OBJECTIVES.get(domain_number, {}).get("weight", 0)


def get_domain_categories(domain_number):
    """Get all task categories for a domain."""
    return EXAM_OBJECTIVES.get(domain_number, {}).get("categories", [])


def get_domain_name(domain_number):
    """Get the display name for a domain."""
    return EXAM_OBJECTIVES.get(domain_number, {}).get("name", "Unknown")
