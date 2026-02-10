"""
File and directory validators including permissions, ACLs, and SELinux contexts.
"""

import os
import stat
import logging
from pathlib import Path
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


# File Existence and Type Validators

def validate_file_exists(path, file_type=None):
    """
    Check if file/directory exists and optionally verify type.

    Args:
        path (str): Path to check
        file_type (str): Optional type: 'file', 'directory', 'link', 'socket', 'block', 'char'

    Returns:
        bool: True if exists and type matches
    """
    p = Path(path)

    if not p.exists():
        return False

    if file_type is None:
        return True

    if file_type == 'file':
        return p.is_file()
    elif file_type == 'directory':
        return p.is_dir()
    elif file_type == 'link':
        return p.is_symlink()
    elif file_type == 'socket':
        return p.is_socket()
    elif file_type == 'block':
        return p.is_block_device()
    elif file_type == 'char':
        return p.is_char_device()

    return False


def get_file_type(path):
    """
    Get file type.

    Args:
        path (str): Path to check

    Returns:
        str: File type or None
    """
    p = Path(path)
    if not p.exists():
        return None

    if p.is_file():
        return 'file'
    elif p.is_dir():
        return 'directory'
    elif p.is_symlink():
        return 'link'
    elif p.is_socket():
        return 'socket'
    elif p.is_block_device():
        return 'block'
    elif p.is_char_device():
        return 'char'

    return 'unknown'


# Permission Validators

def get_file_permissions(path):
    """
    Get file permissions in octal format.

    Args:
        path (str): File path

    Returns:
        str: Permissions in octal (e.g., '0644') or None
    """
    try:
        st = os.stat(path)
        # Get last 4 octal digits (includes special bits)
        perms = oct(stat.S_IMODE(st.st_mode))
        return perms
    except (OSError, IOError):
        return None


def validate_file_permissions(path, expected_perms):
    """
    Validate file permissions.

    Args:
        path (str): File path
        expected_perms (str): Expected permissions (e.g., '0644', '644', '755')

    Returns:
        bool: True if permissions match
    """
    actual = get_file_permissions(path)
    if actual is None:
        return False

    # Normalize expected permissions
    expected = expected_perms.lstrip('0o')
    if not expected.startswith('0'):
        expected = '0' + expected

    # Normalize actual permissions
    actual_normalized = actual.lstrip('0o')
    if not actual_normalized.startswith('0'):
        actual_normalized = '0' + actual_normalized

    return actual_normalized.endswith(expected.lstrip('0'))


def get_file_owner(path):
    """
    Get file owner username.

    Args:
        path (str): File path

    Returns:
        str: Owner username or None
    """
    result = execute_safe(['stat', '-c', '%U', path])
    if result.success:
        return result.stdout.strip()
    return None


def get_file_group(path):
    """
    Get file group name.

    Args:
        path (str): File path

    Returns:
        str: Group name or None
    """
    result = execute_safe(['stat', '-c', '%G', path])
    if result.success:
        return result.stdout.strip()
    return None


def validate_file_ownership(path, owner=None, group=None):
    """
    Validate file ownership.

    Args:
        path (str): File path
        owner (str): Expected owner username (optional)
        group (str): Expected group name (optional)

    Returns:
        bool: True if ownership matches
    """
    if owner is not None:
        actual_owner = get_file_owner(path)
        if actual_owner != owner:
            return False

    if group is not None:
        actual_group = get_file_group(path)
        if actual_group != group:
            return False

    return True


# ACL Validators

def validate_acl_exists(path):
    """
    Check if file has ACLs set.

    Args:
        path (str): File path

    Returns:
        bool: True if ACLs are set
    """
    result = execute_safe(['getfacl', path])
    if result.success:
        # Check if there are ACL entries beyond the standard user/group/other
        for line in result.stdout.split('\n'):
            if line.startswith('user:') and ':' in line[5:]:
                return True
            if line.startswith('group:') and ':' in line[6:]:
                return True
    return False


def get_acl(path):
    """
    Get ACL entries for a file.

    Args:
        path (str): File path

    Returns:
        list: List of ACL entries or None
    """
    result = execute_safe(['getfacl', '-p', path])
    if result.success:
        acl_entries = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                acl_entries.append(line)
        return acl_entries
    return None


def validate_acl_entry(path, acl_type, name, permissions):
    """
    Validate specific ACL entry.

    Args:
        path (str): File path
        acl_type (str): 'user' or 'group'
        name (str): Username or groupname
        permissions (str): Expected permissions (e.g., 'rwx', 'r-x')

    Returns:
        bool: True if ACL entry matches
    """
    acl_entries = get_acl(path)
    if acl_entries is None:
        return False

    # Format: user:username:permissions or group:groupname:permissions
    expected_entry = f"{acl_type}:{name}:{permissions}"

    for entry in acl_entries:
        if entry == expected_entry:
            return True

    return False


# SELinux Validators

def get_selinux_context(path):
    """
    Get SELinux context for a file.

    Args:
        path (str): File path

    Returns:
        str: SELinux context or None
    """
    result = execute_safe(['ls', '-Zd', path])
    if result.success:
        # Output format: "context path" or "context user group path"
        parts = result.stdout.split()
        if parts:
            return parts[0]
    return None


def get_selinux_type(path):
    """
    Get SELinux type context for a file.

    Args:
        path (str): File path

    Returns:
        str: SELinux type (e.g., 'httpd_sys_content_t') or None
    """
    context = get_selinux_context(path)
    if context:
        # Context format: user:role:type:level
        parts = context.split(':')
        if len(parts) >= 3:
            return parts[2]
    return None


def validate_selinux_context(path, expected_type):
    """
    Validate SELinux type context.

    Args:
        path (str): File path
        expected_type (str): Expected SELinux type

    Returns:
        bool: True if type matches
    """
    actual_type = get_selinux_type(path)
    return actual_type == expected_type


def get_selinux_mode():
    """
    Get current SELinux mode.

    Returns:
        str: 'Enforcing', 'Permissive', or 'Disabled'
    """
    result = execute_safe(['getenforce'])
    if result.success:
        return result.stdout.strip()
    return None


def validate_selinux_mode(expected_mode):
    """
    Validate SELinux mode.

    Args:
        expected_mode (str): Expected mode

    Returns:
        bool: True if mode matches
    """
    actual = get_selinux_mode()
    return actual and actual.lower() == expected_mode.lower()


def get_selinux_boolean(boolean_name):
    """
    Get SELinux boolean value.

    Args:
        boolean_name (str): Boolean name

    Returns:
        str: 'on' or 'off' or None
    """
    result = execute_safe(['getsebool', boolean_name])
    if result.success:
        # Output format: "boolean_name --> on"
        if '-->' in result.stdout:
            parts = result.stdout.split('-->')
            if len(parts) == 2:
                return parts[1].strip()
    return None


def validate_selinux_boolean(boolean_name, expected_value):
    """
    Validate SELinux boolean value.

    Args:
        boolean_name (str): Boolean name
        expected_value (str): Expected value ('on' or 'off')

    Returns:
        bool: True if value matches
    """
    actual = get_selinux_boolean(boolean_name)
    return actual == expected_value


# File Content Validators

def validate_file_contains(path, search_string, regex=False, case_sensitive=True):
    """
    Check if file contains a string or pattern.

    Args:
        path (str): File path
        search_string (str): String or regex pattern to search
        regex (bool): Whether to use regex matching
        case_sensitive (bool): Whether search is case-sensitive (default True)

    Returns:
        bool: True if string/pattern found
    """
    grep_args = ['grep']

    # Add case-insensitive flag if needed
    if not case_sensitive:
        grep_args.append('-i')

    # Add regex or fixed string flag
    if regex:
        grep_args.append('-E')
    else:
        grep_args.append('-F')

    grep_args.extend([search_string, path])

    result = execute_safe(grep_args)
    return result.success


def validate_file_line_count(path, expected_count):
    """
    Validate number of lines in file.

    Args:
        path (str): File path
        expected_count (int): Expected line count

    Returns:
        bool: True if line count matches
    """
    result = execute_safe(['wc', '-l', path])
    if result.success:
        # Output format: "count path"
        parts = result.stdout.split()
        if parts:
            try:
                actual_count = int(parts[0])
                return actual_count == expected_count
            except ValueError:
                pass
    return False


# Symlink Validators

def get_symlink_target(path):
    """
    Get symlink target path.

    Args:
        path (str): Symlink path

    Returns:
        str: Target path or None
    """
    try:
        p = Path(path)
        if p.is_symlink():
            return str(p.readlink())
    except (OSError, IOError):
        pass
    return None


def validate_symlink_target(path, expected_target):
    """
    Validate symlink target.

    Args:
        path (str): Symlink path
        expected_target (str): Expected target path

    Returns:
        bool: True if target matches
    """
    actual = get_symlink_target(path)
    return actual == expected_target


# Mount Point Validators

def is_mounted(mount_point):
    """
    Check if a directory is a mount point.

    Args:
        mount_point (str): Path to check

    Returns:
        bool: True if mounted
    """
    result = execute_safe(['mountpoint', '-q', mount_point])
    return result.success


def get_mount_info(mount_point):
    """
    Get mount information for a mount point.

    Args:
        mount_point (str): Mount point path

    Returns:
        dict: Mount information or None
    """
    result = execute_safe(['findmnt', '--json', mount_point])
    if result.success:
        try:
            import json
            data = json.loads(result.stdout)
            if 'filesystems' in data and data['filesystems']:
                return data['filesystems'][0]
        except:
            pass
    return None


def validate_mount(mount_point, device=None, fstype=None, options=None):
    """
    Validate mount configuration.

    Args:
        mount_point (str): Mount point path
        device (str): Expected device (optional)
        fstype (str): Expected filesystem type (optional)
        options (list): Expected mount options (optional)

    Returns:
        bool: True if mount configuration matches
    """
    if not is_mounted(mount_point):
        return False

    info = get_mount_info(mount_point)
    if not info:
        return False

    if device and info.get('source') != device:
        return False

    if fstype and info.get('fstype') != fstype:
        return False

    if options:
        actual_options = info.get('options', '').split(',')
        for opt in options:
            if opt not in actual_options:
                return False

    return True
