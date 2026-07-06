"""
Wall-clock-independent exam countdown, queryable from any terminal.

Exam tasks legitimately change the system date, time, and timezone, so neither
the simulator nor the candidate can trust `date` to know how much exam time is
left. This module anchors the countdown to /proc/uptime — a system-wide clock
that keeps counting no matter what the candidate does to the wall clock — and
persists it in a small sourceable state file so a separate terminal can query
it via the installed `exam-time-left` command (or `source` the state file).

State file format (shell-parseable on purpose):
    UPTIME_START=<seconds, from /proc/uptime at exam start>
    DURATION_SECONDS=<exam length>
    STARTED_WALL=<ISO timestamp, informational only>
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

STATE_FILE = '/var/lib/rhcsa-simulator/exam_clock'
QUERY_CMD = '/usr/local/bin/exam-time-left'

_QUERY_SCRIPT = '''#!/bin/sh
# Prints the time remaining in the running RHCSA-simulator exam.
# Anchored to /proc/uptime, so it stays correct even when exam tasks change
# the system date, time, or timezone. Installed by the simulator at exam start.
STATE=/var/lib/rhcsa-simulator/exam_clock
if [ ! -r "$STATE" ]; then
    echo "No exam in progress."
    exit 1
fi
. "$STATE"
now=$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)
start=${UPTIME_START%.*}
if [ -z "$now" ] || [ -z "$start" ] || [ "$now" -lt "$start" ]; then
    echo "Cannot compute time remaining (system rebooted since exam start?)."
    exit 1
fi
elapsed=$((now - start))
remaining=$((DURATION_SECONDS - elapsed))
if [ "$remaining" -le 0 ]; then
    echo "TIME IS UP ($((DURATION_SECONDS / 60)) minutes elapsed)."
    exit 0
fi
printf 'Time remaining: %dh %02dm %02ds   (elapsed %dm of %dm)\\n' \\
    $((remaining / 3600)) $((remaining % 3600 / 60)) $((remaining % 60)) \\
    $((elapsed / 60)) $((DURATION_SECONDS / 60))
'''


def _uptime():
    with open('/proc/uptime') as f:
        return float(f.read().split()[0])


def start(duration_minutes):
    """Record the exam start and (re)install the query command. Best-effort:
    an exam must never fail to start over the courtesy clock."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            f.write(
                f"UPTIME_START={_uptime():.0f}\n"
                f"DURATION_SECONDS={int(duration_minutes) * 60}\n"
                f"STARTED_WALL={datetime.now().isoformat(timespec='seconds')}\n")
        with open(QUERY_CMD, 'w') as f:
            f.write(_QUERY_SCRIPT)
        os.chmod(QUERY_CMD, 0o755)
        return True
    except Exception as e:
        logger.debug("exam_clock.start failed: %s", e)
        return False


def stop():
    """Clear the countdown (exam finished or box reset). The query command
    stays installed and reports 'No exam in progress.'"""
    try:
        os.remove(STATE_FILE)
    except OSError:
        pass


def remaining_seconds():
    """Remaining seconds for the recorded exam, or None if no exam is running
    or the anchor is unusable (e.g. the box rebooted since exam start)."""
    try:
        state = {}
        with open(STATE_FILE) as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    state[k] = v
        up_start = float(state['UPTIME_START'])
        duration = int(state['DURATION_SECONDS'])
        now = _uptime()
        if now < up_start:
            return None
        return max(0, int(duration - (now - up_start)))
    except Exception:
        return None
