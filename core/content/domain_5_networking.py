"""
Domain 5: Network & DNS
Categories: networking
"""

CONTENT = {
    "networking": {
        "name": "Networking Configuration",
        "explanation": """
Network configuration in RHEL 8/9 uses NetworkManager and the nmcli command.
You must understand the difference between CONNECTIONS and DEVICES:
  - DEVICE: Physical or virtual network interface (eth0, enp0s3)
  - CONNECTION: Configuration profile that can be applied to a device

Key concepts:
  - One device can have multiple connection profiles (only one active)
  - Connection names may differ from device/interface names
  - Use 'nmcli con' for persistent config, 'ip' for temporary changes
  - Config files stored in /etc/NetworkManager/system-connections/

The exam tests: static IP configuration, DNS, hostname, creating connections,
and troubleshooting network issues using nmcli and ip commands.
        """,
        "commands": [
            {
                "name": "Show Connections & Devices",
                "syntax": "nmcli connection show / nmcli device status",
                "example": "nmcli con show --active",
                "flags": {
                    "con show": "List all connection profiles",
                    "con show --active": "Show only active connections",
                    "con show <name>": "Show detailed connection info",
                    "device status": "Show all devices and their state",
                    "device show <dev>": "Show device details",
                    "general status": "Show overall NetworkManager status",
                },
            },
            {
                "name": "Create New Connection",
                "syntax": "nmcli con add type ethernet con-name <name> ifname <device>",
                "example": "nmcli con add type ethernet con-name office ifname eth1 ipv4.addresses 10.0.0.50/24 ipv4.method manual",
                "flags": {
                    "con add": "Create a new connection profile",
                    "type ethernet": "Wired connection (also: wifi, bond, team)",
                    "con-name": "Name for the connection profile",
                    "ifname": "Physical interface to bind to",
                    "autoconnect yes/no": "Auto-activate on boot",
                },
            },
            {
                "name": "Configure Static IP",
                "syntax": "nmcli con mod <name> ipv4.addresses <ip>/<prefix> ipv4.gateway <gw> ipv4.method manual",
                "example": "nmcli con mod eth0 ipv4.addresses 192.168.1.100/24 ipv4.gateway 192.168.1.1 ipv4.method manual",
                "flags": {
                    "ipv4.addresses": "IP with CIDR prefix (required)",
                    "ipv4.gateway": "Default gateway",
                    "ipv4.method manual": "Static IP (CRITICAL - must set!)",
                    "ipv4.method auto": "DHCP",
                    "+ipv4.addresses": "Add secondary IP",
                },
            },
            {
                "name": "Set DNS Servers",
                "syntax": "nmcli con mod <name> ipv4.dns '<dns1> <dns2>'",
                "example": "nmcli con mod eth0 ipv4.dns '8.8.8.8 8.8.4.4'",
                "flags": {
                    "ipv4.dns": "Space-separated DNS IPs (quoted)",
                    "+ipv4.dns": "Add DNS server to existing",
                    "-ipv4.dns": "Remove DNS server",
                    "ipv4.ignore-auto-dns yes": "Ignore DHCP-provided DNS",
                },
            },
            {
                "name": "Set Hostname",
                "syntax": "hostnamectl set-hostname <hostname>",
                "example": "hostnamectl set-hostname server1.example.com",
                "flags": {
                    "set-hostname": "Set all hostname types (persistent)",
                    "status": "Show current hostname info",
                    "--static": "Set only static hostname",
                    "--transient": "Set only transient (temporary)",
                    "--pretty": "Set pretty/display hostname",
                },
            },
            {
                "name": "Activate/Deactivate Connection",
                "syntax": "nmcli con up/down <name>",
                "example": "nmcli con up eth0",
                "flags": {
                    "con up <name>": "Activate connection profile",
                    "con down <name>": "Deactivate connection",
                    "con reload": "Reload all connection files",
                    "device connect <dev>": "Activate device with best profile",
                    "device disconnect <dev>": "Disconnect device",
                },
            },
            {
                "name": "Delete Connection",
                "syntax": "nmcli con delete <name>",
                "example": "nmcli con delete old-connection",
                "flags": {
                    "con delete": "Remove connection profile permanently",
                    "con delete id <name>": "Delete by connection name",
                },
            },
            {
                "name": "Troubleshooting Commands",
                "syntax": "ip addr / ip route / ss -tuln",
                "example": "ip addr show eth0",
                "flags": {
                    "ip addr": "Show IP addresses on all interfaces",
                    "ip addr show <dev>": "Show IP for specific device",
                    "ip route": "Show routing table",
                    "ip route show default": "Show default gateway",
                    "ss -tuln": "Show listening ports (TCP/UDP)",
                    "ping -c 3 <host>": "Test connectivity",
                    "nmcli -f all con show <name>": "Show all connection properties",
                },
            },
            {
                "name": "Network Teaming",
                "syntax": "nmcli con add type team con-name <name> ifname <team> team.runner <mode>",
                "example": "nmcli con add type team con-name team0 ifname team0 team.runner activebackup",
                "flags": {
                    "type team": "Create team master interface",
                    "type team-slave": "Create team port/slave",
                    "team.runner": "Mode: activebackup, roundrobin, loadbalance, lacp",
                    "master <team>": "Assign slave to master team",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting ipv4.method manual (IP set but DHCP still used)",
            "Forgetting CIDR notation (/24) in IP address",
            "Not quoting DNS servers when space-separated",
            "Using 'nmcli device' to configure (use 'nmcli connection')",
            "Forgetting 'nmcli con up' to apply changes",
            "Confusing connection name with interface/device name",
            "Not checking 'nmcli con show' to verify config before activating",
        ],
        "exam_tricks": [
            "Always use nmcli, never edit config files directly on exam",
            "Connection names can be anything - don't assume they match interface",
            "'nmcli con mod' only saves config; 'nmcli con up' applies it",
            "Use 'nmcli con show <name>' to verify settings before activation",
            "If hostname must be FQDN, include domain (server.example.com)",
            "ip commands are temporary - reboot loses changes; nmcli persists",
            "Check 'nmcli device status' to see which connections are active",
        ],
    },
}
