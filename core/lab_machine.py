"""
Shared "lab machine" link — a second box the simulator can reach as root
over SSH.

One link serves every feature that needs a remote machine: the boot-rescue
lab, remote fault injection/validation, and (as a host default) the NFS
server provisioning. It can be the same VM already used as the NFS server.

Design:
  * Linking plants THIS machine's SSH public key on the lab machine
    (ssh-copy-id), so everything afterwards runs unattended with key-based
    BatchMode auth. The key is the simulator's only footprint on the lab
    machine — no agent, nothing installed, nothing to keep updated.
  * The key MUST verify before any scenario is allowed to scramble
    credentials on the lab machine, otherwise we could lose our way back in.
  * Scripts are fed to `bash -s` over stdin (never the command line), so
    secrets embedded in a script are not visible in `ps` on either side.
"""

import os
import json
import glob
import subprocess

STATE_DIR = '/var/lib/rhcsa-simulator'
CONFIG_PATH = os.path.join(STATE_DIR, 'lab_machine.conf')


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def load_config():
    """Return {'host': ..., 'user': ...} or None. Falls back to an existing
    NFS-server link so users who already set that up are linked implicitly."""
    try:
        with open(CONFIG_PATH) as fh:
            return json.load(fh)
    except Exception:
        pass
    # Adopt the NFS server link if one exists (same box, per design).
    try:
        from core import nfs_server
        cfg = nfs_server.load_config()
        if cfg and cfg.get('host'):
            return {'host': cfg['host'], 'user': cfg.get('user', 'root'),
                    'adopted_from': 'nfs_server'}
    except Exception:
        pass
    return None


def save_config(host, user='root'):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as fh:
        json.dump({'host': host, 'user': user}, fh, indent=2)
    return {'host': host, 'user': user}


def clear_config():
    try:
        os.remove(CONFIG_PATH)
        return True
    except FileNotFoundError:
        return False


def get_host():
    cfg = load_config()
    return cfg.get('host') if cfg else None


# --------------------------------------------------------------------------
# Key management
# --------------------------------------------------------------------------

def _have_local_key():
    home = os.path.expanduser('~/.ssh')
    return bool(glob.glob(os.path.join(home, 'id_*.pub')))


def ensure_local_key():
    """Make sure this machine has an SSH keypair to plant. Returns True if a
    key exists (or was just generated)."""
    if _have_local_key():
        return True
    path = os.path.expanduser('~/.ssh/id_ed25519')
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    r = subprocess.run(['ssh-keygen', '-t', 'ed25519', '-N', '', '-f', path],
                       capture_output=True, text=True)
    return r.returncode == 0


def copy_key(host, user='root'):
    """Interactive ssh-copy-id (the one step that may prompt for a password)."""
    ensure_local_key()
    try:
        return subprocess.run(['ssh-copy-id', f'{user}@{host}']).returncode == 0
    except FileNotFoundError:
        return False


def key_works(host=None, user=None, timeout=20):
    """True if unattended key-based SSH to the lab machine works right now."""
    cfg = load_config() or {}
    host = host or cfg.get('host')
    user = user or cfg.get('user', 'root')
    if not host:
        return False
    rc, _ = run('true', host=host, user=user, timeout=timeout)
    return rc == 0


# --------------------------------------------------------------------------
# Remote execution
# --------------------------------------------------------------------------

def run(script, host=None, user=None, timeout=120):
    """Run `script` on the lab machine over key-auth SSH (BatchMode — never
    prompts). Returns (returncode, combined_output); rc None on launch error.

    The script goes over stdin, so it may safely contain secrets."""
    cfg = load_config() or {}
    host = host or cfg.get('host')
    user = user or cfg.get('user', 'root')
    if not host:
        return None, 'no lab machine linked (Setup → Link second lab machine)'
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=accept-new',
           '-o', 'ConnectTimeout=15', '-o', 'BatchMode=yes',
           f'{user}@{host}', 'bash -s']
    try:
        res = subprocess.run(cmd, input=script, text=True,
                             capture_output=True, timeout=timeout)
        return res.returncode, (res.stdout or '') + (res.stderr or '')
    except FileNotFoundError:
        return None, "'ssh' not found on this machine."
    except subprocess.TimeoutExpired:
        return None, f'Timed out talking to {host}.'


def read_values(script, host=None, user=None, timeout=120):
    """Run a script that prints KEY=VALUE lines; return (ok, dict, output).
    Only lines matching ^[A-Z_]+= are collected, so command noise is ignored."""
    rc, out = run(script, host=host, user=user, timeout=timeout)
    values = {}
    for line in (out or '').splitlines():
        if '=' in line:
            key, _, val = line.partition('=')
            if key and key.isupper() and key.replace('_', '').isalnum():
                values[key] = val.strip()
    return rc == 0, values, out
