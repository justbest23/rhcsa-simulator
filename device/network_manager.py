"""
Network State Manager for RHCSA Simulator.

Provides backup/restore functionality for network configuration
to prevent losing connectivity during practice.
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class NetworkState:
    """Snapshot of network configuration."""
    timestamp: str
    hostname: str
    connections: List[Dict]
    active_connection: Optional[str]
    primary_interface: Optional[str]
    primary_ip: Optional[str]
    firewall_default_zone: Optional[str]
    firewall_services: List[str]
    firewall_ports: List[str]
    firewall_rich_rules: List[str]


class NetworkStateManager:
    """
    Manages network state backup and restore for safe practice.

    Features:
    - Backup current network state before practice
    - Restore state if something breaks
    - Detect and warn about primary (SSH) interface
    - Print recovery commands for emergency console access
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.logger = logging.getLogger(__name__)
        self._backup_dir = Path.home() / '.rhcsa-simulator' / 'network-backups'
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._current_backup: Optional[NetworkState] = None
        self._primary_interface: Optional[str] = None
        self._primary_ip: Optional[str] = None

        # Detect primary interface on init
        self._detect_primary_interface()

    def _run_cmd(self, cmd: List[str], timeout: int = 10) -> Optional[str]:
        """Run command and return stdout or None on failure."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            self.logger.debug(f"Command failed: {cmd} - {e}")
            return None

    def _detect_primary_interface(self) -> Optional[str]:
        """
        Detect the primary interface (the one with default route / SSH connection).
        """
        # Get default route interface
        output = self._run_cmd(['ip', 'route', 'show', 'default'])
        if output:
            # Format: "default via 10.0.2.2 dev enp0s3 proto dhcp metric 100"
            parts = output.split()
            if 'dev' in parts:
                dev_idx = parts.index('dev')
                if dev_idx + 1 < len(parts):
                    self._primary_interface = parts[dev_idx + 1]

        # Get primary IP
        if self._primary_interface:
            output = self._run_cmd(['ip', '-4', 'addr', 'show', self._primary_interface])
            if output:
                for line in output.splitlines():
                    if 'inet ' in line:
                        # Format: "inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic enp0s3"
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            self._primary_ip = parts[1].split('/')[0]
                            break

        return self._primary_interface

    def get_primary_interface(self) -> Optional[str]:
        """Get the detected primary interface."""
        return self._primary_interface

    def get_primary_ip(self) -> Optional[str]:
        """Get the primary interface's IP address."""
        return self._primary_ip

    def is_primary_interface(self, interface: str) -> bool:
        """Check if the given interface is the primary (SSH) interface."""
        return interface == self._primary_interface

    def capture_state(self) -> NetworkState:
        """Capture current network state."""
        # Get hostname
        hostname = self._run_cmd(['hostname']) or 'unknown'

        # Get all connections
        connections = []
        output = self._run_cmd(['nmcli', '-t', '-f', 'NAME,UUID,TYPE,DEVICE', 'con', 'show'])
        if output:
            for line in output.splitlines():
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 4:
                        connections.append({
                            'name': parts[0],
                            'uuid': parts[1],
                            'type': parts[2],
                            'device': parts[3] if parts[3] != '--' else None
                        })

        # Get active connection on primary interface
        active_conn = None
        if self._primary_interface:
            output = self._run_cmd(['nmcli', '-t', '-f', 'NAME', 'con', 'show', '--active'])
            if output:
                active_conn = output.splitlines()[0] if output.splitlines() else None

        # Get firewall state
        fw_zone = self._run_cmd(['firewall-cmd', '--get-default-zone'])
        fw_services = []
        fw_ports = []
        fw_rich = []

        services_out = self._run_cmd(['firewall-cmd', '--list-services'])
        if services_out:
            fw_services = services_out.split()

        ports_out = self._run_cmd(['firewall-cmd', '--list-ports'])
        if ports_out:
            fw_ports = ports_out.split()

        rich_out = self._run_cmd(['firewall-cmd', '--list-rich-rules'])
        if rich_out:
            fw_rich = [r.strip() for r in rich_out.splitlines() if r.strip()]

        state = NetworkState(
            timestamp=datetime.now().isoformat(),
            hostname=hostname,
            connections=connections,
            active_connection=active_conn,
            primary_interface=self._primary_interface,
            primary_ip=self._primary_ip,
            firewall_default_zone=fw_zone,
            firewall_services=fw_services,
            firewall_ports=fw_ports,
            firewall_rich_rules=fw_rich
        )

        return state

    def backup_state(self, label: str = "auto") -> str:
        """
        Backup current network state.

        Returns:
            str: Path to backup file
        """
        state = self.capture_state()
        self._current_backup = state

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"network_backup_{label}_{timestamp}.json"
        filepath = self._backup_dir / filename

        with open(filepath, 'w') as f:
            json.dump(asdict(state), f, indent=2)

        self.logger.info(f"Network state backed up to {filepath}")
        return str(filepath)

    def list_backups(self) -> List[Dict]:
        """List available backups."""
        backups = []
        for f in sorted(self._backup_dir.glob("network_backup_*.json"), reverse=True):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    backups.append({
                        'file': str(f),
                        'filename': f.name,
                        'timestamp': data.get('timestamp', 'unknown'),
                        'hostname': data.get('hostname', 'unknown'),
                        'primary_ip': data.get('primary_ip', 'unknown')
                    })
            except Exception as e:
                self.logger.warning(f"Could not read backup {f}: {e}")
        return backups

    def load_backup(self, filepath: str) -> Optional[NetworkState]:
        """Load a backup from file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
                return NetworkState(**data)
        except Exception as e:
            self.logger.error(f"Could not load backup {filepath}: {e}")
            return None

    def get_recovery_commands(self, state: Optional[NetworkState] = None) -> List[str]:
        """
        Generate recovery commands to restore network connectivity.
        These can be typed into VirtualBox console if SSH is lost.
        """
        if state is None:
            state = self._current_backup or self.capture_state()

        commands = [
            "# === NETWORK RECOVERY COMMANDS ===",
            "# Type these in VirtualBox console if you lose SSH access",
            "",
        ]

        # Restore hostname
        if state.hostname:
            commands.append(f"hostnamectl set-hostname {state.hostname}")

        # Restore primary connection
        if state.primary_interface and state.primary_ip:
            conn_name = state.active_connection or state.primary_interface
            commands.append(f"")
            commands.append(f"# Restore primary network interface")
            commands.append(f"nmcli con mod '{conn_name}' ipv4.method auto")
            commands.append(f"nmcli con up '{conn_name}'")
            commands.append(f"")
            commands.append(f"# Or set static IP if DHCP fails:")
            commands.append(f"# nmcli con mod '{conn_name}' ipv4.addresses {state.primary_ip}/24 ipv4.method manual")
            commands.append(f"# nmcli con up '{conn_name}'")

        # Restart NetworkManager as last resort
        commands.append(f"")
        commands.append(f"# Last resort - restart NetworkManager:")
        commands.append(f"systemctl restart NetworkManager")

        return commands

    def print_recovery_commands(self, state: Optional[NetworkState] = None):
        """Print recovery commands to console."""
        commands = self.get_recovery_commands(state)
        print("\n" + "=" * 60)
        print("SAVE THESE RECOVERY COMMANDS BEFORE PROCEEDING!")
        print("=" * 60)
        for cmd in commands:
            print(cmd)
        print("=" * 60 + "\n")

    def generate_restore_script(self, state: NetworkState) -> str:
        """Generate a bash script to restore network state."""
        lines = [
            "#!/bin/bash",
            "# Network State Restore Script",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Original state from: {state.timestamp}",
            "",
            "set -e",
            "",
            "echo 'Restoring network state...'",
            "",
        ]

        # Restore hostname
        lines.append(f"# Restore hostname")
        lines.append(f"hostnamectl set-hostname '{state.hostname}'")
        lines.append("")

        # Restore firewall default zone
        if state.firewall_default_zone:
            lines.append(f"# Restore firewall default zone")
            lines.append(f"firewall-cmd --set-default-zone={state.firewall_default_zone}")
            lines.append("")

        # Bring up primary connection
        if state.active_connection:
            lines.append(f"# Activate primary connection")
            lines.append(f"nmcli con up '{state.active_connection}' || true")
            lines.append("")

        lines.append("echo 'Network state restored.'")
        lines.append("echo 'Current IP addresses:'")
        lines.append("ip -4 addr show | grep 'inet '")

        return '\n'.join(lines)

    def cleanup_practice_connections(self, patterns: List[str] = None) -> List[str]:
        """
        Remove connections created during practice.

        Args:
            patterns: Connection name patterns to remove (default: lab-*, test-*, practice-*)

        Returns:
            List of removed connection names
        """
        if patterns is None:
            patterns = ['lab-', 'test-', 'practice-', 'team0', 'team1']

        removed = []
        output = self._run_cmd(['nmcli', '-t', '-f', 'NAME,UUID', 'con', 'show'])

        if output:
            for line in output.splitlines():
                if ':' in line:
                    name, uuid = line.split(':', 1)
                    # Check if name matches any pattern
                    if any(name.startswith(p) or name == p for p in patterns):
                        # Don't remove if it's active on primary interface
                        if name == self._current_backup.active_connection if self._current_backup else False:
                            self.logger.warning(f"Skipping active connection: {name}")
                            continue

                        result = subprocess.run(
                            ['nmcli', 'con', 'delete', uuid],
                            capture_output=True, text=True
                        )
                        if result.returncode == 0:
                            removed.append(name)
                            self.logger.info(f"Removed practice connection: {name}")
                        else:
                            self.logger.warning(f"Failed to remove {name}: {result.stderr}")

        return removed

    def cleanup_firewall_additions(self, baseline: NetworkState) -> Dict[str, List[str]]:
        """
        Remove firewall rules that were added after baseline was captured.

        Returns:
            Dict with removed services, ports, and rich rules
        """
        removed = {'services': [], 'ports': [], 'rich_rules': []}

        # Get current state
        current = self.capture_state()

        # Remove services not in baseline
        for svc in current.firewall_services:
            if svc not in baseline.firewall_services:
                result = subprocess.run(
                    ['firewall-cmd', '--remove-service=' + svc, '--permanent'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    removed['services'].append(svc)

        # Remove ports not in baseline
        for port in current.firewall_ports:
            if port not in baseline.firewall_ports:
                result = subprocess.run(
                    ['firewall-cmd', '--remove-port=' + port, '--permanent'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    removed['ports'].append(port)

        # Remove rich rules not in baseline
        for rule in current.firewall_rich_rules:
            if rule not in baseline.firewall_rich_rules:
                result = subprocess.run(
                    ['firewall-cmd', '--remove-rich-rule=' + rule, '--permanent'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    removed['rich_rules'].append(rule)

        # Reload if anything was removed
        if any(removed.values()):
            subprocess.run(['firewall-cmd', '--reload'], capture_output=True)

        return removed

    def full_cleanup(self, backup_file: Optional[str] = None) -> Dict:
        """
        Perform full network cleanup based on backup state.

        Args:
            backup_file: Path to backup file (uses most recent if None)

        Returns:
            Summary of cleanup actions
        """
        # Load baseline state
        if backup_file:
            baseline = self.load_backup(backup_file)
        elif self._current_backup:
            baseline = self._current_backup
        else:
            backups = self.list_backups()
            if backups:
                baseline = self.load_backup(backups[0]['file'])
            else:
                return {'error': 'No backup available'}

        if not baseline:
            return {'error': 'Could not load backup'}

        summary = {
            'connections_removed': [],
            'firewall_cleaned': {},
            'hostname_restored': False
        }

        # Clean practice connections
        summary['connections_removed'] = self.cleanup_practice_connections()

        # Clean firewall additions
        summary['firewall_cleaned'] = self.cleanup_firewall_additions(baseline)

        # Restore hostname if changed
        current_hostname = self._run_cmd(['hostname'])
        if current_hostname != baseline.hostname:
            result = subprocess.run(
                ['hostnamectl', 'set-hostname', baseline.hostname],
                capture_output=True, text=True
            )
            summary['hostname_restored'] = result.returncode == 0

        return summary


# Singleton accessor
_network_manager = None

def get_network_manager() -> NetworkStateManager:
    """Get the singleton NetworkStateManager instance."""
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkStateManager()
    return _network_manager


def get_available_interfaces() -> List[str]:
    """
    Get list of available network interfaces (excluding lo).

    Returns:
        List of interface names (e.g., ['enp0s3', 'enp0s8'])
    """
    interfaces = []
    try:
        result = subprocess.run(
            ['ip', '-o', 'link', 'show'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # Format: "2: enp0s3: <BROADCAST,MULTICAST,UP,LOWER_UP> ..."
                parts = line.split(':')
                if len(parts) >= 2:
                    iface = parts[1].strip().split('@')[0]  # Handle veth@xxx format
                    # Skip loopback and virtual interfaces
                    if iface not in ['lo'] and not iface.startswith(('veth', 'docker', 'br-', 'virbr')):
                        interfaces.append(iface)
    except Exception:
        pass
    return interfaces


def get_primary_interface() -> Optional[str]:
    """
    Get the primary network interface (with default route).

    Returns:
        Interface name or None
    """
    nm = get_network_manager()
    return nm.get_primary_interface()


def get_secondary_interfaces() -> List[str]:
    """
    Get interfaces that are NOT the primary (safe for practice).

    Returns:
        List of secondary interface names
    """
    all_ifaces = get_available_interfaces()
    primary = get_primary_interface()

    if primary and primary in all_ifaces:
        return [i for i in all_ifaces if i != primary]
    return all_ifaces


def get_practice_interface() -> Optional[str]:
    """
    Get the best interface for practice (secondary if available, else primary with warning).

    Returns:
        Interface name to use for practice, or None
    """
    secondary = get_secondary_interfaces()
    if secondary:
        return secondary[0]

    # Fall back to primary
    return get_primary_interface()


def get_connection_for_interface(interface: str) -> Optional[str]:
    """
    Get the connection name associated with an interface.

    Args:
        interface: Interface name (e.g., 'enp0s3')

    Returns:
        Connection name or None
    """
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,DEVICE', 'con', 'show', '--active'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ':' in line:
                    name, device = line.rsplit(':', 1)
                    if device == interface:
                        return name
    except Exception:
        pass
    return None
