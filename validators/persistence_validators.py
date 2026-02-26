"""
Dedicated persistence validators for RHCSA Simulator v4.0.0
These check that configurations survive a reboot.
"""

import logging
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


def check_fstab_entry(uuid=None, mountpoint=None, device=None):
    """Check that an fstab entry exists for the given UUID or mountpoint."""
    result = execute_safe(['cat', '/etc/fstab'])
    if not result.success:
        return False

    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue

        if uuid and f"UUID={uuid}" in parts[0]:
            if mountpoint is None or parts[1] == mountpoint:
                return True
        if device and parts[0] == device:
            if mountpoint is None or parts[1] == mountpoint:
                return True
        if mountpoint and parts[1] == mountpoint:
            return True

    return False


def check_service_enabled(service_name):
    """Check that a systemd service is enabled."""
    result = execute_safe(['systemctl', 'is-enabled', service_name])
    if result.success and result.stdout.strip() == 'enabled':
        return True
    return False


def check_firewall_permanent_rule(rule_type, rule_value, zone='public'):
    """
    Check that a firewall rule is permanent.

    Args:
        rule_type: 'service', 'port', or 'rich-rule'
        rule_value: the service name, port/proto, or rich rule text
        zone: firewall zone
    """
    if rule_type == 'service':
        result = execute_safe([
            'firewall-cmd', '--permanent', '--zone', zone,
            '--query-service', rule_value
        ])
    elif rule_type == 'port':
        result = execute_safe([
            'firewall-cmd', '--permanent', '--zone', zone,
            '--query-port', rule_value
        ])
    elif rule_type == 'rich-rule':
        result = execute_safe([
            'firewall-cmd', '--permanent', '--zone', zone,
            '--query-rich-rule', rule_value
        ])
    else:
        return False

    return result.success


def check_selinux_fcontext_persistent(path, context_type):
    """Check that an SELinux file context rule exists in policy."""
    result = execute_safe(['semanage', 'fcontext', '-l'])
    if not result.success:
        return False

    for line in result.stdout.split('\n'):
        if path in line and context_type in line:
            return True
    return False


def check_setsebool_persistent(boolean_name, value):
    """Check that an SELinux boolean is persistently set."""
    result = execute_safe(['getsebool', boolean_name])
    if not result.success:
        return False

    expected = f"{boolean_name} --> {'on' if value else 'off'}"
    return expected in result.stdout


def check_cron_persists(user, pattern):
    """Check that a cron job exists for a user matching a pattern."""
    result = execute_safe(['crontab', '-l', '-u', user])
    if not result.success:
        return False

    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if pattern in line:
            return True
    return False


def check_systemd_timer_enabled(timer_name):
    """Check that a systemd timer is enabled."""
    if not timer_name.endswith('.timer'):
        timer_name += '.timer'
    return check_service_enabled(timer_name)


def check_repo_file_exists(repo_name):
    """Check that a .repo file exists in /etc/yum.repos.d/."""
    result = execute_safe(['test', '-f', f'/etc/yum.repos.d/{repo_name}.repo'])
    if result.success:
        return True
    # Try with case variations
    result = execute_safe(['ls', '/etc/yum.repos.d/'])
    if result.success:
        for fname in result.stdout.split():
            if repo_name.lower() in fname.lower() and fname.endswith('.repo'):
                return True
    return False


def check_network_connection_persistent(connection_name):
    """Check that a NetworkManager connection exists on disk."""
    result = execute_safe(['nmcli', '-t', 'connection', 'show', connection_name])
    return result.success


def check_hostname_persistent(expected_hostname):
    """Check that hostname is set persistently."""
    result = execute_safe(['hostnamectl', 'status'])
    if result.success and expected_hostname in result.stdout:
        return True
    return False


def check_user_exists(username):
    """Check that a user account exists."""
    result = execute_safe(['id', username])
    return result.success


def check_group_exists(groupname):
    """Check that a group exists."""
    result = execute_safe(['getent', 'group', groupname])
    return result.success


def check_lvm_exists(vg_name=None, lv_name=None):
    """Check that LVM structures exist."""
    if lv_name and vg_name:
        result = execute_safe(['lvs', f'{vg_name}/{lv_name}'])
        return result.success
    elif vg_name:
        result = execute_safe(['vgs', vg_name])
        return result.success
    return False


def check_swap_active(device_or_file):
    """Check that swap is active."""
    result = execute_safe(['swapon', '--show'])
    if result.success and device_or_file in result.stdout:
        return True
    return False
