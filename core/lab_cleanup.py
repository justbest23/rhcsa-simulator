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


# All filesystem touches go through a timeout-KILLABLE subprocess. A stale NFS
# mount (server gone while still mounted) makes a plain os.stat()/shutil.rmtree()
# block FOREVER and Python can't interrupt it — which hung the exam at start.
# An external command can be killed by subprocess's timeout, so the worst case
# is a few seconds per path instead of an infinite hang.

def _sh(cmd, timeout_s):
    """Run cmd, return its rc; 124 if it had to be killed for exceeding timeout."""
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout_s).returncode
    except subprocess.TimeoutExpired:
        return 124
    except Exception:
        return 1


def _exists(path):
    """Existence test (incl. broken symlinks) that can't hang on a stale mount."""
    return _sh(['bash', '-c', '[ -e "$1" ] || [ -L "$1" ]', '_', path], 6) == 0


def _expand(pattern):
    """Expand a glob without stat-ing matches (scandir only), else return as-is."""
    if any(c in pattern for c in '*?['):
        try:
            return sorted(glob.glob(pattern))
        except Exception:
            return []
    return [pattern]


def find_leftovers():
    """Existing artifact paths cleanup would act on (timeout-guarded)."""
    found = set()
    for pattern in SWAP_FILES + DIR_ARTIFACTS + FILE_ARTIFACTS:
        for match in _expand(pattern):
            if _is_safe(match) and _exists(match):
                found.add(os.path.normpath(match))
    return sorted(found)


def clean(dry_run=False):
    """Remove all existing lab artifacts. With dry_run, only report them.

    Mount points are lazily unmounted FIRST (fast even for a stale NFS mount) so
    the subsequent existence test / removal can't hang. Every step is a
    timeout-killable subprocess. Returns a list of action strings.
    """
    actions = []

    # 1. Swap files: swapoff then remove.
    for pattern in SWAP_FILES:
        for path in _expand(pattern):
            if not _is_safe(path):
                continue
            if dry_run:
                if _exists(path):
                    actions.append(f"would remove swap {path}")
                continue
            _sh(['swapoff', path], 15)
            if _exists(path) and _sh(['rm', '-f', '--', path], 15) == 0:
                actions.append(f"removed swap {path}")

    # 2. Directories / mount points: lazy-unmount first, then remove.
    for pattern in DIR_ARTIFACTS:
        for path in _expand(pattern):
            if not _is_safe(path):
                continue
            if not dry_run:
                # Detach a (possibly stale) mount before touching the path.
                _sh(['umount', '-l', '--', path], 10)
            if _exists(path):
                if dry_run:
                    actions.append(f"would remove dir  {path}")
                elif _sh(['rm', '-rf', '--', path], 25) == 0:
                    actions.append(f"removed dir  {path}")

    # 3. Files (incl. glob families).
    for pattern in FILE_ARTIFACTS:
        for path in _expand(pattern):
            if not _is_safe(path) or not _exists(path):
                continue
            if dry_run:
                actions.append(f"would remove file {path}")
            elif _sh(['rm', '-rf', '--', path], 15) == 0:
                actions.append(f"removed file {path}")

    return actions
