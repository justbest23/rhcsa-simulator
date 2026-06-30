"""
Remote NFS server provisioning for NFS practice tasks.

The NFS tasks (tasks/network_storage.py) need a *real* NFS server to mount
from, otherwise the candidate can't actually complete or test them. This module
lets Setup SSH into a RHEL box the user names, provision it as an NFS server
(install nfs-utils, create + populate exports, write /etc/exports.d, run
exportfs, enable nfs-server, open the firewall), and record it so the NFS tasks
point at the real server and exports.

Auth is delegated to the system `ssh` (it prompts for a password or key
passphrase on the terminal as needed); no credentials are stored. Only the
server host, login user and export paths are saved.
"""

import os
import json
import subprocess

STATE_DIR = '/var/lib/rhcsa-simulator'
CONFIG_PATH = os.path.join(STATE_DIR, 'nfs_server.conf')

EXPORT_BASE = '/exports/rhcsa'
# (relative-name, export-options) — populated read/write so candidates can test.
_EXPORTS = [
    ('data', 'rw,sync,no_root_squash'),
    ('shared', 'rw,sync,no_root_squash'),
    ('public', 'ro,sync'),
]

# Sentinels the remote script prints so we can confirm success / read exports.
_DONE = 'RHCSA_NFS_DONE'
_EXPORTS_LINE = 'RHCSA_NFS_EXPORTS='


def _remote_script():
    """Idempotent bash provisioning script run on the remote server."""
    exports_paths = [f'{EXPORT_BASE}/{name}' for name, _ in _EXPORTS]
    mkdirs = ' '.join(exports_paths)
    export_lines = "\n".join(
        f'{EXPORT_BASE}/{name} *({opts})' for name, opts in _EXPORTS
    )
    # Seed each export with recognisable, relevant content so that cd-ing into a
    # successful mount obviously shows real files. Every export carries a
    # MANIFEST stamped with the server hostname + time so it's unmistakable.
    seed = f"""
stamp="provisioned by rhcsa-simulator on $(hostname -f 2>/dev/null || hostname) at $(date)"

# data/ — looks like an application data share
mkdir -p {EXPORT_BASE}/data/archive
printf 'date,region,units,revenue\\n2026-01-15,EMEA,120,30450\\n2026-02-03,AMER,98,24010\\n2026-03-20,APAC,142,35980\\n' > {EXPORT_BASE}/data/sales-2026-q1.csv
printf 'widget-a 412\\nwidget-b 87\\nwidget-c 0\\n' > {EXPORT_BASE}/data/inventory.txt
printf 'old rotated log line 1\\nold rotated log line 2\\n' > {EXPORT_BASE}/data/archive/2025.log
printf 'NFS export: data (read-write)\\n%s\\n' "$stamp" > {EXPORT_BASE}/data/MANIFEST.txt

# shared/ — looks like a team collaboration share
mkdir -p {EXPORT_BASE}/shared/projects
printf '# Team Roster\\nalice - lead\\nbob - sysadmin\\ncarol - dba\\n' > {EXPORT_BASE}/shared/team-roster.md
printf 'Standup notes 2026-06-30: NFS migration on track.\\n' > {EXPORT_BASE}/shared/meeting-notes.txt
printf 'project alpha: active\\nproject beta: planning\\n' > {EXPORT_BASE}/shared/projects/status.txt
printf 'NFS export: shared (read-write)\\n%s\\n' "$stamp" > {EXPORT_BASE}/shared/MANIFEST.txt

# public/ — read-only share
printf 'Welcome to the RHCSA practice NFS server.\\nThis share is read-only.\\n' > {EXPORT_BASE}/public/announcement.txt
printf 'rhcsa-simulator NFS v1\\n' > {EXPORT_BASE}/public/VERSION
printf 'NFS export: public (read-only)\\n%s\\n' "$stamp" > {EXPORT_BASE}/public/MANIFEST.txt
"""
    return f"""set -e
echo '== rhcsa-simulator: provisioning NFS server =='
dnf -y install nfs-utils >/dev/null 2>&1 || dnf -y install nfs-utils
mkdir -p {mkdirs}
{seed}
chmod -R 0777 {EXPORT_BASE}/data {EXPORT_BASE}/shared 2>/dev/null || true
# Write our exports to a dedicated drop-in so we never clobber existing ones.
mkdir -p /etc/exports.d
cat > /etc/exports.d/rhcsa.exports <<'EOF'
{export_lines}
EOF
# Restore SELinux contexts for the export tree (public_content_t-friendly).
command -v restorecon >/dev/null 2>&1 && restorecon -R {EXPORT_BASE} 2>/dev/null || true
systemctl enable --now nfs-server
exportfs -ra
# Open the firewall if firewalld is running (ignore if it isn't).
if systemctl is-active --quiet firewalld; then
  firewall-cmd --permanent --add-service=nfs >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-service=mountd >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-service=rpc-bind >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
fi
echo '== current exports =='
exportfs -v || true
echo '{_EXPORTS_LINE}'{','.join(exports_paths)!r}
echo '{_DONE}'
"""


# --------------------------------------------------------------------------
# Config persistence
# --------------------------------------------------------------------------

def load_config():
    """Return the saved NFS server config dict, or None."""
    try:
        with open(CONFIG_PATH) as fh:
            return json.load(fh)
    except Exception:
        return None


def save_config(host, user, exports):
    os.makedirs(STATE_DIR, exist_ok=True)
    cfg = {'host': host, 'user': user, 'exports': exports}
    with open(CONFIG_PATH, 'w') as fh:
        json.dump(cfg, fh, indent=2)
    return cfg


def clear_config():
    try:
        os.remove(CONFIG_PATH)
        return True
    except FileNotFoundError:
        return False


def get_server():
    """Configured server host, or None."""
    cfg = load_config()
    return cfg.get('host') if cfg else None


def pick_export(cfg=None, index=0):
    """Return (export_path) from the configured exports by index (stable)."""
    cfg = cfg or load_config()
    if not cfg or not cfg.get('exports'):
        return None
    exports = cfg['exports']
    return exports[index % len(exports)]


# --------------------------------------------------------------------------
# SSH provisioning
# --------------------------------------------------------------------------

def copy_ssh_key(host, user):
    """Best-effort ssh-copy-id so subsequent runs are passwordless. Interactive."""
    try:
        return subprocess.run(['ssh-copy-id', f'{user}@{host}']).returncode == 0
    except FileNotFoundError:
        return False


def provision(host, user='root'):
    """Run the provisioning script on the remote over interactive ssh.

    Returns (ok, exports, output). ssh prompts for password/passphrase on the
    terminal as needed; the script is fed on stdin (ssh reads auth from the tty,
    not stdin, so this is safe).
    """
    script = _remote_script()
    # BatchMode is NOT set, so ssh can prompt. StrictHostKeyChecking=accept-new
    # avoids a separate interactive yes/no for first-time hosts.
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=accept-new',
           f'{user}@{host}', 'bash -s']
    try:
        res = subprocess.run(cmd, input=script, text=True,
                             capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        return False, [], 'Timed out talking to the server (10 min).'
    except FileNotFoundError:
        return False, [], "'ssh' not found on this machine."

    output = (res.stdout or '') + (res.stderr or '')
    if res.returncode != 0 or _DONE not in (res.stdout or ''):
        return False, [], output

    exports = []
    for line in res.stdout.splitlines():
        if line.startswith(_EXPORTS_LINE):
            raw = line[len(_EXPORTS_LINE):].strip().strip("'\"")
            exports = [p for p in raw.split(',') if p]
            break
    if not exports:
        exports = [f'{EXPORT_BASE}/{name}' for name, _ in _EXPORTS]
    return True, exports, output


def verify_from_client(host):
    """Run showmount -e against the server from this machine. (ok, output)."""
    try:
        res = subprocess.run(['showmount', '-e', host],
                             capture_output=True, text=True, timeout=30)
        return res.returncode == 0, (res.stdout or res.stderr).strip()
    except FileNotFoundError:
        return False, "'showmount' not installed (dnf install nfs-utils)."
    except subprocess.TimeoutExpired:
        return False, 'showmount timed out (firewall? nfs-server not running?).'
