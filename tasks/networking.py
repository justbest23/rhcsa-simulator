"""
Network configuration tasks for RHCSA exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import (
    get_ip_address, get_interface_state, validate_interface_ip,
    get_default_gateway, get_dns_servers, validate_dns_server,
    get_nmcli_connection_info
)
from validators.file_validators import validate_file_contains


logger = logging.getLogger(__name__)


def _get_practice_interface():
    """Get an interface suitable for practice (prefers non-primary)."""
    try:
        from device.network_manager import (
            get_practice_interface, get_primary_interface,
            get_connection_for_interface
        )
        iface = get_practice_interface()
        if iface:
            return iface
    except Exception:
        pass
    return 'eth0'  # Fallback


def _get_primary_interface():
    """Get the primary network interface."""
    try:
        from device.network_manager import get_primary_interface
        iface = get_primary_interface()
        if iface:
            return iface
    except Exception:
        pass
    return 'eth0'  # Fallback


def _get_connection_name(interface):
    """Get connection name for an interface."""
    try:
        from device.network_manager import get_connection_for_interface
        conn = get_connection_for_interface(interface)
        if conn:
            return conn
    except Exception:
        pass
    return interface  # Fallback to interface name


@TaskRegistry.register("networking")
class ConfigureStaticIPTask(BaseTask):
    """Configure static IP address using nmcli."""

    def __init__(self):
        super().__init__(
            id="net_static_ip_001",
            category="networking",
            difficulty="medium",
            points=12
        )
        self.interface = None
        self.ip_address = None
        self.netmask = None
        self.connection_name = None

    def generate(self, **params):
        """Generate static IP configuration task."""
        self.interface = params.get('interface') or _get_practice_interface()
        self.ip_address = params.get('ip', f'192.168.{random.randint(1,254)}.{random.randint(10,250)}')
        self.netmask = params.get('netmask', '24')
        self.connection_name = params.get('connection', self.interface)

        self.description = (
            f"Configure static IP address:\n"
            f"  - Interface: {self.interface}\n"
            f"  - IP Address: {self.ip_address}/{self.netmask}\n"
            f"  - Connection name: {self.connection_name}\n"
            f"  - Use nmcli to configure\n"
            f"  - Configuration must persist across reboots\n"
            f"  - Activate the connection"
        )

        self.hints = [
            f"Use nmcli to modify connection: nmcli con mod {self.connection_name}",
            f"Set IP: nmcli con mod {self.connection_name} ipv4.addresses {self.ip_address}/{self.netmask}",
            f"Set method to manual: nmcli con mod {self.connection_name} ipv4.method manual",
            f"Activate: nmcli con up {self.connection_name}",
            f"Verify: ip addr show {self.interface} or nmcli con show {self.connection_name}",
            f"Check persistent config: nmcli -f ipv4 con show {self.connection_name}"
        ]

        return self

    def validate(self):
        """Validate static IP configuration."""
        checks = []
        total_points = 0

        # Check 1: Interface has correct IP (6 points)
        actual_ip = get_ip_address(self.interface)
        if actual_ip == self.ip_address:
            checks.append(ValidationCheck(
                name="ip_address_set",
                passed=True,
                points=6,
                message=f"IP address {self.ip_address} correctly configured"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="ip_address_set",
                passed=False,
                points=0,
                max_points=6,
                message=f"IP address is {actual_ip}, expected {self.ip_address}"
            ))

        # Check 2: Interface is UP (3 points)
        state = get_interface_state(self.interface)
        if state == 'UP':
            checks.append(ValidationCheck(
                name="interface_up",
                passed=True,
                points=3,
                message=f"Interface {self.interface} is UP"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="interface_up",
                passed=False,
                points=0,
                max_points=3,
                message=f"Interface {self.interface} is {state}"
            ))

        # Check 3: Connection configured persistently (3 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info:
            # Check if ipv4.method is manual
            if conn_info.get('ipv4.method') == 'manual':
                checks.append(ValidationCheck(
                    name="persistent_config",
                    passed=True,
                    points=3,
                    message=f"Connection configured with manual IPv4"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="persistent_config",
                    passed=True,
                    points=2,
                    message=f"Connection exists but IPv4 method is {conn_info.get('ipv4.method')} (partial credit)"
                ))
                total_points += 2
        else:
            checks.append(ValidationCheck(
                name="persistent_config",
                passed=False,
                points=0,
                max_points=3,
                message=f"Connection {self.connection_name} not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureDefaultGatewayTask(BaseTask):
    """Configure default gateway."""

    def __init__(self):
        super().__init__(
            id="net_gateway_001",
            category="networking",
            difficulty="easy",
            points=8
        )
        self.gateway = None
        self.connection_name = None

    def generate(self, **params):
        """Generate gateway configuration task."""
        self.gateway = params.get('gateway', f'192.168.{random.randint(1,254)}.1')
        iface = _get_practice_interface()
        self.connection_name = params.get('connection') or _get_connection_name(iface) or iface

        self.description = (
            f"Configure default gateway:\n"
            f"  - Gateway IP: {self.gateway}\n"
            f"  - Connection: {self.connection_name}\n"
            f"  - Use nmcli to configure\n"
            f"  - Configuration must be persistent"
        )

        self.hints = [
            f"Set gateway: nmcli con mod {self.connection_name} ipv4.gateway {self.gateway}",
            f"Activate connection: nmcli con up {self.connection_name}",
            "Verify: ip route show default",
            f"Or verify: nmcli -f ipv4 con show {self.connection_name}"
        ]

        return self

    def validate(self):
        """Validate gateway configuration."""
        checks = []
        total_points = 0

        # Check 1: Default gateway is set (5 points)
        current_gateway = get_default_gateway()
        if current_gateway == self.gateway:
            checks.append(ValidationCheck(
                name="gateway_set",
                passed=True,
                points=5,
                message=f"Default gateway is {self.gateway}"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="gateway_set",
                passed=False,
                points=0,
                max_points=5,
                message=f"Default gateway is {current_gateway}, expected {self.gateway}"
            ))

        # Check 2: Gateway configured persistently in connection (3 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info and self.gateway in str(conn_info.get('ipv4.gateway', '')):
            checks.append(ValidationCheck(
                name="gateway_persistent",
                passed=True,
                points=3,
                message=f"Gateway configured persistently"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="gateway_persistent",
                passed=False,
                points=0,
                max_points=3,
                message=f"Gateway not configured persistently in connection"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureDNSTask(BaseTask):
    """Configure DNS servers."""

    def __init__(self):
        super().__init__(
            id="net_dns_001",
            category="networking",
            difficulty="easy",
            points=8
        )
        self.dns_servers = None
        self.connection_name = None

    def generate(self, **params):
        """Generate DNS configuration task."""
        self.dns_servers = params.get('dns', ['8.8.8.8', '8.8.4.4'])
        if isinstance(self.dns_servers, str):
            self.dns_servers = [self.dns_servers]
        iface = _get_practice_interface()
        self.connection_name = params.get('connection') or _get_connection_name(iface) or iface

        dns_list = ' '.join(self.dns_servers)

        self.description = (
            f"Configure DNS servers:\n"
            f"  - DNS servers: {', '.join(self.dns_servers)}\n"
            f"  - Connection: {self.connection_name}\n"
            f"  - Use nmcli to configure\n"
            f"  - Configuration must be persistent"
        )

        self.hints = [
            f"Set DNS: nmcli con mod {self.connection_name} ipv4.dns \"{dns_list}\"",
            f"Activate: nmcli con up {self.connection_name}",
            "Verify: cat /etc/resolv.conf",
            f"Or verify: nmcli -f ipv4 con show {self.connection_name}"
        ]

        return self

    def validate(self):
        """Validate DNS configuration."""
        checks = []
        total_points = 0

        # Check 1: DNS servers are configured (5 points)
        current_dns = get_dns_servers()
        dns_configured = all(dns in current_dns for dns in self.dns_servers)

        if dns_configured:
            checks.append(ValidationCheck(
                name="dns_configured",
                passed=True,
                points=5,
                message=f"DNS servers correctly configured"
            ))
            total_points += 5
        elif any(dns in current_dns for dns in self.dns_servers):
            checks.append(ValidationCheck(
                name="dns_configured",
                passed=True,
                points=3,
                message=f"Some DNS servers configured (partial credit)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="dns_configured",
                passed=False,
                points=0,
                max_points=5,
                message=f"DNS servers not configured. Current: {current_dns}"
            ))

        # Check 2: DNS configured persistently (3 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info and any(dns in str(conn_info.get('ipv4.dns', '')) for dns in self.dns_servers):
            checks.append(ValidationCheck(
                name="dns_persistent",
                passed=True,
                points=3,
                message=f"DNS configured persistently"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="dns_persistent",
                passed=False,
                points=0,
                max_points=3,
                message=f"DNS not configured persistently in connection"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class SetHostnameTask(BaseTask):
    """Set system hostname."""

    def __init__(self):
        super().__init__(
            id="net_hostname_001",
            category="networking",
            difficulty="easy",
            points=6
        )
        self.hostname = None

    def generate(self, **params):
        """Generate hostname task."""
        hostnames = ['server1.example.com', 'rhel9.lab.local', 'workstation.test.net']
        self.hostname = params.get('hostname', random.choice(hostnames))

        self.description = (
            f"Set system hostname:\n"
            f"  - Hostname: {self.hostname}\n"
            f"  - Use hostnamectl command\n"
            f"  - Configuration must be persistent across reboots"
        )

        self.hints = [
            f"Set hostname: hostnamectl set-hostname {self.hostname}",
            "Verify: hostnamectl status",
            "Or verify: hostname",
            "Check persistent config: cat /etc/hostname"
        ]

        return self

    def validate(self):
        """Validate hostname configuration."""
        checks = []
        total_points = 0

        from validators.safe_executor import execute_safe

        # Check 1: Current hostname (3 points)
        result = execute_safe(['hostname'])
        current_hostname = result.stdout.strip() if result.success else None

        if current_hostname == self.hostname:
            checks.append(ValidationCheck(
                name="current_hostname",
                passed=True,
                points=3,
                message=f"Hostname is {self.hostname}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="current_hostname",
                passed=False,
                points=0,
                max_points=3,
                message=f"Hostname is {current_hostname}, expected {self.hostname}"
            ))

        # Check 2: Persistent hostname in /etc/hostname (3 points)
        if validate_file_contains('/etc/hostname', self.hostname):
            checks.append(ValidationCheck(
                name="persistent_hostname",
                passed=True,
                points=3,
                message=f"Hostname configured persistently"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="persistent_hostname",
                passed=False,
                points=0,
                max_points=3,
                message=f"Hostname not in /etc/hostname"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureNetworkFullTask(BaseTask):
    """Complete network configuration (compound task)."""

    def __init__(self):
        super().__init__(
            id="net_full_config_001",
            category="networking",
            difficulty="exam",
            points=15
        )
        self.interface = None
        self.ip_address = None
        self.netmask = None
        self.gateway = None
        self.dns = None
        self.connection_name = None

    def generate(self, **params):
        """Generate complete network configuration task."""
        self.interface = params.get('interface') or _get_practice_interface()
        self.ip_address = params.get('ip', f'192.168.{random.randint(1,254)}.{random.randint(10,250)}')
        self.netmask = params.get('netmask', '24')
        self.gateway = params.get('gateway', f'192.168.{self.ip_address.split(".")[2]}.1')
        self.dns = params.get('dns', ['8.8.8.8', '8.8.4.4'])
        if isinstance(self.dns, str):
            self.dns = [self.dns]
        self.connection_name = params.get('connection') or _get_connection_name(self.interface) or self.interface

        self.description = (
            f"Configure complete network settings:\n"
            f"  - Interface: {self.interface}\n"
            f"  - IP Address: {self.ip_address}/{self.netmask}\n"
            f"  - Gateway: {self.gateway}\n"
            f"  - DNS Servers: {', '.join(self.dns)}\n"
            f"  - Connection: {self.connection_name}\n"
            f"  - All configuration must persist across reboots\n"
            f"  - Use nmcli for configuration"
        )

        dns_list = ' '.join(self.dns)

        self.hints = [
            f"Set static IP: nmcli con mod {self.connection_name} ipv4.addresses {self.ip_address}/{self.netmask}",
            f"Set method: nmcli con mod {self.connection_name} ipv4.method manual",
            f"Set gateway: nmcli con mod {self.connection_name} ipv4.gateway {self.gateway}",
            f"Set DNS: nmcli con mod {self.connection_name} ipv4.dns \"{dns_list}\"",
            f"Activate: nmcli con up {self.connection_name}",
            "Verify: ip addr show; ip route; cat /etc/resolv.conf"
        ]

        return self

    def validate(self):
        """Validate complete network configuration."""
        checks = []
        total_points = 0

        # Check 1: IP address (5 points)
        actual_ip = get_ip_address(self.interface)
        if actual_ip == self.ip_address:
            checks.append(ValidationCheck(
                name="ip_configured",
                passed=True,
                points=5,
                message=f"IP address correctly configured"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="ip_configured",
                passed=False,
                points=0,
                max_points=5,
                message=f"IP is {actual_ip}, expected {self.ip_address}"
            ))

        # Check 2: Gateway (4 points)
        current_gateway = get_default_gateway()
        if current_gateway == self.gateway:
            checks.append(ValidationCheck(
                name="gateway_configured",
                passed=True,
                points=4,
                message=f"Gateway correctly configured"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="gateway_configured",
                passed=False,
                points=0,
                max_points=4,
                message=f"Gateway is {current_gateway}, expected {self.gateway}"
            ))

        # Check 3: DNS (3 points)
        current_dns = get_dns_servers()
        dns_ok = all(dns in current_dns for dns in self.dns)
        if dns_ok:
            checks.append(ValidationCheck(
                name="dns_configured",
                passed=True,
                points=3,
                message=f"DNS servers correctly configured"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="dns_configured",
                passed=False,
                points=0,
                max_points=3,
                message=f"DNS not fully configured"
            ))

        # Check 4: Interface UP (3 points)
        state = get_interface_state(self.interface)
        if state == 'UP':
            checks.append(ValidationCheck(
                name="interface_up",
                passed=True,
                points=3,
                message=f"Interface is UP"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="interface_up",
                passed=False,
                points=0,
                max_points=3,
                message=f"Interface is {state}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureFirewallServiceTask(BaseTask):
    """Allow a service through the firewall."""

    def __init__(self):
        super().__init__(
            id="net_firewall_service_001",
            category="networking",
            difficulty="medium",
            points=8
        )
        self.service = None
        self.zone = None

    def generate(self, **params):
        services = ['http', 'https', 'ssh', 'nfs', 'samba', 'ftp']
        self.service = params.get('service', random.choice(services))
        self.zone = params.get('zone', 'public')

        self.description = (
            f"Configure firewall to allow a service:\n"
            f"  - Service: {self.service}\n"
            f"  - Zone: {self.zone}\n"
            f"  - Make the change permanent\n"
            f"  - Ensure firewalld is running"
        )

        self.hints = [
            "Ensure firewalld is running: systemctl status firewalld",
            f"Add service: firewall-cmd --zone={self.zone} --add-service={self.service} --permanent",
            "Reload firewall: firewall-cmd --reload",
            f"Verify: firewall-cmd --zone={self.zone} --list-services",
            "Without --permanent, changes are lost on reload/reboot"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: Firewalld is running (3 points)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=True,
                points=3,
                message=f"firewalld is running"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=False,
                points=0,
                max_points=3,
                message=f"firewalld is not running"
            ))

        # Check 2: Service is allowed (5 points)
        # Check runtime config
        result = execute_safe(['firewall-cmd', f'--zone={self.zone}', '--list-services'])
        runtime_has_service = result.success and self.service in result.stdout

        # Also check permanent config
        result_perm = execute_safe(['firewall-cmd', f'--zone={self.zone}', '--list-services', '--permanent'])
        permanent_has_service = result_perm.success and self.service in result_perm.stdout

        if runtime_has_service:
            checks.append(ValidationCheck(
                name="service_allowed",
                passed=True,
                points=5,
                message=f"Service '{self.service}' is allowed in zone {self.zone}"
            ))
            total_points += 5
        elif permanent_has_service:
            # Service is in permanent config but not runtime - user forgot to reload
            checks.append(ValidationCheck(
                name="service_allowed",
                passed=False,
                points=2,  # Partial credit
                max_points=5,
                message=f"Service '{self.service}' is in permanent config but not active. Run: firewall-cmd --reload"
            ))
            total_points += 2
        else:
            # Check if maybe wrong zone
            result_default = execute_safe(['firewall-cmd', '--list-services'])
            if result_default.success and self.service in result_default.stdout:
                checks.append(ValidationCheck(
                    name="service_allowed",
                    passed=False,
                    points=1,
                    max_points=5,
                    message=f"Service '{self.service}' found in default zone, but task requires zone '{self.zone}'"
                ))
                total_points += 1
            else:
                checks.append(ValidationCheck(
                    name="service_allowed",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Service '{self.service}' is not allowed in zone {self.zone}"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureFirewallPortTask(BaseTask):
    """Allow a specific port through the firewall."""

    def __init__(self):
        super().__init__(
            id="net_firewall_port_001",
            category="networking",
            difficulty="medium",
            points=8
        )
        self.port = None
        self.protocol = None
        self.zone = None

    def generate(self, **params):
        ports = [8080, 8443, 3000, 5000, 9090]
        self.port = params.get('port', random.choice(ports))
        self.protocol = params.get('protocol', 'tcp')
        self.zone = params.get('zone', 'public')

        self.description = (
            f"Configure firewall to allow a port:\n"
            f"  - Port: {self.port}/{self.protocol}\n"
            f"  - Zone: {self.zone}\n"
            f"  - Make the change permanent\n"
            f"  - Reload firewall to apply"
        )

        self.hints = [
            f"Add port: firewall-cmd --zone={self.zone} --add-port={self.port}/{self.protocol} --permanent",
            "Reload: firewall-cmd --reload",
            f"Verify: firewall-cmd --zone={self.zone} --list-ports",
            "Port format: <port>/<protocol> (e.g., 8080/tcp)",
            "Check current zone: firewall-cmd --get-active-zones"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: Firewalld is running (3 points)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=True,
                points=3,
                message=f"firewalld is running"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=False,
                points=0,
                max_points=3,
                message=f"firewalld is not running"
            ))

        # Check 2: Port is allowed (5 points)
        port_str = f'{self.port}/{self.protocol}'

        # Check runtime config
        result = execute_safe(['firewall-cmd', f'--zone={self.zone}', '--list-ports'])
        runtime_has_port = result.success and port_str in result.stdout

        # Check permanent config
        result_perm = execute_safe(['firewall-cmd', f'--zone={self.zone}', '--list-ports', '--permanent'])
        permanent_has_port = result_perm.success and port_str in result_perm.stdout

        if runtime_has_port:
            checks.append(ValidationCheck(
                name="port_allowed",
                passed=True,
                points=5,
                message=f"Port {port_str} is allowed"
            ))
            total_points += 5
        elif permanent_has_port:
            checks.append(ValidationCheck(
                name="port_allowed",
                passed=False,
                points=2,
                max_points=5,
                message=f"Port {port_str} is in permanent config but not active. Run: firewall-cmd --reload"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="port_allowed",
                passed=False,
                points=0,
                max_points=5,
                message=f"Port {port_str} is not allowed in zone {self.zone}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureFirewallRichRuleTask(BaseTask):
    """Configure a rich rule in firewalld."""

    def __init__(self):
        super().__init__(
            id="net_firewall_rich_001",
            category="networking",
            difficulty="exam",
            points=12
        )
        self.source_ip = None
        self.port = None
        self.action = None

    def generate(self, **params):
        self.source_ip = params.get('source', f'192.168.{random.randint(1,254)}.0/24')
        self.port = params.get('port', random.choice([22, 80, 443, 8080]))
        self.action = params.get('action', 'accept')

        self.description = (
            f"Configure a firewall rich rule:\n"
            f"  - Allow traffic from: {self.source_ip}\n"
            f"  - To port: {self.port}/tcp\n"
            f"  - Action: {self.action}\n"
            f"  - Make the rule permanent\n"
            f"  - Reload firewall to apply"
        )

        self.hints = [
            f"Rich rule format: rule family='ipv4' source address='{self.source_ip}' port port={self.port} protocol=tcp accept",
            f"Add rule: firewall-cmd --add-rich-rule='rule family=\"ipv4\" source address=\"{self.source_ip}\" port port=\"{self.port}\" protocol=\"tcp\" accept' --permanent",
            "Reload: firewall-cmd --reload",
            "List rich rules: firewall-cmd --list-rich-rules",
            "Rich rules allow more complex firewall configurations"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: Firewalld is running (4 points)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=True,
                points=4,
                message=f"firewalld is running"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=False,
                points=0,
                max_points=4,
                message=f"firewalld is not running"
            ))

        # Check 2: Rich rule exists (8 points)
        result = execute_safe(['firewall-cmd', '--list-rich-rules'])
        if result.success and self.source_ip in result.stdout and str(self.port) in result.stdout:
            checks.append(ValidationCheck(
                name="rich_rule_exists",
                passed=True,
                points=8,
                message=f"Rich rule configured correctly"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="rich_rule_exists",
                passed=False,
                points=0,
                max_points=8,
                message=f"Rich rule not found or incomplete"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class CreateConnectionTask(BaseTask):
    """Create a new network connection from scratch."""

    def __init__(self):
        super().__init__(
            id="net_create_conn_001",
            category="networking",
            difficulty="medium",
            points=10
        )
        self.connection_name = None
        self.interface = None
        self.ip_address = None
        self.netmask = None

    def generate(self, **params):
        """Generate create connection task."""
        self.connection_name = params.get('connection', 'lab-connection')
        # Prefer secondary interface for new connections to avoid SSH disruption
        try:
            from device.network_manager import get_secondary_interfaces
            secondary = get_secondary_interfaces()
            default_iface = secondary[0] if secondary else _get_practice_interface()
        except Exception:
            default_iface = _get_practice_interface()
        self.interface = params.get('interface') or default_iface
        self.ip_address = params.get('ip', f'10.0.{random.randint(1,254)}.{random.randint(10,250)}')
        self.netmask = params.get('netmask', '24')

        self.description = (
            f"Create a NEW network connection:\n"
            f"  - Connection name: {self.connection_name}\n"
            f"  - Interface: {self.interface}\n"
            f"  - IP Address: {self.ip_address}/{self.netmask}\n"
            f"  - Method: Static (manual)\n"
            f"  - The connection should be created, not just modified"
        )

        self.hints = [
            f"Create connection: nmcli con add type ethernet con-name {self.connection_name} ifname {self.interface}",
            f"Set IP: nmcli con mod {self.connection_name} ipv4.addresses {self.ip_address}/{self.netmask}",
            f"Set method: nmcli con mod {self.connection_name} ipv4.method manual",
            f"Activate: nmcli con up {self.connection_name}",
            "Key difference: 'con add' creates new, 'con mod' modifies existing"
        ]

        return self

    def validate(self):
        """Validate connection creation."""
        checks = []
        total_points = 0

        # Check 1: Connection exists (4 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info:
            checks.append(ValidationCheck(
                name="connection_exists",
                passed=True,
                points=4,
                message=f"Connection '{self.connection_name}' exists"
            ))
            total_points += 4

            # Check 2: Correct interface (2 points)
            if conn_info.get('connection.interface-name') == self.interface:
                checks.append(ValidationCheck(
                    name="correct_interface",
                    passed=True,
                    points=2,
                    message=f"Connection bound to {self.interface}"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="correct_interface",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Interface mismatch"
                ))

            # Check 3: IP configured (4 points)
            if self.ip_address in str(conn_info.get('ipv4.addresses', '')):
                checks.append(ValidationCheck(
                    name="ip_configured",
                    passed=True,
                    points=4,
                    message=f"IP {self.ip_address} configured"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="ip_configured",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"IP not configured correctly"
                ))
        else:
            checks.append(ValidationCheck(
                name="connection_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Connection '{self.connection_name}' not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureFirewallZoneTask(BaseTask):
    """Configure firewall zone settings."""

    def __init__(self):
        super().__init__(
            id="net_firewall_zone_001",
            category="networking",
            difficulty="medium",
            points=10
        )
        self.zone = None
        self.interface = None
        self.set_default = False

    def generate(self, **params):
        """Generate firewall zone task."""
        zones = ['trusted', 'home', 'internal', 'work', 'dmz', 'external', 'block']
        self.zone = params.get('zone', random.choice(zones))
        self.interface = params.get('interface') or _get_practice_interface()
        self.set_default = params.get('set_default', random.choice([True, False]))

        if self.set_default:
            self.description = (
                f"Configure firewall default zone:\n"
                f"  - Set default zone to: {self.zone}\n"
                f"  - Make the change permanent\n"
                f"  - Ensure firewalld is running"
            )
            self.hints = [
                f"Set default zone: firewall-cmd --set-default-zone={self.zone}",
                "Verify: firewall-cmd --get-default-zone",
                "This change is automatically permanent",
                "List all zones: firewall-cmd --get-zones"
            ]
        else:
            self.description = (
                f"Configure firewall zone for interface:\n"
                f"  - Interface: {self.interface}\n"
                f"  - Zone: {self.zone}\n"
                f"  - Make the change permanent"
            )
            self.hints = [
                f"Add interface to zone: firewall-cmd --zone={self.zone} --change-interface={self.interface} --permanent",
                "Reload: firewall-cmd --reload",
                f"Verify: firewall-cmd --get-zone-of-interface={self.interface}",
                "Or verify: firewall-cmd --get-active-zones"
            ]

        return self

    def validate(self):
        """Validate firewall zone configuration."""
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: Firewalld running (3 points)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=True,
                points=3,
                message="firewalld is running"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=False,
                points=0,
                max_points=3,
                message="firewalld is not running"
            ))
            passed = False
            return ValidationResult(self.id, passed, total_points, self.points, checks)

        if self.set_default:
            # Check 2: Default zone set (7 points)
            result = execute_safe(['firewall-cmd', '--get-default-zone'])
            if result.success and result.stdout.strip() == self.zone:
                checks.append(ValidationCheck(
                    name="default_zone",
                    passed=True,
                    points=7,
                    message=f"Default zone is {self.zone}"
                ))
                total_points += 7
            else:
                checks.append(ValidationCheck(
                    name="default_zone",
                    passed=False,
                    points=0,
                    max_points=7,
                    message=f"Default zone is {result.stdout.strip()}, expected {self.zone}"
                ))
        else:
            # Check 2: Interface in correct zone (7 points)
            result = execute_safe(['firewall-cmd', f'--get-zone-of-interface={self.interface}'])
            if result.success and result.stdout.strip() == self.zone:
                checks.append(ValidationCheck(
                    name="interface_zone",
                    passed=True,
                    points=7,
                    message=f"Interface {self.interface} is in zone {self.zone}"
                ))
                total_points += 7
            else:
                checks.append(ValidationCheck(
                    name="interface_zone",
                    passed=False,
                    points=0,
                    max_points=7,
                    message=f"Interface not in expected zone"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class NetworkTroubleshootingTask(BaseTask):
    """Troubleshoot network connectivity issues."""

    def __init__(self):
        super().__init__(
            id="net_troubleshoot_001",
            category="networking",
            difficulty="exam",
            points=15
        )
        self.connection_name = None
        self.expected_ip = None
        self.expected_gateway = None

    def generate(self, **params):
        """Generate troubleshooting task."""
        iface = _get_practice_interface()
        self.connection_name = params.get('connection') or _get_connection_name(iface) or iface
        self.expected_ip = params.get('ip', f'192.168.100.{random.randint(10,250)}')
        self.expected_gateway = params.get('gateway', '192.168.100.1')

        self.description = (
            f"Troubleshoot and fix network connectivity:\n"
            f"  - Connection: {self.connection_name}\n"
            f"  - Required IP: {self.expected_ip}/24\n"
            f"  - Required Gateway: {self.expected_gateway}\n"
            f"  - Ensure the connection is active and working\n"
            f"  - Configuration must be persistent\n\n"
            f"  Hint: The connection may need to be created, modified, or activated"
        )

        self.hints = [
            "First diagnose: nmcli con show, nmcli device status",
            "Check current IP: ip addr show",
            "Check route: ip route show",
            f"If connection missing: nmcli con add type ethernet con-name {self.connection_name} ifname {self.connection_name}",
            f"Set IP: nmcli con mod {self.connection_name} ipv4.addresses {self.expected_ip}/24 ipv4.gateway {self.expected_gateway} ipv4.method manual",
            f"Activate: nmcli con up {self.connection_name}",
            "Verify: ping {gateway} (if reachable)"
        ]

        return self

    def validate(self):
        """Validate network troubleshooting."""
        checks = []
        total_points = 0

        # Check 1: Connection exists (3 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info:
            checks.append(ValidationCheck(
                name="connection_exists",
                passed=True,
                points=3,
                message=f"Connection '{self.connection_name}' exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="connection_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Connection '{self.connection_name}' not found"
            ))

        # Check 2: IP address configured (5 points)
        actual_ip = get_ip_address(self.connection_name)
        ip_in_config = conn_info and self.expected_ip in str(conn_info.get('ipv4.addresses', ''))

        if actual_ip == self.expected_ip:
            checks.append(ValidationCheck(
                name="ip_active",
                passed=True,
                points=5,
                message=f"IP {self.expected_ip} is active"
            ))
            total_points += 5
        elif ip_in_config:
            checks.append(ValidationCheck(
                name="ip_active",
                passed=True,
                points=3,
                message=f"IP configured but connection may not be active (partial)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="ip_active",
                passed=False,
                points=0,
                max_points=5,
                message=f"IP is {actual_ip}, expected {self.expected_ip}"
            ))

        # Check 3: Gateway configured (4 points)
        current_gw = get_default_gateway()
        gw_in_config = conn_info and self.expected_gateway in str(conn_info.get('ipv4.gateway', ''))

        if current_gw == self.expected_gateway:
            checks.append(ValidationCheck(
                name="gateway_active",
                passed=True,
                points=4,
                message=f"Gateway {self.expected_gateway} is active"
            ))
            total_points += 4
        elif gw_in_config:
            checks.append(ValidationCheck(
                name="gateway_active",
                passed=True,
                points=2,
                message=f"Gateway configured but may not be active (partial)"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="gateway_active",
                passed=False,
                points=0,
                max_points=4,
                message=f"Gateway is {current_gw}, expected {self.expected_gateway}"
            ))

        # Check 4: Interface is UP (3 points)
        state = get_interface_state(self.connection_name)
        if state == 'UP':
            checks.append(ValidationCheck(
                name="interface_up",
                passed=True,
                points=3,
                message="Interface is UP"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="interface_up",
                passed=False,
                points=0,
                max_points=3,
                message=f"Interface is {state}, expected UP"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class ConfigureNetworkTeamTask(BaseTask):
    """Configure network teaming for link aggregation."""

    def __init__(self):
        super().__init__(
            id="net_team_001",
            category="networking",
            difficulty="exam",
            points=18
        )
        self.team_name = None
        self.team_ip = None
        self.runner = None
        self.port_interfaces = None

    def generate(self, **params):
        """Generate network teaming task."""
        self.team_name = params.get('team_name', 'team0')
        self.team_ip = params.get('ip', f'10.10.10.{random.randint(10,250)}')
        runners = ['activebackup', 'roundrobin', 'loadbalance']
        self.runner = params.get('runner', random.choice(runners))

        # Get secondary interfaces for teaming (need at least 2)
        try:
            from device.network_manager import get_secondary_interfaces, get_available_interfaces
            all_ifaces = get_available_interfaces()
            secondary = get_secondary_interfaces()
            if len(secondary) >= 2:
                default_ports = secondary[:2]
            elif len(all_ifaces) >= 2:
                # Use any 2 interfaces (warn user about primary)
                default_ports = all_ifaces[:2]
            else:
                # Not enough interfaces - use placeholder names
                default_ports = ['eth1', 'eth2']
        except Exception:
            default_ports = ['eth1', 'eth2']

        self.port_interfaces = params.get('ports') or default_ports
        self._insufficient_interfaces = default_ports == ['eth1', 'eth2']

        runner_desc = {
            'activebackup': 'Active-Backup (failover)',
            'roundrobin': 'Round-Robin (load balance)',
            'loadbalance': 'Load Balance'
        }

        # Check if we have enough interfaces
        iface_warning = ""
        if self._insufficient_interfaces:
            iface_warning = (
                f"\n\n  NOTE: Your VM needs 2+ network adapters for teaming!\n"
                f"  Add adapters in VirtualBox: Settings -> Network -> Adapter 2, 3\n"
                f"  Then run: nmcli device status"
            )

        self.description = (
            f"Configure network teaming:\n"
            f"  - Team interface: {self.team_name}\n"
            f"  - Team IP: {self.team_ip}/24\n"
            f"  - Runner (mode): {self.runner} - {runner_desc.get(self.runner, '')}\n"
            f"  - Port interfaces: {', '.join(self.port_interfaces)}\n"
            f"  - Configuration must be persistent"
            f"{iface_warning}"
        )

        self.hints = [
            f"Create team: nmcli con add type team con-name {self.team_name} ifname {self.team_name} team.runner {self.runner}",
            f"Add port: nmcli con add type team-slave con-name {self.team_name}-port1 ifname {self.port_interfaces[0]} master {self.team_name}",
            f"Add port: nmcli con add type team-slave con-name {self.team_name}-port2 ifname {self.port_interfaces[1]} master {self.team_name}",
            f"Set IP: nmcli con mod {self.team_name} ipv4.addresses {self.team_ip}/24 ipv4.method manual",
            f"Activate: nmcli con up {self.team_name}",
            f"Verify: teamdctl {self.team_name} state",
            "Team runners: activebackup, roundrobin, loadbalance, broadcast, lacp"
        ]

        return self

    def validate(self):
        """Validate network teaming configuration."""
        checks = []
        total_points = 0
        from validators.safe_executor import execute_safe

        # Check 1: Team connection exists (4 points)
        conn_info = get_nmcli_connection_info(self.team_name)
        if conn_info:
            checks.append(ValidationCheck(
                name="team_exists",
                passed=True,
                points=4,
                message=f"Team connection '{self.team_name}' exists"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="team_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Team connection '{self.team_name}' not found"
            ))
            passed = False
            return ValidationResult(self.id, passed, total_points, self.points, checks)

        # Check 2: Team interface exists (3 points)
        result = execute_safe(['ip', 'link', 'show', self.team_name])
        if result.success and self.team_name in result.stdout:
            checks.append(ValidationCheck(
                name="team_interface",
                passed=True,
                points=3,
                message=f"Team interface {self.team_name} exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="team_interface",
                passed=False,
                points=0,
                max_points=3,
                message=f"Team interface not found"
            ))

        # Check 3: IP configured (4 points)
        if self.team_ip in str(conn_info.get('ipv4.addresses', '')):
            checks.append(ValidationCheck(
                name="team_ip",
                passed=True,
                points=4,
                message=f"Team IP {self.team_ip} configured"
            ))
            total_points += 4
        else:
            actual_ip = get_ip_address(self.team_name)
            if actual_ip == self.team_ip:
                checks.append(ValidationCheck(
                    name="team_ip",
                    passed=True,
                    points=4,
                    message=f"Team IP {self.team_ip} active"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="team_ip",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Team IP not configured correctly"
                ))

        # Check 4: Runner mode (3 points)
        result = execute_safe(['nmcli', '-g', 'team.runner', 'con', 'show', self.team_name])
        if result.success and self.runner in result.stdout:
            checks.append(ValidationCheck(
                name="team_runner",
                passed=True,
                points=3,
                message=f"Team runner is {self.runner}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="team_runner",
                passed=False,
                points=0,
                max_points=3,
                message=f"Team runner not set to {self.runner}"
            ))

        # Check 5: At least one port configured (4 points)
        # Method 1: Use teamdctl to check team state (most reliable)
        ports_found = []
        team_state = execute_safe(['teamdctl', self.team_name, 'state'])
        if team_state.success:
            # teamdctl output shows ports - parse for interface names
            for port in self.port_interfaces:
                if port in team_state.stdout:
                    ports_found.append(port)
            # Also check for generic port detection in output
            if not ports_found and 'link watches:' in team_state.stdout.lower():
                # If we see link watches, there's at least one port
                ports_found.append('detected')

        # Method 2: Check all connections for slave-type = team
        if not ports_found:
            result = execute_safe(['nmcli', '-t', '-f', 'NAME', 'con', 'show'])
            if result.success:
                for line in result.stdout.splitlines():
                    conn_name = line.strip()
                    if not conn_name:
                        continue
                    # Check if this connection is a team slave
                    slave_type = execute_safe(['nmcli', '-g', 'connection.slave-type', 'con', 'show', conn_name])
                    if slave_type.success and slave_type.stdout.strip() == 'team':
                        # Verify it belongs to our team
                        master = execute_safe(['nmcli', '-g', 'connection.master', 'con', 'show', conn_name])
                        if master.success:
                            master_val = master.stdout.strip()
                            # Master can be team name, interface name, or UUID
                            if master_val == self.team_name or self.team_name in master_val:
                                ports_found.append(conn_name)

        # Method 3: Check for connections with team name prefix (common naming pattern)
        if not ports_found:
            result = execute_safe(['nmcli', '-t', '-f', 'NAME', 'con', 'show'])
            if result.success:
                for line in result.stdout.splitlines():
                    conn_name = line.strip()
                    # Look for port naming patterns like "team0-port1", "team0-slave1", etc.
                    if conn_name.startswith(f'{self.team_name}-') or conn_name.startswith(f'{self.team_name}_'):
                        if 'port' in conn_name.lower() or 'slave' in conn_name.lower():
                            ports_found.append(conn_name)

        port_found = len(ports_found) > 0

        if port_found:
            checks.append(ValidationCheck(
                name="team_ports",
                passed=True,
                points=4,
                message=f"Team ports configured: {', '.join(ports_found[:2])}"
            ))
            total_points += 4
        else:
            # Provide helpful debug info
            debug_info = ""
            if team_state.success:
                debug_info = " (teamdctl worked but no ports detected)"
            else:
                debug_info = " (teamdctl failed - team may not be active)"
            checks.append(ValidationCheck(
                name="team_ports",
                passed=False,
                points=0,
                max_points=4,
                message=f"No team slave ports found for {self.team_name}{debug_info}. "
                        f"Create with: nmcli con add type team-slave con-name {self.team_name}-port1 ifname <interface> master {self.team_name}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("networking")
class SwitchToStaticIPTask(BaseTask):
    """Switch connection from DHCP to static IP."""

    def __init__(self):
        super().__init__(
            id="net_dhcp_static_001",
            category="networking",
            difficulty="easy",
            points=8
        )
        self.connection_name = None
        self.ip_address = None

    def generate(self, **params):
        """Generate DHCP to static task."""
        iface = _get_practice_interface()
        self.connection_name = params.get('connection') or _get_connection_name(iface) or iface
        self.ip_address = params.get('ip', f'172.16.{random.randint(1,254)}.{random.randint(10,250)}')

        self.description = (
            f"Switch connection from DHCP to static IP:\n"
            f"  - Connection: {self.connection_name}\n"
            f"  - Static IP: {self.ip_address}/24\n"
            f"  - Change IPv4 method from 'auto' to 'manual'\n"
            f"  - Activate the change"
        )

        self.hints = [
            "Current method: nmcli -f ipv4.method con show {connection}",
            f"Set IP: nmcli con mod {self.connection_name} ipv4.addresses {self.ip_address}/24",
            f"Change method: nmcli con mod {self.connection_name} ipv4.method manual",
            f"Activate: nmcli con up {self.connection_name}",
            "DHCP = auto, Static = manual"
        ]

        return self

    def validate(self):
        """Validate DHCP to static switch."""
        checks = []
        total_points = 0

        # Check 1: Method is manual (4 points)
        conn_info = get_nmcli_connection_info(self.connection_name)
        if conn_info and conn_info.get('ipv4.method') == 'manual':
            checks.append(ValidationCheck(
                name="method_manual",
                passed=True,
                points=4,
                message="IPv4 method is 'manual' (static)"
            ))
            total_points += 4
        else:
            method = conn_info.get('ipv4.method', 'unknown') if conn_info else 'unknown'
            checks.append(ValidationCheck(
                name="method_manual",
                passed=False,
                points=0,
                max_points=4,
                message=f"IPv4 method is '{method}', expected 'manual'"
            ))

        # Check 2: IP configured (4 points)
        actual_ip = get_ip_address(self.connection_name)
        if actual_ip == self.ip_address:
            checks.append(ValidationCheck(
                name="ip_set",
                passed=True,
                points=4,
                message=f"Static IP {self.ip_address} is active"
            ))
            total_points += 4
        elif conn_info and self.ip_address in str(conn_info.get('ipv4.addresses', '')):
            checks.append(ValidationCheck(
                name="ip_set",
                passed=True,
                points=3,
                message=f"IP configured, connection may need activation (partial)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="ip_set",
                passed=False,
                points=0,
                max_points=4,
                message=f"IP is {actual_ip}, expected {self.ip_address}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
