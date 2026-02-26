"""
Domain 7: Security - SELinux & Firewall
Categories: selinux, firewall
"""

CONTENT = {
    "selinux": {
        "name": "SELinux Security",
        "explanation": """
SELinux (Security-Enhanced Linux) provides mandatory access control.
You must understand contexts (user:role:type:level), booleans, and modes.
The exam tests setting file contexts with semanage/restorecon,
toggling booleans with setsebool, and changing SELinux modes.
Always make changes persistent!
        """,
        "commands": [
            {
                "name": "Set File Context (Persistent)",
                "syntax": "semanage fcontext -a -t <type> '<path>(/.*)?' && restorecon -Rv <path>",
                "example": "semanage fcontext -a -t httpd_sys_content_t '/web(/.*)?'\nrestorecon -Rv /web",
                "flags": {
                    "-a": "Add policy rule",
                    "-t": "Set type context",
                    "'<path>(/.*)?'": "Regex for path and subdirs",
                    "restorecon -Rv": "Apply the context now",
                },
            },
            {
                "name": "Set Boolean (Persistent)",
                "syntax": "setsebool -P <boolean> on|off",
                "example": "setsebool -P httpd_can_network_connect on",
                "flags": {
                    "-P": "Make change persistent (CRITICAL!)",
                    "on": "Enable boolean",
                    "off": "Disable boolean",
                },
            },
            {
                "name": "Change SELinux Mode",
                "syntax": "setenforce 0|1 && edit /etc/selinux/config",
                "example": "setenforce 0\nvi /etc/selinux/config (set SELINUX=permissive)",
                "flags": {
                    "0": "Permissive mode (now)",
                    "1": "Enforcing mode (now)",
                    "/etc/selinux/config": "Persistent setting",
                    "SELINUX=": "enforcing, permissive, or disabled",
                },
            },
            {
                "name": "Check Context",
                "syntax": "ls -Z <file>",
                "example": "ls -Zd /var/www/html",
                "flags": {
                    "-Z": "Show SELinux context",
                    "getenforce": "Show current mode",
                    "getsebool -a": "List all booleans",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting -P flag on setsebool (not persistent!)",
            "Not running restorecon after semanage",
            "Wrong regex pattern in semanage (missing (/.*)?)",
            "Setting mode without editing /etc/selinux/config",
            "Using chcon instead of semanage (not persistent)",
        ],
        "exam_tricks": [
            "Exam always wants persistent changes - use -P and semanage",
            "File context needs BOTH semanage AND restorecon",
            "Boolean might already be set but not persistent",
            "Context format is user:role:type:level (you usually change type)",
        ],
    },
    "firewall": {
        "name": "Firewall Configuration",
        "explanation": """
RHEL uses firewalld for dynamic firewall management. Key concepts:

ZONES: Pre-defined security levels applied to interfaces
  - public: Default, untrusted networks (allows ssh, dhcpv6-client)
  - trusted: All traffic allowed
  - home/work/internal: More permissive than public
  - dmz: Limited access for DMZ servers
  - external: For NAT/masquerading
  - block: Reject all incoming (outgoing allowed)
  - drop: Drop all incoming silently

SERVICES vs PORTS:
  - Services: Named rules (http, https, ssh) - preferred method
  - Ports: Numeric (80/tcp, 443/tcp) - for custom apps

PERMANENT vs RUNTIME:
  - Without --permanent: Active now, lost on reload/reboot
  - With --permanent: Saved to config, needs --reload to apply
  - Best practice: Use --permanent then --reload
        """,
        "commands": [
            {
                "name": "Zone Management",
                "syntax": "firewall-cmd --get-zones / --get-default-zone / --set-default-zone=<zone>",
                "example": "firewall-cmd --set-default-zone=trusted",
                "flags": {
                    "--get-zones": "List all available zones",
                    "--get-default-zone": "Show current default zone",
                    "--set-default-zone=": "Change default zone (auto-permanent)",
                    "--get-active-zones": "Show zones with assigned interfaces",
                    "--zone=<zone> --list-all": "Show all settings for a zone",
                },
            },
            {
                "name": "Allow Service",
                "syntax": "firewall-cmd --zone=<zone> --add-service=<service> --permanent",
                "example": "firewall-cmd --add-service=http --permanent && firewall-cmd --reload",
                "flags": {
                    "--add-service=": "Allow a service (http, https, ssh, nfs, etc.)",
                    "--remove-service=": "Remove a service",
                    "--list-services": "List allowed services",
                    "--get-services": "List all available service names",
                    "--permanent": "Make change persistent",
                },
            },
            {
                "name": "Allow Port",
                "syntax": "firewall-cmd --zone=<zone> --add-port=<port>/<protocol> --permanent",
                "example": "firewall-cmd --add-port=8080/tcp --permanent && firewall-cmd --reload",
                "flags": {
                    "--add-port=": "Allow port (e.g., 8080/tcp, 53/udp)",
                    "--remove-port=": "Remove port rule",
                    "--list-ports": "List allowed ports",
                    "--permanent": "Make change persistent",
                },
            },
            {
                "name": "Rich Rules",
                "syntax": "firewall-cmd --add-rich-rule='rule family=ipv4 source address=<ip> port port=<port> protocol=tcp accept'",
                "example": "firewall-cmd --add-rich-rule='rule family=\"ipv4\" source address=\"192.168.1.0/24\" service name=\"http\" accept' --permanent",
                "flags": {
                    "rule family=": "ipv4 or ipv6",
                    "source address=": "Source IP or network",
                    "port port=": "Destination port",
                    "protocol=": "tcp or udp",
                    "service name=": "Use service name instead of port",
                    "accept/reject/drop": "Action to take",
                },
            },
            {
                "name": "Reload & Status",
                "syntax": "firewall-cmd --reload / systemctl status firewalld",
                "example": "firewall-cmd --reload",
                "flags": {
                    "--reload": "Apply permanent changes to runtime",
                    "--complete-reload": "Full reload (drops connections)",
                    "--state": "Check if firewalld is running",
                    "systemctl status firewalld": "Full service status",
                },
            },
            {
                "name": "Interface to Zone",
                "syntax": "firewall-cmd --zone=<zone> --change-interface=<iface> --permanent",
                "example": "firewall-cmd --zone=trusted --change-interface=eth1 --permanent",
                "flags": {
                    "--change-interface=": "Move interface to zone",
                    "--add-interface=": "Add interface to zone",
                    "--remove-interface=": "Remove interface from zone",
                    "--get-zone-of-interface=": "Check which zone an interface is in",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting --permanent (changes lost on reload/reboot)",
            "Forgetting --reload after --permanent (changes not active)",
            "Using wrong zone (check --get-active-zones)",
            "Port format errors (must be port/protocol like 80/tcp)",
            "Rich rule quoting issues (use single quotes outside, escaped doubles inside)",
            "Firewalld not running (systemctl start firewalld)",
        ],
        "exam_tricks": [
            "Always use --permanent then --reload for persistent changes",
            "--set-default-zone is automatically permanent (no --reload needed)",
            "Prefer services over ports when available (--get-services to list)",
            "Rich rules for source IP restrictions (common exam question)",
            "Check firewalld is enabled: systemctl enable --now firewalld",
            "Verify with --list-all after making changes",
        ],
    },
}
