"""
Preflight package check.

Several troubleshooting fault-injectors and positive-configuration tasks
assume common exam-relevant packages already exist on the box (httpd,
vsftpd, nfs-utils, samba, chrony...). A minimal RHEL/Rocky/Alma install
often doesn't have them. When a package is missing, a task's
inject_fault()/setup_environment() call still "succeeds" (its own commands
just no-op or fail silently) so the resulting scenario looks like it was
never created — e.g. an httpd 403 troubleshooting task where httpd was
never actually running.

This module runs a read-only `rpm -q` check at startup and warns about
what's missing so the gap is visible up front instead of surfacing later
as a confusing "nothing happened" task.
"""

import subprocess

from utils import formatters as fmt

# package -> which tasks need it
REQUIRED_PACKAGES = {
    'httpd': 'Apache web server tasks (SELinux, firewall, service troubleshooting)',
    'vsftpd': 'FTP service tasks',
    'nfs-utils': 'NFS server/client and network storage tasks',
    'samba': 'Samba/SMB file sharing tasks',
    'chrony': 'time synchronization tasks',
    'firewalld': 'firewall management and troubleshooting tasks',
    'bind-utils': 'DNS lookup tooling used by networking tasks',
    'tuned': 'tuning profile (tuned-adm) tasks',
}


def _rpm_installed(pkg):
    """True/False if rpm can answer, None if rpm itself isn't available
    (e.g. a non-RPM environment such as a CI container)."""
    try:
        r = subprocess.run(['rpm', '-q', pkg], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def check_dependencies(packages=None):
    """Return {pkg: True|False|None} for each of REQUIRED_PACKAGES (or the
    given package list). None means installation status is unknown."""
    packages = packages if packages is not None else REQUIRED_PACKAGES
    return {pkg: _rpm_installed(pkg) for pkg in packages}


def missing_packages(statuses=None):
    """Packages confirmed NOT installed (excludes unknown/None statuses)."""
    statuses = statuses if statuses is not None else check_dependencies()
    return sorted(pkg for pkg, installed in statuses.items() if installed is False)


def warn_missing(missing=None):
    """Print a one-time warning listing missing packages and how to install
    them. No-op if nothing is missing (or rpm status is unknown)."""
    missing = missing if missing is not None else missing_packages()
    if not missing:
        return
    print(fmt.warning(
        f"\n! {len(missing)} exam-relevant package(s) not installed: {', '.join(missing)}"
    ))
    for pkg in missing:
        print(fmt.dim(f"    {pkg} — {REQUIRED_PACKAGES.get(pkg, '')}"))
    print(fmt.warning(
        "  Tasks that rely on them may fail to set up their scenario "
        "(e.g. an httpd task where httpd never runs).\n"
        f"  Install with: dnf install -y {' '.join(missing)}\n"
    ))
