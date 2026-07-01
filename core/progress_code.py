"""
Portable progress codes — carry your task history + SM-2 state across installs
without any login or server.

A code is a self-contained, copy-pasteable string that encodes everything the
simulator needs to reconstruct your progress (what you got right/wrong, per
category and per attempt, plus the adaptive spaced-repetition state). Export a
code before a VM snapshot/revert or a reinstall, then import it on the fresh
box.

Format (kept purely uppercase-alphanumeric so it survives copy/paste and can be
typed): the payload is JSON → zlib-compressed → prefixed with a 3-byte magic
and a CRC32 → Base32-encoded. On import we strip anything outside the Base32
alphabet, re-pad, and verify the magic + checksum so a corrupted/mistyped code
is rejected rather than silently importing garbage.
"""

import base64
import binascii
import json
import zlib

MAGIC = b'RH1'            # bumped if the payload layout changes
_GROUP = 8                # dash-group size for display
_ALPHABET = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')


class ProgressCodeError(Exception):
    """Raised when a code can't be decoded (not ours, corrupt, or mistyped)."""


def encode(payload):
    """dict -> shareable code string."""
    raw = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    crc = binascii.crc32(raw) & 0xffffffff
    blob = MAGIC + crc.to_bytes(4, 'big') + zlib.compress(raw, 9)
    b32 = base64.b32encode(blob).decode('ascii').rstrip('=')
    # Group with dashes for readability; dashes are stripped on import.
    return '-'.join(b32[i:i + _GROUP] for i in range(0, len(b32), _GROUP))


def _normalize(code):
    return ''.join(c for c in code.upper() if c in _ALPHABET)


def decode(code):
    """code string -> dict. Raises ProgressCodeError on any problem."""
    s = _normalize(code)
    if not s:
        raise ProgressCodeError("empty or unreadable code")
    pad = (-len(s)) % 8
    try:
        blob = base64.b32decode(s + '=' * pad)
    except binascii.Error as e:
        raise ProgressCodeError(f"not a valid code ({e})")
    if len(blob) < 7 or blob[:3] != MAGIC:
        raise ProgressCodeError("this is not an RHCSA progress code")
    crc_expected = int.from_bytes(blob[3:7], 'big')
    try:
        raw = zlib.decompress(blob[7:])
    except zlib.error as e:
        raise ProgressCodeError(f"corrupt code ({e})")
    if (binascii.crc32(raw) & 0xffffffff) != crc_expected:
        raise ProgressCodeError("checksum mismatch — the code was mistyped or truncated")
    try:
        return json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        raise ProgressCodeError(f"corrupt payload ({e})")


# ── High-level helpers tying the codec to ResultsDB ──────────────────────────

def export_code(db=None):
    """Read the ResultsDB and return a progress code string."""
    if db is None:
        from core.results_db import get_results_db
        db = get_results_db()
    payload = db.dump_progress()
    payload['v'] = 1
    return encode(payload)


def summarize(payload):
    """Human-readable counts for a decoded payload (for a pre-import preview)."""
    return {
        'exams': len(payload.get('exams', [])),
        'exam tasks': len(payload.get('tasks', [])),
        'practice attempts': len(payload.get('practice', [])),
        'categories (SM-2)': len(payload.get('weak', [])),
    }


def import_code(code, mode='replace', db=None):
    """Decode a code and load it into the ResultsDB. Returns (counts, summary).
    Raises ProgressCodeError if the code is invalid."""
    payload = decode(code)
    if db is None:
        from core.results_db import get_results_db
        db = get_results_db()
    counts = db.load_progress(payload, mode=mode)
    return counts, summarize(payload)
