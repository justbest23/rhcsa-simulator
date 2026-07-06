"""
Enhanced timer system with time pressure warnings for RHCSA Simulator.
Provides countdown timer with configurable warning thresholds.
"""

import time
import threading
import sys
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from dataclasses import dataclass


@dataclass
class TimerWarning:
    """Configuration for a timer warning."""
    minutes_remaining: int
    message: str
    sound: bool = True
    color: str = 'yellow'


class ExamTimer:
    """
    Enhanced exam timer with time pressure warnings.

    Features:
    - Countdown display
    - Configurable warning thresholds
    - Audio/visual alerts
    - Pause/resume capability
    - Background thread for continuous updates
    """

    # Default warning thresholds
    DEFAULT_WARNINGS = [
        TimerWarning(60, "1 hour remaining - You should be halfway through the tasks", color='green'),
        TimerWarning(30, "30 MINUTES LEFT - Focus on completing what you can", color='yellow'),
        TimerWarning(15, "15 MINUTES LEFT - Finish current task, then validate", color='orange'),
        TimerWarning(10, "10 MINUTES LEFT - Start wrapping up!", color='orange'),
        TimerWarning(5, "5 MINUTES LEFT - Time critical! Validate now!", color='red'),
        TimerWarning(2, "2 MINUTES LEFT - STOP and validate immediately!", color='red'),
        TimerWarning(1, "1 MINUTE LEFT - Submit what you have!", color='red'),
    ]

    def __init__(self, duration_minutes: int = 150,
                 warnings: Optional[List[TimerWarning]] = None,
                 on_expire: Optional[Callable] = None,
                 on_warning: Optional[Callable[[TimerWarning], None]] = None):
        """
        Initialize exam timer.

        Args:
            duration_minutes: Total exam duration in minutes (default: 150 for RHCSA)
            warnings: List of warning configurations
            on_expire: Callback when timer expires
            on_warning: Callback when a warning threshold is reached
        """
        self.duration_minutes = duration_minutes
        self.duration_seconds = duration_minutes * 60
        self.warnings = warnings or self.DEFAULT_WARNINGS
        self.on_expire = on_expire
        self.on_warning = on_warning

        # Anchored to time.monotonic(), NOT the wall clock — exam tasks have
        # the candidate change the system date/time/timezone, and the exam
        # countdown must not jump when they do.
        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.paused_duration: float = 0.0
        self.is_running = False
        self.is_paused = False
        self.is_expired = False

        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._triggered_warnings: set = set()

    def start(self):
        """Start the timer."""
        if self.is_running:
            return

        self.start_time = time.monotonic()
        self.is_running = True
        self.is_expired = False
        self._triggered_warnings.clear()

        # Start background thread for warnings
        self._stop_event.clear()
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def stop(self):
        """Stop the timer."""
        self.is_running = False
        self._stop_event.set()
        if self._timer_thread:
            self._timer_thread.join(timeout=1)

    def pause(self):
        """Pause the timer."""
        if self.is_running and not self.is_paused:
            self.pause_time = time.monotonic()
            self.is_paused = True

    def resume(self):
        """Resume the timer."""
        if self.is_paused and self.pause_time:
            self.paused_duration += time.monotonic() - self.pause_time
            self.pause_time = None
            self.is_paused = False

    def get_elapsed(self) -> timedelta:
        """Get elapsed time."""
        if self.start_time is None:
            return timedelta()

        if self.is_paused and self.pause_time:
            seconds = self.pause_time - self.start_time - self.paused_duration
        else:
            seconds = time.monotonic() - self.start_time - self.paused_duration

        return timedelta(seconds=seconds)

    def get_remaining(self) -> timedelta:
        """Get remaining time."""
        elapsed = self.get_elapsed()
        remaining = timedelta(seconds=self.duration_seconds) - elapsed

        if remaining.total_seconds() < 0:
            return timedelta()
        return remaining

    def get_remaining_minutes(self) -> int:
        """Get remaining time in minutes."""
        return int(self.get_remaining().total_seconds() // 60)

    def get_remaining_formatted(self) -> str:
        """Get remaining time as formatted string (HH:MM:SS)."""
        remaining = self.get_remaining()
        total_seconds = int(remaining.total_seconds())

        if total_seconds < 0:
            return "00:00:00"

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0-100)."""
        elapsed = self.get_elapsed().total_seconds()
        return min(100, (elapsed / self.duration_seconds) * 100)

    def is_time_critical(self) -> bool:
        """Check if we're in time-critical phase (< 15 minutes)."""
        return self.get_remaining_minutes() < 15

    def _timer_loop(self):
        """Background loop to check warnings and expiration."""
        while not self._stop_event.is_set():
            if not self.is_paused:
                remaining_minutes = self.get_remaining_minutes()

                # Check for expiration (in seconds — get_remaining_minutes()
                # floors, which would expire the timer a whole minute early)
                if self.get_remaining().total_seconds() <= 0 and not self.is_expired:
                    self.is_expired = True
                    self.is_running = False
                    if self.on_expire:
                        self.on_expire()
                    break

                # Check for warnings
                for warning in self.warnings:
                    if (remaining_minutes <= warning.minutes_remaining and
                            warning.minutes_remaining not in self._triggered_warnings):
                        self._triggered_warnings.add(warning.minutes_remaining)
                        if self.on_warning:
                            self.on_warning(warning)

            self._stop_event.wait(1)  # Check every second

    def get_status_line(self) -> str:
        """Get a status line for display."""
        remaining = self.get_remaining_formatted()
        remaining_mins = self.get_remaining_minutes()

        if self.is_expired:
            return "TIME EXPIRED!"
        elif self.is_paused:
            return f"PAUSED - {remaining} remaining"
        elif remaining_mins <= 5:
            return f"⚠️  CRITICAL: {remaining} remaining"
        elif remaining_mins <= 15:
            return f"⏰ WARNING: {remaining} remaining"
        else:
            return f"Time: {remaining} remaining"

    def get_progress_bar(self, width: int = 40) -> str:
        """Get a visual progress bar."""
        percentage = self.get_progress_percentage()
        filled = int(width * percentage / 100)
        empty = width - filled

        # Color based on remaining time
        remaining_mins = self.get_remaining_minutes()
        if remaining_mins <= 5:
            bar_char = '█'  # Will be colored red by caller
        elif remaining_mins <= 15:
            bar_char = '█'  # Yellow
        else:
            bar_char = '█'  # Green

        return f"[{bar_char * filled}{'░' * empty}] {percentage:.0f}%"


class TimerDisplay:
    """Handles timer display in terminal."""

    COLORS = {
        'red': '\033[91m',
        'orange': '\033[93m',
        'yellow': '\033[93m',
        'green': '\033[92m',
        'reset': '\033[0m',
        'bold': '\033[1m',
    }

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Add color to text."""
        if color in cls.COLORS:
            return f"{cls.COLORS[color]}{text}{cls.COLORS['reset']}"
        return text

    @classmethod
    def print_warning(cls, warning: TimerWarning):
        """Print a timer warning."""
        border = "=" * 60
        color = cls.COLORS.get(warning.color, '')
        reset = cls.COLORS['reset']

        print(f"\n{color}{border}")
        print(f"⏰  {warning.message}")
        print(f"{border}{reset}\n")

        # Terminal bell if sound enabled
        if warning.sound:
            print('\a', end='')  # Terminal bell

    @classmethod
    def print_expired(cls):
        """Print time expired message."""
        border = "=" * 60
        print(f"\n{cls.COLORS['red']}{border}")
        print("⏰  TIME HAS EXPIRED!")
        print("    Your exam time is up. Please validate your work now.")
        print(f"{border}{cls.COLORS['reset']}\n")
        print('\a\a\a')  # Multiple bells

    @classmethod
    def get_status_display(cls, timer: ExamTimer) -> str:
        """Get formatted status display for timer."""
        remaining = timer.get_remaining_formatted()
        remaining_mins = timer.get_remaining_minutes()

        if timer.is_expired:
            return cls.colorize("TIME EXPIRED!", 'red')
        elif timer.is_paused:
            return cls.colorize(f"⏸ PAUSED - {remaining}", 'yellow')
        elif remaining_mins <= 5:
            return cls.colorize(f"⚠️ {remaining}", 'red')
        elif remaining_mins <= 15:
            return cls.colorize(f"⏰ {remaining}", 'orange')
        elif remaining_mins <= 30:
            return cls.colorize(f"⏱ {remaining}", 'yellow')
        else:
            return cls.colorize(f"⏱ {remaining}", 'green')


def create_exam_timer(duration_minutes: int = 150) -> ExamTimer:
    """
    Create a standard RHCSA exam timer.

    Args:
        duration_minutes: Exam duration (default 150 for RHCSA)

    Returns:
        Configured ExamTimer instance
    """
    def on_warning(warning: TimerWarning):
        TimerDisplay.print_warning(warning)

    def on_expire():
        TimerDisplay.print_expired()

    return ExamTimer(
        duration_minutes=duration_minutes,
        on_warning=on_warning,
        on_expire=on_expire
    )
