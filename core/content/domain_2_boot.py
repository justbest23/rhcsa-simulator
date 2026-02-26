"""
Domain 2: System Setup & Boot
Categories: boot, boot_recovery (NEW), journalctl (NEW)
"""

CONTENT = {
    "boot": {
        "name": "Boot Process, GRUB & Targets",
        "explanation": """
The RHCSA exam heavily tests boot process knowledge including:
- Systemd targets (replacing runlevels)
- GRUB bootloader configuration
- Boot troubleshooting and log analysis
- initramfs management with dracut

BOOT SEQUENCE:
  1. BIOS/UEFI -> 2. GRUB2 -> 3. Kernel + initramfs -> 4. systemd -> 5. Target

SYSTEMD TARGETS (vs Runlevels):
  poweroff.target    = runlevel 0 (halt)
  rescue.target      = runlevel 1 (single user)
  multi-user.target  = runlevel 3 (CLI, no GUI)
  graphical.target   = runlevel 5 (GUI)
  reboot.target      = runlevel 6 (reboot)
  emergency.target   = minimal shell (root fs read-only)

KEY FILES:
  /etc/default/grub          - GRUB configuration source
  /boot/grub2/grub.cfg       - Generated GRUB config (BIOS)
  /boot/efi/EFI/redhat/grub.cfg - Generated GRUB config (UEFI)
  /etc/fstab                 - Filesystem mount table
  /boot/initramfs-*.img      - Initial RAM filesystem
        """,
        "commands": [
            {
                "name": "Show/Set Default Target",
                "syntax": "systemctl get-default / set-default <target>",
                "example": "systemctl set-default multi-user.target",
                "flags": {
                    "get-default": "Show current default boot target",
                    "set-default": "Set persistent default target",
                    "multi-user.target": "CLI mode (no GUI)",
                    "graphical.target": "GUI mode",
                    "rescue.target": "Single-user mode",
                    "emergency.target": "Minimal shell",
                },
            },
            {
                "name": "Switch Target Immediately",
                "syntax": "systemctl isolate <target>",
                "example": "systemctl isolate rescue.target",
                "flags": {
                    "isolate": "Switch to target NOW (temporary)",
                    "Does NOT change default": "Reverts on reboot",
                    "rescue.target": "Enter rescue mode",
                    "emergency.target": "Enter emergency mode",
                },
            },
            {
                "name": "Modify GRUB Timeout",
                "syntax": "Edit /etc/default/grub then grub2-mkconfig",
                "example": "vi /etc/default/grub  # Set GRUB_TIMEOUT=5\ngrub2-mkconfig -o /boot/grub2/grub.cfg",
                "flags": {
                    "GRUB_TIMEOUT": "Seconds to show menu (0 = instant boot)",
                    "GRUB_CMDLINE_LINUX": "Kernel parameters",
                    "grub2-mkconfig -o": "Regenerate GRUB config",
                    "/boot/grub2/grub.cfg": "BIOS systems",
                    "/boot/efi/EFI/redhat/grub.cfg": "UEFI systems",
                },
            },
            {
                "name": "Add/Remove Kernel Parameters",
                "syntax": "Edit GRUB_CMDLINE_LINUX in /etc/default/grub",
                "example": 'GRUB_CMDLINE_LINUX="... quiet rhgb"\ngrub2-mkconfig -o /boot/grub2/grub.cfg',
                "flags": {
                    "quiet": "Suppress boot messages",
                    "rhgb": "Red Hat graphical boot",
                    "rd.break": "Break into emergency shell (password reset)",
                    "systemd.unit=rescue.target": "Boot to rescue",
                    "init=/bin/bash": "Boot to bash (alternative recovery)",
                },
            },
            {
                "name": "Analyze Boot Time",
                "syntax": "systemd-analyze [blame|critical-chain]",
                "example": "systemd-analyze blame | head -10",
                "flags": {
                    "systemd-analyze": "Show total boot time",
                    "blame": "Show time per service (slowest first)",
                    "critical-chain": "Show critical path dependencies",
                    "plot > boot.svg": "Generate boot chart",
                },
            },
            {
                "name": "Rebuild initramfs",
                "syntax": "dracut -f [path] [kernel-version]",
                "example": "dracut -f",
                "flags": {
                    "dracut -f": "Force rebuild for current kernel",
                    "dracut -f /boot/initramfs-$(uname -r).img": "Explicit path",
                    "lsinitrd": "List initramfs contents",
                    "When to rebuild": "After adding kernel modules",
                },
            },
            {
                "name": "List Boot Entries (grubby)",
                "syntax": "grubby --info=ALL / --default-kernel",
                "example": "grubby --info=ALL",
                "flags": {
                    "--info=ALL": "Show all boot entries",
                    "--default-kernel": "Show default kernel path",
                    "--default-index": "Show default entry number",
                    "--set-default": "Set default kernel",
                },
            },
        ],
        "common_mistakes": [
            "Using 'isolate' when permanent change is needed (use set-default)",
            "Forgetting to run grub2-mkconfig after editing /etc/default/grub",
            "Wrong grub.cfg path (BIOS vs UEFI systems)",
            "Not testing fstab with 'mount -a' before reboot",
            "Typos in fstab can completely prevent boot",
        ],
        "exam_tricks": [
            "'Boot into X target' = systemctl set-default (permanent)",
            "'Switch to X target' = systemctl isolate (temporary)",
            "ALWAYS verify GRUB changes: grep GRUB_TIMEOUT /etc/default/grub",
            "ALWAYS run grub2-mkconfig after editing /etc/default/grub",
            "Check boot errors: journalctl -b -p err",
            "Find slow services: systemd-analyze blame | head",
            "Bad fstab = rescue mode needed. Use 'mount -o remount,rw /' to fix",
            "Emergency vs Rescue: Emergency = minimal, Rescue = more services",
            "UEFI path: /boot/efi/EFI/redhat/grub.cfg (not /boot/grub2/)",
        ],
    },
    "boot_recovery": {
        "name": "Boot Recovery & Root Password Reset",
        "explanation": """
Boot recovery is a CRITICAL exam skill. You must be able to reset a forgotten
root password and recover a system that fails to boot due to fstab errors,
SELinux issues, or corrupted configuration.

ROOT PASSWORD RESET PROCEDURE (MEMORIZE THIS!):
  1. Reboot system
  2. At GRUB menu, press 'e' to edit
  3. Find the 'linux' line, add 'rd.break' at the end
  4. Press Ctrl+X to boot
  5. mount -o remount,rw /sysroot
  6. chroot /sysroot
  7. passwd root
  8. touch /.autorelabel
  9. exit (twice)
  10. System reboots and relabels

RECOVERY MODES:
  rd.break:          Breaks before root mount (initramfs shell)
  rescue.target:     Single-user mode with basic services
  emergency.target:  Minimal shell, root fs read-only
  init=/bin/bash:    Direct bash shell (no systemd)

COMMON BOOT FAILURES:
  Bad /etc/fstab:    System drops to emergency mode
  SELinux mislabel:  Login fails after password change
  Missing initramfs: Kernel panic at boot
  Bad GRUB config:   System fails to load kernel
        """,
        "commands": [
            {
                "name": "Root Password Reset (rd.break)",
                "syntax": "rd.break -> remount -> chroot -> passwd -> autorelabel",
                "example": "mount -o remount,rw /sysroot\nchroot /sysroot\npasswd root\ntouch /.autorelabel\nexit\nexit",
                "flags": {
                    "rd.break": "Add to kernel line in GRUB (press 'e')",
                    "remount,rw": "Make /sysroot writable",
                    "chroot /sysroot": "Change root to real filesystem",
                    "passwd root": "Set new root password",
                    "touch /.autorelabel": "Fix SELinux labels on next boot",
                    "exit twice": "First exits chroot, second continues boot",
                },
            },
            {
                "name": "Fix Bad fstab (Emergency Mode)",
                "syntax": "mount -o remount,rw / -> fix /etc/fstab -> reboot",
                "example": "mount -o remount,rw /\nvi /etc/fstab\nsystemctl reboot",
                "flags": {
                    "mount -o remount,rw /": "Make root filesystem writable",
                    "vi /etc/fstab": "Fix the problematic entry",
                    "Comment out bad line": "Add # at start of broken entry",
                    "mount -a": "Test fstab changes before reboot",
                    "systemctl reboot": "Reboot to verify fix",
                },
            },
            {
                "name": "Boot to Rescue Target",
                "syntax": "systemd.unit=rescue.target on kernel line",
                "example": "# In GRUB edit mode, add to linux line:\nsystemd.unit=rescue.target",
                "flags": {
                    "rescue.target": "Single-user with basic services",
                    "Root password": "Required to enter rescue mode",
                    "Networking": "Available in rescue mode",
                    "More tools": "More utilities than emergency mode",
                },
            },
            {
                "name": "Boot to Emergency Target",
                "syntax": "systemd.unit=emergency.target on kernel line",
                "example": "# In GRUB edit mode, add to linux line:\nsystemd.unit=emergency.target",
                "flags": {
                    "emergency.target": "Minimal shell, root fs read-only",
                    "Root password": "Required to enter emergency mode",
                    "mount -o remount,rw /": "Make root writable for changes",
                    "Minimal services": "Only essential services running",
                },
            },
            {
                "name": "Schedule SELinux Relabel",
                "syntax": "touch /.autorelabel",
                "example": "touch /.autorelabel",
                "flags": {
                    "/.autorelabel": "Triggers relabel on next boot",
                    "Required after": "Password reset, major changes",
                    "fixfiles -F onboot": "Alternative method",
                    "Takes time": "Can take 10+ minutes on large systems",
                },
            },
            {
                "name": "Validate fstab Before Reboot",
                "syntax": "findmnt --verify && mount -a",
                "example": "findmnt --verify --verbose",
                "flags": {
                    "findmnt --verify": "Check fstab syntax",
                    "--verbose": "Show detailed info",
                    "mount -a": "Try to mount all entries",
                    "CRITICAL": "Bad fstab = system won't boot!",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting 'touch /.autorelabel' after password reset (SELinux blocks login!)",
            "Forgetting to remount /sysroot as read-write before chroot",
            "Exiting only once after chroot (need to exit twice)",
            "Not testing fstab with 'mount -a' before reboot",
            "Editing /etc/fstab without remounting root as rw first",
            "Panicking - the procedure is straightforward if memorized",
        ],
        "exam_tricks": [
            "ROOT PASSWORD RESET: rd.break -> remount,rw -> chroot -> passwd -> autorelabel -> exit x2",
            "This is almost GUARANTEED on the exam - memorize the exact steps",
            "If fstab is broken, system boots to emergency mode automatically",
            "In emergency mode: mount -o remount,rw / first, then fix fstab",
            "After fixing fstab, always 'mount -a' to verify before reboot",
            "SELinux relabel can take several minutes - don't interrupt it",
            "Ctrl+X to boot after editing GRUB (not Enter or F10 in most cases)",
        ],
    },
    "journalctl": {
        "name": "Journal & Log Analysis",
        "explanation": """
The systemd journal (journald) collects log data from the kernel, services,
and applications. journalctl is the primary tool for querying these logs.
Persistent journal storage requires configuration.

KEY CONCEPTS:
  journald:   Systemd log collection daemon
  journal:    Binary log files managed by journald
  Volatile:   Logs in /run/log/journal/ (lost on reboot) - DEFAULT
  Persistent: Logs in /var/log/journal/ (survives reboot) - must configure

ENABLING PERSISTENT JOURNAL:
  mkdir -p /var/log/journal
  systemd-tmpfiles --create --prefix /var/log/journal
  systemctl restart systemd-journald
  OR: Set Storage=persistent in /etc/systemd/journald.conf

PRIORITY LEVELS (syslog):
  0 emerg    - System is unusable
  1 alert    - Immediate action needed
  2 crit     - Critical conditions
  3 err      - Error conditions
  4 warning  - Warning conditions
  5 notice   - Normal but significant
  6 info     - Informational
  7 debug    - Debug messages
        """,
        "commands": [
            {
                "name": "View Logs (Basic)",
                "syntax": "journalctl [options]",
                "example": "journalctl -xe\njournalctl --no-pager",
                "flags": {
                    "journalctl": "Show all journal entries",
                    "-e": "Jump to end of log",
                    "-x": "Add explanatory text",
                    "-f": "Follow (like tail -f)",
                    "--no-pager": "Don't use pager (output directly)",
                    "-n 50": "Show last 50 lines",
                },
            },
            {
                "name": "Filter by Boot",
                "syntax": "journalctl -b [N]",
                "example": "journalctl -b\njournalctl -b -1\njournalctl --list-boots",
                "flags": {
                    "-b": "Current boot only",
                    "-b -1": "Previous boot",
                    "-b -2": "Two boots ago",
                    "--list-boots": "List all recorded boots",
                },
            },
            {
                "name": "Filter by Priority",
                "syntax": "journalctl -p <priority>",
                "example": "journalctl -b -p err\njournalctl -p warning..err",
                "flags": {
                    "-p emerg": "Emergency only (0)",
                    "-p err": "Errors and above (0-3)",
                    "-p warning": "Warnings and above (0-4)",
                    "-p info": "Info and above (0-6)",
                    "-p err..warning": "Range: errors and warnings only",
                },
            },
            {
                "name": "Filter by Unit/Service",
                "syntax": "journalctl -u <unit>",
                "example": "journalctl -u sshd.service\njournalctl -u httpd -u nginx",
                "flags": {
                    "-u <unit>": "Show logs for specific service",
                    "-u sshd": "SSH daemon logs",
                    "-u httpd": "Apache logs",
                    "Multiple -u": "Combine logs from multiple services",
                },
            },
            {
                "name": "Filter by Time",
                "syntax": "journalctl --since/--until '<datetime>'",
                "example": "journalctl --since '2025-01-01 08:00' --until '2025-01-01 17:00'\njournalctl --since '1 hour ago'",
                "flags": {
                    "--since": "Show entries from this time",
                    "--until": "Show entries until this time",
                    "'YYYY-MM-DD HH:MM'": "Absolute time format",
                    "'1 hour ago'": "Relative time",
                    "'today'": "Since midnight today",
                    "'yesterday'": "Since yesterday midnight",
                },
            },
            {
                "name": "Configure Persistent Journal",
                "syntax": "mkdir -p /var/log/journal && systemctl restart systemd-journald",
                "example": "mkdir -p /var/log/journal\nsystemd-tmpfiles --create --prefix /var/log/journal\nsystemctl restart systemd-journald",
                "flags": {
                    "/var/log/journal": "Directory triggers persistent storage",
                    "Storage=persistent": "Alternative: set in /etc/systemd/journald.conf",
                    "SystemMaxUse=": "Max disk usage for journal",
                    "SystemMaxFileSize=": "Max size per journal file",
                },
            },
        ],
        "common_mistakes": [
            "Journal is volatile by default - logs lost on reboot without persistent config",
            "Forgetting -b flag (shows ALL boots, very long output)",
            "Wrong priority level number (0=most severe, 7=least severe)",
            "Not quoting time strings with spaces in --since/--until",
            "Forgetting to restart systemd-journald after config changes",
            "Not creating /var/log/journal directory for persistent storage",
        ],
        "exam_tricks": [
            "Persistent journal: mkdir -p /var/log/journal + restart journald",
            "journalctl -b -p err = current boot errors (very common exam query)",
            "journalctl -u <service> = debug service issues quickly",
            "journalctl --since '1 hour ago' for recent issues",
            "--list-boots shows boot IDs (requires persistent journal)",
            "Combine filters: journalctl -b -p err -u httpd (boot + priority + unit)",
        ],
    },
}
