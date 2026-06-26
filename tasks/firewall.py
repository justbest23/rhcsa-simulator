"""
Firewall management tasks for RHCSA EX200 v10 exam.
Covers enabling firewalld, managing services/ports/zones, rich rules,
port forwarding, reloading, troubleshooting, and full setup scenarios.
"""

import os
import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared pools for randomisation
# ---------------------------------------------------------------------------
_FIREWALL_SERVICES = ['http', 'https', 'nfs', 'samba', 'mysql', 'dns', 'smtp']

_FIREWALL_ZONES = ['public', 'internal', 'dmz', 'trusted', 'work', 'home', 'external']

_FIREWALL_PORTS = [
    ('8080', 'tcp'),
    ('3306', 'tcp'),
    ('5432', 'tcp'),
    ('8443', 'tcp'),
    ('9090', 'tcp'),
    ('6379', 'tcp'),
    ('27017', 'tcp'),
    ('1514', 'udp'),
]

_DEFAULT_ZONE_CHOICES = ['internal', 'dmz', 'trusted', 'work', 'home']

_RICH_RULE_TEMPLATES = [
    {
        'source': '192.168.1.0/24',
        'service': 'http',
        'action': 'accept',
        'family': 'ipv4',
    },
    {
        'source': '10.0.0.0/8',
        'service': 'ssh',
        'action': 'accept',
        'family': 'ipv4',
    },
    {
        'source': '172.16.0.0/16',
        'service': 'https',
        'action': 'accept',
        'family': 'ipv4',
    },
    {
        'source': '192.168.100.0/24',
        'service': 'dns',
        'action': 'accept',
        'family': 'ipv4',
    },
    {
        'source': '10.10.0.0/16',
        'service': 'nfs',
        'action': 'reject',
        'family': 'ipv4',
    },
]

_PORT_FORWARD_CONFIGS = [
    {'from_port': '80', 'proto': 'tcp', 'to_port': '8080'},
    {'from_port': '443', 'proto': 'tcp', 'to_port': '8443'},
    {'from_port': '8080', 'proto': 'tcp', 'to_port': '80'},
    {'from_port': '2222', 'proto': 'tcp', 'to_port': '22'},
    {'from_port': '3000', 'proto': 'tcp', 'to_port': '8080'},
]


# ===== 1. EnableFirewallTask (easy / 5pts) [PERSIST] =======================

@TaskRegistry.register("firewall")
class EnableFirewallTask(BaseTask):
    """Fault-injection: firewalld is stopped and disabled; user must re-enable it."""

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="fw_enable_001",
            category="firewall",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'enable', 'persistence', 'fault-injection']
        self.exam_tips = [
            "Use 'systemctl enable --now firewalld' to enable and start in one command.",
            "Verify with 'firewall-cmd --state' which should return 'running'.",
            "If firewalld is masked, unmask it first: 'systemctl unmask firewalld'.",
        ]
        # firewalld ships active+enabled on RHEL, so without breaking it first
        # this task would pass without the candidate doing anything.
        self.has_fault_injection = True
        self._fault_info = None

    def inject_fault(self):
        from tasks.troubleshooting import save_fault_state, _run
        act = _run(['systemctl', 'is-active', 'firewalld'])
        was_active = act.stdout.strip() == 'active'
        en = _run(['systemctl', 'is-enabled', 'firewalld'])
        was_enabled = 'enabled' in (en.stdout or '')
        _run(['systemctl', 'stop', 'firewalld'])
        _run(['systemctl', 'disable', 'firewalld'])
        self._fault_info = {
            'service': 'firewalld',
            'was_active': was_active,
            'was_enabled': was_enabled,
        }
        save_fault_state(self.id, self._fault_info)
        return True, "Stopped and disabled firewalld"

    def restore_fault(self):
        from tasks.troubleshooting import _restore_service, clear_fault_state
        msgs = []
        _restore_service(self._fault_info or {'service': 'firewalld'}, msgs)
        clear_fault_state()
        return True, '; '.join(msgs)

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: firewalld Is Stopped and Disabled\n"
            "Symptom: The system firewall is not running and will not start at boot.\n\n"
            "Tasks:\n"
            "  1. Start the firewalld service\n"
            "  2. Enable it to start automatically at boot\n"
            "  3. Verify with: firewall-cmd --state"
        )
        self.hints = [
            "systemctl enable --now firewalld",
            "firewall-cmd --state  (should return 'running')",
            "systemctl is-enabled firewalld  (should return 'enabled')",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        _sp.run(['systemctl', 'stop', 'firewalld'], capture_output=True)
        _sp.run(['systemctl', 'disable', 'firewalld'], capture_output=True)
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'service': 'firewalld'})
        return True, "Stopped and disabled firewalld"

    def restore_fault(self):
        import subprocess as _sp
        _sp.run(['systemctl', 'enable', '--now', 'firewalld'], capture_output=True)
        from tasks.troubleshooting import clear_fault_state
        clear_fault_state()
        return True, "Re-enabled and started firewalld"

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: firewalld is active (3 pts)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_active",
                passed=True,
                points=3,
                message="firewalld is running",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="firewalld_active",
                passed=False,
                points=0,
                max_points=3,
                message=f"firewalld is not running (got: {result.stdout.strip()})",
            ))

        # Check 2: firewalld is enabled (2 pts)
        result = execute_safe(['systemctl', 'is-enabled', 'firewalld'])
        if result.success and result.stdout.strip() == 'enabled':
            checks.append(ValidationCheck(
                name="firewalld_enabled",
                passed=True,
                points=2,
                message="firewalld is enabled at boot",
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="firewalld_enabled",
                passed=False,
                points=0,
                max_points=2,
                message=f"firewalld is not enabled (got: {result.stdout.strip()})",
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 2. AddServiceToFirewallTask (exam / 10pts) [PERSIST] ================

@TaskRegistry.register("firewall")
class AddServiceToFirewallTask(BaseTask):
    """Add a service to a firewall zone permanently."""

    def __init__(self):
        super().__init__(
            id="fw_add_service_001",
            category="firewall",
            difficulty="exam",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'service', 'zone', 'exam-core', 'persistence']
        self.exam_tips = [
            "Always use --permanent so the rule survives reboot.",
            "After --permanent changes, run 'firewall-cmd --reload' to apply immediately.",
            "Or add the rule twice: once with --permanent, once without (for immediate effect).",
        ]
        self.service_name = None
        self.zone = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(_FIREWALL_SERVICES))
        self.zone = params.get('zone', random.choice(['public', 'internal', 'work', 'home']))

        self.description = (
            f"Add the '{self.service_name}' service to the firewall:\n"
            f"  - Zone: {self.zone}\n"
            f"  - The rule must be permanent (survive reboot)\n"
            f"  - Reload the firewall to apply immediately\n"
            f"  - Verify the service is listed in the zone"
        )

        self.hints = [
            f"firewall-cmd --permanent --zone={self.zone} --add-service={self.service_name}",
            "firewall-cmd --reload",
            f"firewall-cmd --zone={self.zone} --list-services",
            f"firewall-cmd --permanent --zone={self.zone} --query-service={self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is in the permanent config (6 pts)
        result = execute_safe([
            'firewall-cmd', '--permanent',
            f'--zone={self.zone}',
            f'--query-service={self.service_name}',
        ])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="service_permanent",
                passed=True,
                points=6,
                message=f"Service '{self.service_name}' is in permanent config for zone '{self.zone}'",
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="service_permanent",
                passed=False,
                points=0,
                max_points=6,
                message=f"Service '{self.service_name}' not found in permanent config for zone '{self.zone}'",
            ))

        # Check 2: service is in the runtime config (4 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            f'--query-service={self.service_name}',
        ])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="service_runtime",
                passed=True,
                points=4,
                message=f"Service '{self.service_name}' is active in runtime config (reload done)",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="service_runtime",
                passed=False,
                points=0,
                max_points=4,
                message=f"Service '{self.service_name}' not in runtime config -- did you reload?",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 3. AddPortToFirewallTask (exam / 10pts) [PERSIST] ===================

@TaskRegistry.register("firewall")
class AddPortToFirewallTask(BaseTask):
    """Add a port/protocol to a firewall zone permanently."""

    def __init__(self):
        super().__init__(
            id="fw_add_port_001",
            category="firewall",
            difficulty="exam",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'port', 'exam-core', 'persistence']
        self.exam_tips = [
            "Syntax: firewall-cmd --permanent --add-port=<port>/<protocol>",
            "Remember to reload after permanent changes.",
            "Common protocols: tcp, udp.",
        ]
        self.port = None
        self.protocol = None
        self.zone = None

    def generate(self, **params):
        port_info = params.get('port_info', random.choice(_FIREWALL_PORTS))
        self.port = port_info[0]
        self.protocol = port_info[1]
        self.zone = params.get('zone', 'public')

        port_proto = f'{self.port}/{self.protocol}'

        self.description = (
            f"Open port {port_proto} in the firewall:\n"
            f"  - Zone: {self.zone}\n"
            f"  - Port: {self.port}\n"
            f"  - Protocol: {self.protocol}\n"
            f"  - The rule must be permanent\n"
            f"  - Reload the firewall to apply immediately"
        )

        self.hints = [
            f"firewall-cmd --permanent --zone={self.zone} --add-port={port_proto}",
            "firewall-cmd --reload",
            f"firewall-cmd --permanent --zone={self.zone} --query-port={port_proto}",
            f"firewall-cmd --zone={self.zone} --list-ports",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        port_proto = f'{self.port}/{self.protocol}'

        # Check 1: port in permanent config (6 pts)
        result = execute_safe([
            'firewall-cmd', '--permanent',
            f'--zone={self.zone}',
            f'--query-port={port_proto}',
        ])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="port_permanent",
                passed=True,
                points=6,
                message=f"Port {port_proto} is in permanent config for zone '{self.zone}'",
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="port_permanent",
                passed=False,
                points=0,
                max_points=6,
                message=f"Port {port_proto} not found in permanent config for zone '{self.zone}'",
            ))

        # Check 2: port in runtime config (4 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            f'--query-port={port_proto}',
        ])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="port_runtime",
                passed=True,
                points=4,
                message=f"Port {port_proto} is active in runtime config",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="port_runtime",
                passed=False,
                points=0,
                max_points=4,
                message=f"Port {port_proto} not in runtime config -- did you reload?",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 4. RemoveServiceFromFirewallTask (medium / 8pts) [PERSIST] ==========

@TaskRegistry.register("firewall")
class RemoveServiceFromFirewallTask(BaseTask):
    """Remove a service from a firewall zone permanently."""

    def __init__(self):
        super().__init__(
            id="fw_remove_service_001",
            category="firewall",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'remove', 'service', 'persistence']
        self.exam_tips = [
            "Use --remove-service with --permanent to remove permanently.",
            "Reload afterwards to apply the change to the running config.",
            "Verify with --query-service (should return 'no').",
        ]
        self.service_name = None
        self.zone = None

    def generate(self, **params):
        # Pick a service that is commonly in default zones
        removable_services = ['cockpit', 'dhcpv6-client', 'mdns', 'samba-client']
        self.service_name = params.get('service', random.choice(removable_services))
        self.zone = params.get('zone', 'public')

        self.description = (
            f"Remove the '{self.service_name}' service from the firewall:\n"
            f"  - Zone: {self.zone}\n"
            f"  - The removal must be permanent\n"
            f"  - Reload the firewall to apply immediately\n"
            f"  - Verify the service is no longer listed"
        )

        self.hints = [
            f"firewall-cmd --permanent --zone={self.zone} --remove-service={self.service_name}",
            "firewall-cmd --reload",
            f"firewall-cmd --permanent --zone={self.zone} --query-service={self.service_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: service is NOT in permanent config (5 pts)
        result = execute_safe([
            'firewall-cmd', '--permanent',
            f'--zone={self.zone}',
            f'--query-service={self.service_name}',
        ])
        # query-service returns exit code 1 and "no" if not present
        service_absent = (not result.success) or ('no' in result.stdout.lower())
        if service_absent:
            checks.append(ValidationCheck(
                name="service_removed_permanent",
                passed=True,
                points=5,
                message=f"Service '{self.service_name}' removed from permanent config in zone '{self.zone}'",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="service_removed_permanent",
                passed=False,
                points=0,
                max_points=5,
                message=f"Service '{self.service_name}' still in permanent config for zone '{self.zone}'",
            ))

        # Check 2: service is NOT in runtime config (3 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            f'--query-service={self.service_name}',
        ])
        service_absent_rt = (not result.success) or ('no' in result.stdout.lower())
        if service_absent_rt:
            checks.append(ValidationCheck(
                name="service_removed_runtime",
                passed=True,
                points=3,
                message=f"Service '{self.service_name}' removed from runtime config (reload done)",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="service_removed_runtime",
                passed=False,
                points=0,
                max_points=3,
                message=f"Service '{self.service_name}' still in runtime config -- did you reload?",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 5. SetDefaultZoneTask (medium / 8pts) [PERSIST] =====================

@TaskRegistry.register("firewall")
class SetDefaultZoneTask(BaseTask):
    """Set the default firewall zone."""

    def __init__(self):
        super().__init__(
            id="fw_default_zone_001",
            category="firewall",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'zone', 'default', 'persistence']
        self.exam_tips = [
            "'firewall-cmd --set-default-zone=<zone>' changes the default immediately AND permanently.",
            "No --reload needed -- this takes effect right away.",
            "Verify with 'firewall-cmd --get-default-zone'.",
        ]
        self.zone = None

    def generate(self, **params):
        self.zone = params.get('zone', random.choice(_DEFAULT_ZONE_CHOICES))

        self.description = (
            f"Set the default firewall zone to '{self.zone}':\n"
            f"  - Change the default zone from the current setting to '{self.zone}'\n"
            f"  - This change is automatically permanent\n"
            f"  - Verify the default zone was changed"
        )

        self.hints = [
            "firewall-cmd has a --set-default-zone option",
            "Verify with: firewall-cmd --get-default-zone",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: default zone matches (8 pts)
        result = execute_safe(['firewall-cmd', '--get-default-zone'])
        if result.success and result.stdout.strip() == self.zone:
            checks.append(ValidationCheck(
                name="default_zone_set",
                passed=True,
                points=8,
                message=f"Default zone is '{self.zone}'",
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="default_zone_set",
                passed=False,
                points=0,
                max_points=8,
                message=f"Default zone is '{result.stdout.strip()}', expected '{self.zone}'",
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 6. AddRichRuleTask (hard / 15pts) [PERSIST] =========================

@TaskRegistry.register("firewall")
class AddRichRuleTask(BaseTask):
    """Add a firewalld rich rule to control access from a specific source."""

    def __init__(self):
        super().__init__(
            id="fw_rich_rule_001",
            category="firewall",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'rich-rule', 'advanced', 'persistence']
        self.exam_tips = [
            "Rich rule syntax: rule family=\"ipv4\" source address=\"x.x.x.x/y\" service name=\"svc\" accept",
            "Always use --permanent and --reload.",
            "Verify with: firewall-cmd --permanent --list-rich-rules",
            "Quoting matters -- use single quotes around the entire rule.",
        ]
        self.zone = None
        self.source = None
        self.service = None
        self.action = None
        self.family = None

    def generate(self, **params):
        template = params.get('template', random.choice(_RICH_RULE_TEMPLATES))
        self.source = template['source']
        self.service = template['service']
        self.action = template['action']
        self.family = template['family']
        self.zone = params.get('zone', 'public')

        self.rich_rule = (
            f'rule family="{self.family}" '
            f'source address="{self.source}" '
            f'service name="{self.service}" '
            f'{self.action}'
        )

        self.description = (
            f"Add a firewall rich rule:\n"
            f"  - Zone: {self.zone}\n"
            f"  - Allow/deny traffic from {self.source} to service '{self.service}'\n"
            f"  - Action: {self.action}\n"
            f"  - Family: {self.family}\n"
            f"  - Full rule: {self.rich_rule}\n"
            f"  - Must be permanent and reloaded"
        )

        self.hints = [
            f"firewall-cmd --permanent --zone={self.zone} --add-rich-rule='{self.rich_rule}'",
            "firewall-cmd --reload",
            f"firewall-cmd --permanent --zone={self.zone} --list-rich-rules",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: rich rule is in permanent config (10 pts)
        result = execute_safe([
            'firewall-cmd', '--permanent',
            f'--zone={self.zone}',
            '--list-rich-rules',
        ])
        # The rule should appear in the output
        rule_found = False
        if result.success and result.stdout.strip():
            # Check for key components of the rule in the output
            output = result.stdout.strip()
            has_source = self.source in output
            has_service = self.service in output
            has_action = self.action in output
            if has_source and has_service and has_action:
                rule_found = True

        if rule_found:
            checks.append(ValidationCheck(
                name="rich_rule_permanent",
                passed=True,
                points=10,
                message=f"Rich rule found in permanent config for zone '{self.zone}'",
            ))
            total_points += 10
        else:
            checks.append(ValidationCheck(
                name="rich_rule_permanent",
                passed=False,
                points=0,
                max_points=10,
                message=f"Rich rule not found in permanent config for zone '{self.zone}'",
                details=f"Expected rule containing: source={self.source}, service={self.service}, action={self.action}",
            ))

        # Check 2: rich rule is in runtime config (5 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            '--list-rich-rules',
        ])
        rule_found_rt = False
        if result.success and result.stdout.strip():
            output = result.stdout.strip()
            if self.source in output and self.service in output and self.action in output:
                rule_found_rt = True

        if rule_found_rt:
            checks.append(ValidationCheck(
                name="rich_rule_runtime",
                passed=True,
                points=5,
                message=f"Rich rule active in runtime config (reload done)",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="rich_rule_runtime",
                passed=False,
                points=0,
                max_points=5,
                message=f"Rich rule not in runtime config -- did you reload?",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 7. ConfigurePortForwardTask (hard / 15pts) [PERSIST] ================

@TaskRegistry.register("firewall")
class ConfigurePortForwardTask(BaseTask):
    """Configure port forwarding in firewalld."""

    def __init__(self):
        super().__init__(
            id="fw_port_forward_001",
            category="firewall",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'port-forward', 'advanced', 'persistence']
        self.exam_tips = [
            "Syntax: firewall-cmd --permanent --add-forward-port=port=<p>:proto=<proto>:toport=<tp>",
            "For forwarding to another host add :toaddr=<ip>.",
            "Always reload afterwards.",
            "Verify with: firewall-cmd --permanent --list-forward-ports",
        ]
        self.from_port = None
        self.protocol = None
        self.to_port = None
        self.zone = None

    def generate(self, **params):
        config = params.get('config', random.choice(_PORT_FORWARD_CONFIGS))
        self.from_port = config['from_port']
        self.protocol = config['proto']
        self.to_port = config['to_port']
        self.zone = params.get('zone', 'public')

        forward_spec = f'port={self.from_port}:proto={self.protocol}:toport={self.to_port}'

        self.description = (
            f"Configure port forwarding in the firewall:\n"
            f"  - Zone: {self.zone}\n"
            f"  - Forward port {self.from_port}/{self.protocol} to port {self.to_port}\n"
            f"  - The rule must be permanent\n"
            f"  - Reload the firewall to apply\n"
            f"  - Forward spec: {forward_spec}"
        )

        self.hints = [
            f"firewall-cmd --permanent --zone={self.zone} --add-forward-port={forward_spec}",
            "firewall-cmd --reload",
            f"firewall-cmd --permanent --zone={self.zone} --list-forward-ports",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        forward_spec = f'port={self.from_port}:proto={self.protocol}:toport={self.to_port}'

        # Check 1: forward rule in permanent config (10 pts)
        result = execute_safe([
            'firewall-cmd', '--permanent',
            f'--zone={self.zone}',
            '--list-forward-ports',
        ])
        fwd_found = False
        if result.success and result.stdout.strip():
            output = result.stdout.strip()
            # firewall-cmd outputs forward rules in the format:
            # port=80:proto=tcp:toport=8080:toaddr=
            if (f'port={self.from_port}' in output and
                    f'toport={self.to_port}' in output and
                    f'proto={self.protocol}' in output):
                fwd_found = True

        if fwd_found:
            checks.append(ValidationCheck(
                name="forward_permanent",
                passed=True,
                points=10,
                message=f"Port forward {self.from_port}->{self.to_port}/{self.protocol} in permanent config",
            ))
            total_points += 10
        else:
            checks.append(ValidationCheck(
                name="forward_permanent",
                passed=False,
                points=0,
                max_points=10,
                message=f"Port forward not found in permanent config (expected: {forward_spec})",
            ))

        # Check 2: forward rule in runtime config (5 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            '--list-forward-ports',
        ])
        fwd_found_rt = False
        if result.success and result.stdout.strip():
            output = result.stdout.strip()
            if (f'port={self.from_port}' in output and
                    f'toport={self.to_port}' in output and
                    f'proto={self.protocol}' in output):
                fwd_found_rt = True

        if fwd_found_rt:
            checks.append(ValidationCheck(
                name="forward_runtime",
                passed=True,
                points=5,
                message=f"Port forward active in runtime config (reload done)",
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="forward_runtime",
                passed=False,
                points=0,
                max_points=5,
                message=f"Port forward not in runtime config -- did you reload?",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 8. FirewallReloadTask (easy / 5pts) ==================================

@TaskRegistry.register("firewall")
class FirewallReloadTask(BaseTask):
    """
    Fault-injection: adds 'tftp' to the permanent firewall config but NOT
    the runtime, simulating a sysadmin who ran --permanent but forgot --reload.
    The user must run firewall-cmd --reload to apply it.
    """

    has_fault_injection = True
    _INJECT_SERVICE = 'tftp'

    def __init__(self):
        super().__init__(
            id="fw_reload_001",
            category="firewall",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = False
        self.tags = ['firewalld', 'reload', 'fault-injection']
        self.exam_tips = [
            "'firewall-cmd --reload' applies permanent rules to the running config instantly.",
            "Without --reload, --permanent changes only take effect after the next reboot.",
            "Always reload after making permanent changes so they are immediately active.",
        ]

    def generate(self, **params):
        self.description = (
            "TROUBLESHOOTING: Permanent Firewall Rule Not Active\n"
            f"Symptom: The '{self._INJECT_SERVICE}' service was added to the permanent\n"
            "firewall config, but it is NOT in the active runtime rules yet.\n"
            "A reload was never run.\n\n"
            "Tasks:\n"
            "  1. Confirm the discrepancy between permanent and runtime rules\n"
            "  2. Reload the firewall to apply all pending permanent rules\n"
            "  3. Verify the service is now active in the runtime config"
        )
        self.hints = [
            "Compare: firewall-cmd --list-services  vs  firewall-cmd --permanent --list-services",
            "Apply permanent rules to runtime: firewall-cmd --reload",
            f"Verify: firewall-cmd --query-service={self._INJECT_SERVICE}",
        ]
        return self

    def inject_fault(self):
        import subprocess as _sp
        svc = self._INJECT_SERVICE
        # Ensure it's NOT in the runtime (remove if somehow already there)
        _sp.run(['firewall-cmd', '--remove-service', svc], capture_output=True)
        # Add only to permanent config — the "forgot to reload" scenario
        _sp.run(['firewall-cmd', '--permanent', '--add-service', svc], capture_output=True)
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'service': svc})
        return True, f"Added {svc} to permanent config only (runtime not updated)"

    def restore_fault(self):
        import subprocess as _sp
        svc = self._INJECT_SERVICE
        _sp.run(['firewall-cmd', '--permanent', '--remove-service', svc], capture_output=True)
        _sp.run(['firewall-cmd', '--remove-service', svc], capture_output=True)
        from tasks.troubleshooting import clear_fault_state
        clear_fault_state()
        return True, f"Removed {svc} from permanent and runtime firewall"

    def validate(self):
        checks = []
        score = 0
        svc = self._INJECT_SERVICE

        # Check 1: service active in runtime (3 pts)
        r = execute_safe(['firewall-cmd', '--query-service', svc])
        if r.success and r.stdout.strip() == 'yes':
            checks.append(ValidationCheck("service_in_runtime", True, 3,
                message=f"'{svc}' is active in the runtime firewall (reload was run)"))
            score += 3
        else:
            checks.append(ValidationCheck("service_in_runtime", False, 0, max_points=3,
                message=f"'{svc}' still not in runtime — run: firewall-cmd --reload"))

        # Check 2: firewall still running (2 pts)
        r = execute_safe(['firewall-cmd', '--state'])
        if r.success and 'running' in r.stdout:
            checks.append(ValidationCheck("firewall_running", True, 2,
                message="firewalld is running"))
            score += 2
        else:
            checks.append(ValidationCheck("firewall_running", False, 0, max_points=2,
                message="firewalld is not running"))

        return ValidationResult(self.id, score >= self.points * 0.6, score, self.points, checks)


# ===== 9. TroubleshootFirewallTask (hard / 18pts) ==========================

@TaskRegistry.register("firewall")
class TroubleshootFirewallTask(BaseTask):
    """Diagnose why a service is not accessible through the firewall."""

    def __init__(self):
        super().__init__(
            id="fw_troubleshoot_001",
            category="firewall",
            difficulty="hard",
            points=18,
        )
        self.requires_persistence = False
        self.tags = ['firewalld', 'troubleshooting', 'diagnostics']
        self.exam_tips = [
            "Check: Is firewalld running?  Is the service/port in the correct zone?",
            "Check: Is the interface assigned to the expected zone?",
            "Use 'firewall-cmd --get-active-zones' to see zone-interface mappings.",
            "Use 'firewall-cmd --zone=<zone> --list-all' for a full zone dump.",
        ]
        self.service_name = None
        self.zone = None
        self.port = None
        self.protocol = None
        self.scenario = None

    def generate(self, **params):
        self.service_name = params.get('service', random.choice(['http', 'https', 'ssh', 'nfs']))
        self.zone = params.get('zone', random.choice(['public', 'internal', 'work']))

        port_map = {
            'http': ('80', 'tcp'),
            'https': ('443', 'tcp'),
            'ssh': ('22', 'tcp'),
            'nfs': ('2049', 'tcp'),
        }
        self.port, self.protocol = port_map.get(self.service_name, ('80', 'tcp'))

        scenarios = [
            {
                'id': 'service_not_added',
                'desc': f"the '{self.service_name}' service is not added to zone '{self.zone}'",
                'hint': f"firewall-cmd --permanent --zone={self.zone} --add-service={self.service_name}",
            },
            {
                'id': 'wrong_zone',
                'desc': "the service is added to a different zone than the active one",
                'hint': "Check firewall-cmd --get-active-zones and ensure service is in the right zone",
            },
            {
                'id': 'not_reloaded',
                'desc': "permanent rules have not been reloaded to the running config",
                'hint': "Run firewall-cmd --reload to apply permanent rules",
            },
            {
                'id': 'firewalld_stopped',
                'desc': "firewalld is not running",
                'hint': "systemctl start firewalld",
            },
        ]

        self.scenario = params.get('scenario', random.choice(scenarios))

        self.description = (
            f"A client cannot reach the '{self.service_name}' service (port {self.port}/{self.protocol}).\n"
            f"  - Likely cause: {self.scenario['desc']}\n"
            f"  - Diagnose and fix the firewall so the service is accessible\n"
            f"  - Ensure the service is in zone '{self.zone}'\n"
            f"  - Ensure the port is open\n"
            f"  - Firewalld must be running"
        )

        self.hints = [
            "firewall-cmd --state",
            f"firewall-cmd --zone={self.zone} --list-all",
            "firewall-cmd --get-active-zones",
            self.scenario['hint'],
            "firewall-cmd --reload",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: firewalld is running (4 pts)
        result = execute_safe(['systemctl', 'is-active', 'firewalld'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=True,
                points=4,
                message="firewalld is running",
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="firewalld_running",
                passed=False,
                points=0,
                max_points=4,
                message="firewalld is not running",
            ))

        # Check 2: service is in the correct zone (7 pts)
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            f'--query-service={self.service_name}',
        ])
        if result.success and 'yes' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="service_in_zone",
                passed=True,
                points=7,
                message=f"Service '{self.service_name}' is in zone '{self.zone}'",
            ))
            total_points += 7
        else:
            checks.append(ValidationCheck(
                name="service_in_zone",
                passed=False,
                points=0,
                max_points=7,
                message=f"Service '{self.service_name}' is NOT in zone '{self.zone}'",
            ))

        # Check 3: port is open (7 pts)
        port_proto = f'{self.port}/{self.protocol}'
        result = execute_safe([
            'firewall-cmd',
            f'--zone={self.zone}',
            f'--query-port={port_proto}',
        ])
        # Port may be implicitly open via the service, so check both
        port_open = result.success and 'yes' in result.stdout.lower()

        # If the service is added, the port is implicitly open even if
        # --query-port returns no.  Give credit if service check passed.
        service_passed = any(
            c.name == 'service_in_zone' and c.passed for c in checks
        )

        if port_open or service_passed:
            checks.append(ValidationCheck(
                name="port_accessible",
                passed=True,
                points=7,
                message=f"Port {port_proto} is accessible (via service or explicit port rule)",
            ))
            total_points += 7
        else:
            checks.append(ValidationCheck(
                name="port_accessible",
                passed=False,
                points=0,
                max_points=7,
                message=f"Port {port_proto} is not accessible in zone '{self.zone}'",
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


# ===== 10. FullFirewallSetupTask (exam / 20pts) [PERSIST] ==================

@TaskRegistry.register("firewall")
class FullFirewallSetupTask(BaseTask):
    """Complete firewall setup: enable, set zone, add services and ports, reload."""

    def __init__(self):
        super().__init__(
            id="fw_full_setup_001",
            category="firewall",
            difficulty="exam",
            points=20,
        )
        self.requires_persistence = True
        self.tags = ['firewalld', 'full-setup', 'exam-core', 'persistence']
        self.exam_tips = [
            "Order: 1) enable firewalld  2) set default zone  3) add services  4) add ports  5) reload.",
            "Everything must be --permanent to survive the reboot the exam will perform.",
            "Verify each step individually before moving on.",
        ]
        self.zone = None
        self.services = None
        self.ports = None

    def generate(self, **params):
        self.zone = params.get('zone', random.choice(_DEFAULT_ZONE_CHOICES))

        # Pick 2-3 random services
        num_services = random.randint(2, 3)
        self.services = params.get(
            'services',
            random.sample(_FIREWALL_SERVICES, num_services),
        )

        # Pick 1-2 random ports
        num_ports = random.randint(1, 2)
        self.ports = params.get(
            'ports',
            random.sample(_FIREWALL_PORTS, num_ports),
        )

        ports_display = ', '.join(f'{p[0]}/{p[1]}' for p in self.ports)
        services_display = ', '.join(self.services)

        self.description = (
            f"Perform a complete firewall configuration:\n"
            f"  1. Enable and start firewalld\n"
            f"  2. Set the default zone to '{self.zone}'\n"
            f"  3. Add services: {services_display}\n"
            f"  4. Open ports: {ports_display}\n"
            f"  5. Reload the firewall\n"
            f"  - All changes must be permanent (survive reboot)"
        )

        self.hints = [
            "systemctl enable --now firewalld",
            f"firewall-cmd --set-default-zone={self.zone}",
        ]
        for svc in self.services:
            self.hints.append(
                f"firewall-cmd --permanent --zone={self.zone} --add-service={svc}"
            )
        for port, proto in self.ports:
            self.hints.append(
                f"firewall-cmd --permanent --zone={self.zone} --add-port={port}/{proto}"
            )
        self.hints.append("firewall-cmd --reload")
        self.hints.append(f"firewall-cmd --zone={self.zone} --list-all")

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: firewalld is running and enabled (4 pts)
        result_active = execute_safe(['systemctl', 'is-active', 'firewalld'])
        result_enabled = execute_safe(['systemctl', 'is-enabled', 'firewalld'])
        fw_running = result_active.success and result_active.stdout.strip() == 'active'
        fw_enabled = result_enabled.success and result_enabled.stdout.strip() == 'enabled'

        if fw_running and fw_enabled:
            checks.append(ValidationCheck(
                name="firewalld_running_enabled",
                passed=True,
                points=4,
                message="firewalld is running and enabled",
            ))
            total_points += 4
        else:
            msg_parts = []
            if not fw_running:
                msg_parts.append("not running")
            if not fw_enabled:
                msg_parts.append("not enabled")
            checks.append(ValidationCheck(
                name="firewalld_running_enabled",
                passed=False,
                points=0,
                max_points=4,
                message=f"firewalld is {', '.join(msg_parts)}",
            ))

        # Check 2: default zone is correct (3 pts)
        result = execute_safe(['firewall-cmd', '--get-default-zone'])
        if result.success and result.stdout.strip() == self.zone:
            checks.append(ValidationCheck(
                name="default_zone",
                passed=True,
                points=3,
                message=f"Default zone is '{self.zone}'",
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="default_zone",
                passed=False,
                points=0,
                max_points=3,
                message=f"Default zone is '{result.stdout.strip()}', expected '{self.zone}'",
            ))

        # Check 3: each service is present (points split among services)
        svc_points_each = 3 if len(self.services) <= 2 else 2
        for svc in self.services:
            result = execute_safe([
                'firewall-cmd', '--permanent',
                f'--zone={self.zone}',
                f'--query-service={svc}',
            ])
            if result.success and 'yes' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name=f"service_{svc}",
                    passed=True,
                    points=svc_points_each,
                    message=f"Service '{svc}' is in zone '{self.zone}' (permanent)",
                ))
                total_points += svc_points_each
            else:
                checks.append(ValidationCheck(
                    name=f"service_{svc}",
                    passed=False,
                    points=0,
                    max_points=svc_points_each,
                    message=f"Service '{svc}' not found in zone '{self.zone}' (permanent)",
                ))

        # Check 4: each port is present (points split among ports)
        port_points_each = 3 if len(self.ports) <= 1 else 2
        for port, proto in self.ports:
            port_proto = f'{port}/{proto}'
            result = execute_safe([
                'firewall-cmd', '--permanent',
                f'--zone={self.zone}',
                f'--query-port={port_proto}',
            ])
            if result.success and 'yes' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name=f"port_{port}_{proto}",
                    passed=True,
                    points=port_points_each,
                    message=f"Port {port_proto} is open in zone '{self.zone}' (permanent)",
                ))
                total_points += port_points_each
            else:
                checks.append(ValidationCheck(
                    name=f"port_{port}_{proto}",
                    passed=False,
                    points=0,
                    max_points=port_points_each,
                    message=f"Port {port_proto} not open in zone '{self.zone}' (permanent)",
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
