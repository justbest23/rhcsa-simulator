#!/usr/bin/env python3
"""Detect a Claude Code subscription usage-limit stop in an execution log.

Usage:  claude_usage_limit.py <execution_file>

Reads the claude-code-action execution file (a JSON transcript, but treated
as plain text so upstream format changes don't break detection) and appends
GitHub Actions outputs to $GITHUB_OUTPUT:

    rate_limited=true|false
    reset_epoch=<unix seconds, UTC>            (only when rate_limited)
    reset_human=<e.g. 2026-07-07 17:00 SAST>   (only when rate_limited)

Known message shapes handled:
  * "Claude AI usage limit reached|1751890000"          (epoch after a pipe)
  * "5-hour limit reached ∙ resets 3pm"
  * "... usage limit reached ... resets at 3:30pm (Africa/Johannesburg)"

If a limit is detected but no reset time can be parsed, fall back to
now + 30 minutes: the scheduled resumer will retry, hit the limit again if
it is still active, and re-persist a fresh state comment. Self-correcting.
"""

import os
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Timezone assumed when the CLI prints a bare wall-clock time with no zone.
DEFAULT_TZ = os.environ.get("CLAUDE_RESET_TZ", "Africa/Johannesburg")

# A grace margin so we never resume seconds *before* the window actually opens.
MARGIN_SECONDS = 120

LIMIT_RE = re.compile(
    r"usage limit reached|5-hour limit reached|limit will reset", re.IGNORECASE
)
EPOCH_RE = re.compile(r"limit reached\|(\d{9,11})")
WALL_RE = re.compile(
    r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s*\(([^)]+)\))?",
    re.IGNORECASE,
)


def emit(**outputs):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        for key, value in outputs.items():
            fh.write(f"{key}={value}\n")


def parse_wall_time(match, now_ts):
    hour = int(match.group(1)) % 12
    if match.group(3).lower() == "pm":
        hour += 12
    minute = int(match.group(2) or 0)
    tz_name = (match.group(4) or DEFAULT_TZ).strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(DEFAULT_TZ)
    now = datetime.fromtimestamp(now_ts, tz)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return int(candidate.timestamp())


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        text = ""

    if not LIMIT_RE.search(text):
        emit(rate_limited="false")
        print("No usage-limit message found.")
        return

    now_ts = time.time()
    epoch = None

    epoch_match = EPOCH_RE.search(text)
    if epoch_match:
        epoch = int(epoch_match.group(1))
    else:
        wall_match = WALL_RE.search(text)
        if wall_match:
            epoch = parse_wall_time(wall_match, now_ts)

    if epoch is None or epoch <= now_ts:
        epoch = int(now_ts) + 30 * 60
        print("Limit detected but reset time unparseable; retrying in 30 min.")

    epoch += MARGIN_SECONDS
    human = datetime.fromtimestamp(epoch, ZoneInfo(DEFAULT_TZ)).strftime(
        "%Y-%m-%d %H:%M %Z"
    )
    emit(rate_limited="true", reset_epoch=str(epoch), reset_human=human)
    print(f"Usage limit detected; window resets at {human} (epoch {epoch}).")


if __name__ == "__main__":
    main()
