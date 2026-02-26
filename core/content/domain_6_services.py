"""
Domain 6: Systemd, Services & Processes
Categories: services, systemd_timers (NEW)
"""

CONTENT = {
    "services": {
        "name": "Service Management (systemd)",
        "explanation": """
Systemd is the init system and service manager in RHEL 8/9.
You must know how to start, stop, enable, disable, and check service status.
Understanding the difference between 'start' (now) and 'enable' (at boot)
is crucial. The exam tests service manipulation, unit file creation,
and boot target management.
        """,
        "commands": [
            {
                "name": "Start Service (Immediately)",
                "syntax": "systemctl start <service>",
                "example": "systemctl start httpd",
                "flags": {
                    "start": "Start service now (doesn't survive reboot)",
                    "stop": "Stop service now",
                    "restart": "Stop then start",
                    "reload": "Reload config without stopping",
                },
            },
            {
                "name": "Enable Service (At Boot)",
                "syntax": "systemctl enable <service>",
                "example": "systemctl enable httpd",
                "flags": {
                    "enable": "Start at boot (doesn't start now)",
                    "disable": "Don't start at boot",
                    "enable --now": "Enable AND start immediately",
                },
            },
            {
                "name": "Check Service Status",
                "syntax": "systemctl status <service>",
                "example": "systemctl status sshd",
                "flags": {
                    "status": "Show current status and recent logs",
                    "is-active": "Check if running (active/inactive)",
                    "is-enabled": "Check if enabled at boot",
                },
            },
            {
                "name": "Mask Service (Prevent Start)",
                "syntax": "systemctl mask <service>",
                "example": "systemctl mask postfix",
                "flags": {
                    "mask": "Completely prevent service from starting",
                    "unmask": "Remove mask",
                },
            },
        ],
        "common_mistakes": [
            "Only starting service (forgetting to enable)",
            "Only enabling service (forgetting to start)",
            "Using service name without .service suffix sometimes needed",
            "Not reloading systemd after editing unit files",
            "Checking wrong service name",
        ],
        "exam_tricks": [
            "Task says 'configure to start at boot' = enable + start",
            "Service might already be masked - must unmask first",
            "May need to reload daemon: systemctl daemon-reload",
            "Check both is-active AND is-enabled",
        ],
    },
    "systemd_timers": {
        "name": "Systemd Timers",
        "explanation": """
Systemd timers are the modern replacement for cron jobs. They provide more
flexible scheduling, better logging through journald, and dependency management.
Each timer unit (.timer) activates a corresponding service unit (.service).

KEY CONCEPTS:
  Timer Unit (.timer):   Defines when to trigger
  Service Unit (.service): Defines what to run
  Monotonic Timer:       Relative to boot or activation (OnBootSec, OnUnitActiveSec)
  Realtime Timer:        Calendar-based scheduling (OnCalendar)

TIMER TYPES:
  Monotonic:  OnBootSec=, OnStartupSec=, OnUnitActiveSec=, OnUnitInactiveSec=
  Realtime:   OnCalendar= with calendar expressions

CALENDAR EXPRESSIONS:
  daily           = *-*-* 00:00:00
  weekly          = Mon *-*-* 00:00:00
  monthly         = *-*-01 00:00:00
  hourly          = *-*-* *:00:00
  *-*-* 02:00:00  = Every day at 2 AM
  Mon..Fri *-*-* 09:00:00 = Weekdays at 9 AM
  *:0/15          = Every 15 minutes

UNIT FILE LOCATIONS:
  /etc/systemd/system/     - Admin-created units (highest priority)
  /usr/lib/systemd/system/ - Package-provided units
  ~/.config/systemd/user/  - User units (rootless)

EXAMPLE TIMER:
  [Unit]
  Description=My backup timer

  [Timer]
  OnCalendar=daily
  Persistent=true

  [Install]
  WantedBy=timers.target
        """,
        "commands": [
            {
                "name": "List Active Timers",
                "syntax": "systemctl list-timers [--all]",
                "example": "systemctl list-timers\nsystemctl list-timers --all",
                "flags": {
                    "list-timers": "Show active timers with next/last trigger",
                    "--all": "Include inactive timers",
                    "NEXT": "Next scheduled activation",
                    "LEFT": "Time until next activation",
                    "LAST": "Last time timer was triggered",
                    "PASSED": "Time since last activation",
                },
            },
            {
                "name": "Create Timer Unit",
                "syntax": "/etc/systemd/system/<name>.timer",
                "example": "[Unit]\nDescription=Run backup daily\n\n[Timer]\nOnCalendar=*-*-* 02:00:00\nPersistent=true\n\n[Install]\nWantedBy=timers.target",
                "flags": {
                    "[Timer]": "Timer configuration section",
                    "OnCalendar=": "Calendar-based schedule",
                    "OnBootSec=": "Time after boot (e.g., 5min)",
                    "OnUnitActiveSec=": "Time after unit last activated",
                    "Persistent=true": "Run missed executions on next boot",
                    "AccuracySec=": "Timer accuracy (default 1min)",
                    "RandomizedDelaySec=": "Random delay to spread load",
                },
            },
            {
                "name": "Create Corresponding Service",
                "syntax": "/etc/systemd/system/<name>.service",
                "example": "[Unit]\nDescription=Backup script\n\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/backup.sh",
                "flags": {
                    "Type=oneshot": "Run once and exit (typical for timers)",
                    "ExecStart=": "Command to execute",
                    "User=": "Run as specific user",
                    "WorkingDirectory=": "Working directory for command",
                },
            },
            {
                "name": "Enable and Start Timer",
                "syntax": "systemctl enable --now <name>.timer",
                "example": "systemctl daemon-reload\nsystemctl enable --now backup.timer",
                "flags": {
                    "daemon-reload": "Reload unit files after changes",
                    "enable --now": "Enable at boot and start immediately",
                    "start": "Start timer without enabling",
                    "stop": "Stop timer",
                    "disable": "Disable timer at boot",
                },
            },
            {
                "name": "Validate Calendar Expressions",
                "syntax": "systemd-analyze calendar '<expression>'",
                "example": "systemd-analyze calendar 'daily'\nsystemd-analyze calendar '*-*-* 02:00:00'\nsystemd-analyze calendar 'Mon..Fri *-*-* 09:00'",
                "flags": {
                    "calendar": "Parse and show normalized calendar spec",
                    "Shows": "Next matching time(s)",
                    "Useful for": "Verifying OnCalendar expressions",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting to create the matching .service file for the .timer",
            "Timer and service names don't match (must have same prefix)",
            "Forgetting systemctl daemon-reload after creating unit files",
            "Enabling the .service instead of the .timer",
            "Wrong calendar expression syntax (use systemd-analyze calendar to verify)",
            "Forgetting Persistent=true (missed triggers won't catch up)",
            "Wrong unit file permissions (should be 644)",
        ],
        "exam_tricks": [
            "Timer needs matching service: backup.timer -> backup.service",
            "Always systemctl daemon-reload after creating/editing unit files",
            "Enable the .timer, NOT the .service",
            "Persistent=true catches up on missed runs (exam expects this)",
            "systemd-analyze calendar '<expr>' to verify timing",
            "Type=oneshot for timer-triggered services (run once per trigger)",
            "Check with systemctl list-timers to verify active",
            "User timers: systemctl --user enable --now <timer>",
        ],
    },
}
