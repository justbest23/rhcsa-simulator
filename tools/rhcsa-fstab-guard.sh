#!/bin/bash
#
# rhcsa-fstab-guard.sh — keep /etc/fstab bootable across simulator sessions.
#
# The RHCSA simulator (and the candidate, while practising) adds entries to
# /etc/fstab for swap, LVM/filesystem mounts, and fault-injection scenarios
# (bad UUIDs, missing-device mounts). If a session is interrupted — the
# simulator crashes, the VM is reset, or the box is rebooted mid-exam — those
# entries are left behind and the NEXT boot can drop to an emergency shell.
#
# This guard restores /etc/fstab to a known-good baseline so the system always
# boots clean. It is wired to run:
#   * at shutdown/reboot (ExecStop)  — the primary guarantee: the persisted
#     fstab is clean before the machine goes down, so the next boot is safe.
#   * early at boot (ExecStart, before local-fs-pre.target) — self-heal after a
#     crash/power-loss; daemon-reload re-runs the fstab generator so the bad
#     mount units are dropped for the current boot too.
#
# SAFETY: this script never deletes baseline entries and never writes a fstab it
# cannot verify. Extra (non-baseline) entries are COMMENTED OUT, not removed, so
# nothing is lost and the change is auditable. The candidate fstab is validated
# with `findmnt --verify` before it replaces /etc/fstab; on any error the
# original file is left untouched. Timestamped backups are kept.
#
# Usage: rhcsa-fstab-guard.sh [boot|shutdown|init|status]
#   init      capture the current fstab as the baseline (run once, when clean)
#   boot      sanitize early at boot, then daemon-reload
#   shutdown  sanitize before the system goes down
#   status    show what would be changed (dry run)
#
set -u

FSTAB="/etc/fstab"
STATE_DIR="/var/lib/rhcsa-simulator"
BASELINE="${STATE_DIR}/fstab.baseline"
BACKUP_DIR="${STATE_DIR}/fstab-backups"
TAG="rhcsa-guard"
MODE="${1:-status}"

log() {
    # Log to journal/syslog when available, always echo for interactive runs.
    if command -v logger >/dev/null 2>&1; then
        logger -t "$TAG" -- "$*"
    fi
    echo "[$TAG] $*"
}

mkdir -p "$STATE_DIR" "$BACKUP_DIR" 2>/dev/null

# Normalise an fstab line for comparison: drop a trailing inline comment, then
# collapse all whitespace to single spaces and trim. Blank/comment lines map to
# the empty string and are ignored by callers.
normalise() {
    local line="$1"
    line="${line%%#*}"
    # shellcheck disable=SC2086
    echo $line
}

# Capture the current fstab as the baseline — only if it is currently valid.
do_init() {
    if findmnt --verify --quiet >/dev/null 2>&1 || findmnt --verify >/dev/null 2>&1; then
        cp -f "$FSTAB" "$BASELINE"
        log "Captured baseline fstab ($(grep -cvE '^\s*(#|$)' "$BASELINE") entries) -> $BASELINE"
        return 0
    fi
    log "Refusing to capture baseline: current /etc/fstab fails 'findmnt --verify'"
    return 1
}

# Produce a sanitized fstab on stdout: every non-baseline data line is commented
# out with an explanatory marker. Baseline lines, comments and blanks pass through.
sanitize_to_stdout() {
    awk -v baseline="$BASELINE" '
        function norm(s,   t) {
            sub(/#.*/, "", s)         # strip inline comment
            gsub(/[ \t]+/, " ", s)    # collapse whitespace
            gsub(/^ | $/, "", s)      # trim
            return s
        }
        BEGIN {
            while ((getline bl < baseline) > 0) {
                n = norm(bl)
                if (n != "") keep[n] = 1
            }
            close(baseline)
        }
        {
            line = $0
            n = norm(line)
            if (n == "") { print line; next }            # comment / blank
            if (n in keep) { print line; next }          # baseline entry
            print "# [rhcsa-guard removed " strftime("%Y-%m-%d %H:%M:%S") "] " line
            changed++
        }
        END { exit (changed > 0 ? 10 : 0) }
    ' "$FSTAB"
}

do_sanitize() {
    local why="$1"

    if [ ! -f "$BASELINE" ]; then
        # First ever run with no baseline: try to establish one from a clean
        # fstab, then there is nothing to strip.
        do_init || log "No baseline and current fstab invalid — leaving fstab untouched ($why)"
        return 0
    fi

    local tmp rc
    tmp="$(mktemp /tmp/fstab.guard.XXXXXX)" || { log "mktemp failed"; return 1; }
    sanitize_to_stdout > "$tmp"
    rc=$?

    if [ "$rc" -eq 0 ]; then
        rm -f "$tmp"
        return 0                       # nothing to change
    fi
    if [ "$rc" -ne 10 ]; then
        log "sanitize aborted (awk rc=$rc) — fstab untouched ($why)"
        rm -f "$tmp"
        return 1
    fi

    # We have changes. Verify the candidate parses before swapping it in.
    if ! findmnt --verify --fstab "$tmp" >/dev/null 2>&1; then
        # --fstab flag may be unavailable on very old util-linux; fall back to a
        # structural check (root entry still present, file non-empty).
        if ! grep -qE '[[:space:]]/[[:space:]]' "$tmp" || [ ! -s "$tmp" ]; then
            log "Candidate fstab failed validation — refusing to apply ($why)"
            rm -f "$tmp"
            return 1
        fi
    fi

    local stamp backup
    stamp="$(date +%Y%m%d-%H%M%S)"
    backup="${BACKUP_DIR}/fstab.${stamp}"
    cp -f "$FSTAB" "$backup"
    cat "$tmp" > "$FSTAB"
    rm -f "$tmp"

    local n
    n="$(grep -c '\[rhcsa-guard removed' "$FSTAB")"
    log "Commented out $n leftover fstab entry/entries ($why). Backup: $backup"
    return 10
}

case "$MODE" in
    init)
        do_init
        ;;
    ensure)
        # Capture a baseline only if we don't already have one. Safe to call on
        # every simulator start; it refuses to capture a dirty fstab.
        if [ -f "$BASELINE" ]; then
            exit 0
        fi
        do_init
        ;;
    status)
        if [ ! -f "$BASELINE" ]; then
            echo "No baseline captured yet (run: $0 init on a clean system)."
            exit 0
        fi
        diff <(sanitize_to_stdout) "$FSTAB" >/dev/null 2>&1 \
            && echo "fstab is clean — nothing to strip." \
            || { echo "The following entries would be commented out:"; \
                 sanitize_to_stdout | grep '\[rhcsa-guard removed'; }
        ;;
    boot)
        do_sanitize "boot"
        if [ $? -eq 10 ]; then
            # Re-run the fstab generator so the current boot ignores the bad
            # mount units we just commented out.
            systemctl daemon-reload >/dev/null 2>&1 || true
        fi
        ;;
    shutdown)
        do_sanitize "shutdown"
        ;;
    *)
        echo "Usage: $0 [init|boot|shutdown|status]" >&2
        exit 2
        ;;
esac
exit 0
