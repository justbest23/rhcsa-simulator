"""
Lab leftover cleanup.

Tasks ask the candidate to create files, directories, mounts and swap in a known
set of locations (/tmp scratch outputs, /mnt mount points, /opt, /srv, a couple
of /root markers, /home/guests, swap files). When a previous lab/session is
interrupted, those artifacts linger (e.g. a stray /tmp/special_perms.txt) and
can interfere with the next run.

Rather than snapshot the whole filesystem and diff it (which risks deleting
unrelated user data), this module removes ONLY the specific paths the
simulator's own tasks define — a curated manifest derived from the task set.
It never touches /etc (fstab is handled separately by the fstab guard) and never
touches shell dotfiles, SSH keys, or anything outside the manifest.
"""

import os
import glob
import shutil
import subprocess

# Swap files a task may ask the candidate to create (swapoff before removing).
SWAP_FILES = ['/swapfile', '/var/swap', '/swap.img']

# Mount points / directories tasks create. Unmounted first if mounted, then the
# directory tree is removed (these are simulator-owned scratch locations).
DIR_ARTIFACTS = [
    '/mnt/data', '/mnt/nfsdata', '/mnt/shared', '/mnt/persistent',
    '/mnt/practice_extend', '/mnt/vfat', '/mnt/external', '/mnt/faulttest',
    '/mnt/recovery', '/mnt/rescue', '/mnt/sysimage', '/mnt/nonexistent',
    '/mnt/lvm*',
    '/opt/appdata', '/opt/webdata',
    '/srv/nfs', '/srv/samba', '/srv/website', '/srv/web', '/srv/webapp',
    '/srv/shares', '/srv/ftp',
    '/home/guests',
]

# Individual files/dirs under /tmp and a couple of /root, /home markers. Globs
# cover the randomised name families (journal_*, scp_*, top_*, etc.).
FILE_ARTIFACTS = [
    # /tmp scratch outputs
    '/tmp/special_perms.txt', '/tmp/specialperm*',
    '/tmp/processed.txt', '/tmp/sorted_output.txt', '/tmp/diff_output.txt',
    '/tmp/extracted_field.txt', '/tmp/findresults.txt', '/tmp/grepresults.txt',
    '/tmp/boot_analysis.*', '/tmp/boot_entries.txt', '/tmp/boot_errors.log',
    '/tmp/boot_issues.txt', '/tmp/grub_entries.txt', '/tmp/journal_*',
    '/tmp/cron_jobs.txt', '/tmp/cronlog.txt', '/tmp/atjob.log',
    '/tmp/active-timers-*', '/tmp/failed-services-*', '/tmp/top_*',
    '/tmp/tuned_profiles.txt', '/tmp/dnf_history.txt', '/tmp/pkg_info.txt',
    '/tmp/package_provider.txt', '/tmp/rpm_verify.txt',
    '/tmp/backup.tar*', '/tmp/bg_process.pid', '/tmp/rw_test_passed',
    '/tmp/hardlink*', '/tmp/passwdlink*', '/tmp/flatpak_*',
    '/tmp/remote_pull_*', '/tmp/scp_src_*', '/tmp/scp_dst_*',
    '/tmp/scp_transfer_*',
    # /tmp dirs
    '/tmp/extracted', '/tmp/chroot_test', '/tmp/sysroot_sim',
    '/tmp/acltest*', '/tmp/ownertest*', '/tmp/original', '/tmp/testfile*',
    # /root markers (NEVER dotfiles)
    '/root/recovery_marker.txt', '/root/rw_confirmed',
    # /home symlink lab
    '/home/loglink',
]

# Hard safety floor: a target must live under one of these and not BE one of
# them. Guards against a bad glob ever matching '/', '/etc', a top-level dir, etc.
_ALLOWED_PREFIXES = ('/tmp/', '/mnt/', '/opt/', '/srv/', '/root/', '/home/', '/var/swap')
_NEVER = {'/tmp', '/mnt', '/opt', '/srv', '/root', '/home', '/var', '/'}
# Belt-and-braces: never remove these even if a glob somehow matches them.
_PROTECT = {'/root/.bashrc', '/root/.bash_profile', '/root/.ssh',
            '/root/.bash_history'}


def _is_safe(path):
    path = os.path.normpath(path)
    if path in _NEVER or path in _PROTECT:
        return False
    if path in SWAP_FILES:
        return True
    return path.startswith(_ALLOWED_PREFIXES)


def _is_mounted(path):
    try:
        return os.path.ismount(path)
    except OSError:
        return False


def find_leftovers():
    """Return the sorted list of existing artifact paths that cleanup would act
    on (after glob expansion and the safety filter)."""
    found = set()
    for pattern in SWAP_FILES + DIR_ARTIFACTS + FILE_ARTIFACTS:
        for match in (glob.glob(pattern) if any(c in pattern for c in '*?[') else [pattern]):
            if os.path.lexists(match) and _is_safe(match):
                found.add(os.path.normpath(match))
    return sorted(found)


def _remove_one(path):
    """Remove a single artifact (swapoff / unmount as needed). Returns an action
    string describing what was done, or None on failure."""
    if not _is_safe(path) or not os.path.lexists(path):
        return None
    try:
        if path in SWAP_FILES:
            subprocess.run(['swapoff', path], capture_output=True, timeout=15)
        if _is_mounted(path):
            subprocess.run(['umount', '-l', path], capture_output=True, timeout=15)
        if os.path.islink(path) or os.path.isfile(path):
            os.remove(path)
            return f"removed file {path}"
        if os.path.isdir(path):
            shutil.rmtree(path)
            return f"removed dir  {path}"
    except Exception as e:
        return f"FAILED {path}: {e}"
    return None


def clean(dry_run=False):
    """Remove all existing lab artifacts. With dry_run, only report them.
    Returns a list of action strings."""
    actions = []
    for path in find_leftovers():
        if dry_run:
            kind = 'dir ' if os.path.isdir(path) and not os.path.islink(path) else 'file'
            actions.append(f"would remove {kind} {path}")
        else:
            result = _remove_one(path)
            if result:
                actions.append(result)
    return actions
