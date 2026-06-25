"""
Output formatting utilities for RHCSA Simulator.
"""

from config import settings


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'

    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


def colorize(text, color_code):
    """
    Colorize text with ANSI color codes.

    Args:
        text (str): Text to colorize
        color_code (str): ANSI color code

    Returns:
        str: Colorized text (or plain if colors disabled)
    """
    if not settings.USE_COLOR:
        return text
    return f"{color_code}{text}{Colors.RESET}"


def success(text):
    """Format text as success (green)."""
    return colorize(text, Colors.GREEN)


def error(text):
    """Format text as error (red)."""
    return colorize(text, Colors.RED)


def warning(text):
    """Format text as warning (yellow)."""
    return colorize(text, Colors.YELLOW)


def info(text):
    """Format text as info (cyan)."""
    return colorize(text, Colors.CYAN)


def bold(text):
    """Format text as bold."""
    if not settings.USE_COLOR:
        return text
    return f"{Colors.BOLD}{text}{Colors.RESET}"


def dim(text):
    """Format text as dim."""
    if not settings.USE_COLOR:
        return text
    return f"{Colors.DIM}{text}{Colors.RESET}"


def print_header(text, width=None, char='='):
    """
    Print a header with decorative lines.

    Args:
        text (str): Header text
        width (int): Width of header (default: terminal width)
        char (str): Character for decorative lines
    """
    if width is None:
        from utils.helpers import get_terminal_width
        width = get_terminal_width()

    print()
    print(colorize(char * width, Colors.CYAN))
    print(colorize(text.center(width), Colors.BOLD + Colors.CYAN))
    print(colorize(char * width, Colors.CYAN))
    print()


def print_section(text):
    """
    Print a section header.

    Args:
        text (str): Section text
    """
    print()
    print(bold(text))
    print("-" * len(text))


def print_task(task_number, description, max_points=None):
    """
    Print a task description.

    Args:
        task_number (int): Task number
        description (str): Task description
        max_points (int): Maximum points for task
    """
    points_str = f" ({max_points} points)" if max_points else ""
    print(f"\n{bold(f'Task {task_number}:')}{points_str}")
    print(description)


def print_check_result(name, passed, message, points=None, max_points=None):
    """
    Print a validation check result.

    Args:
        name (str): Check name
        passed (bool): Whether check passed
        message (str): Result message
        points (int): Points earned
        max_points (int): Maximum points for this check
    """
    if passed:
        symbol = colorize("✓", Colors.GREEN)
        status = success("PASS")
    else:
        symbol = colorize("✗", Colors.RED)
        status = error("FAIL")

    if points is not None and max_points is not None:
        points_str = f" ({points}/{max_points} points)"
    elif points is not None:
        points_str = f" ({points} points)"
    else:
        points_str = ""

    print(f"  {symbol} {message}{points_str}")


def print_result_summary(passed, score, max_score, percentage):
    """
    Print a task result summary.

    Args:
        passed (bool): Whether task passed
        score (int): Score earned
        max_score (int): Maximum score
        percentage (float): Percentage score
    """
    status = success("PASS") if passed else error("FAIL")
    score_text = f"{score}/{max_score} points ({percentage:.0f}%)"

    print()
    print(f"  Score: {score_text} - {status}")
    print()


def print_table(headers, rows, col_widths=None):
    """
    Print a formatted table.

    Args:
        headers (list): List of header strings
        rows (list): List of row lists
        col_widths (list): Optional list of column widths
    """
    if not rows:
        return

    # Calculate column widths if not provided
    if col_widths is None:
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width + 2)  # Add padding

    # Print header
    header_row = "".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(bold(header_row))
    print("-" * sum(col_widths))

    # Print rows
    for row in rows:
        row_str = "".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(row_str)


def print_progress_bar(current, total, width=40, prefix="Progress"):
    """
    Print a progress bar.

    Args:
        current (int): Current progress value
        total (int): Total value
        width (int): Width of progress bar
        prefix (str): Prefix text
    """
    if total == 0:
        percentage = 0
    else:
        percentage = int((current / total) * 100)

    filled = int((current / total) * width) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)

    print(f"\r{prefix}: |{bar}| {percentage}% ({current}/{total})", end="", flush=True)


def print_box(text, width=None, padding=1):
    """
    Print text in a box.

    Args:
        text (str): Text to display in box
        width (int): Width of box (default: text length + padding)
        padding (int): Padding around text
    """
    if width is None:
        width = len(text) + (padding * 2) + 2

    top_bottom = "+" + "-" * (width - 2) + "+"
    padding_line = "|" + " " * (width - 2) + "|"
    text_line = "|" + text.center(width - 2) + "|"

    print(top_bottom)
    for _ in range(padding):
        print(padding_line)
    print(text_line)
    for _ in range(padding):
        print(padding_line)
    print(top_bottom)


def print_menu_option(number, text, description=None):
    """
    Print a menu option.

    Args:
        number (int|str): Option number
        text (str): Option text
        description (str): Optional description
    """
    option = bold(f"{number}.")
    if description:
        print(f"  {option} {text}")
        print(f"     {dim(description)}")
    else:
        print(f"  {option} {text}")


def format_category_name(category):
    """
    Format a category name for display.

    Args:
        category (str): Category identifier (e.g., "users_groups")

    Returns:
        str: Formatted name (e.g., "Users & Groups")
    """
    replacements = {
        'users_groups': 'Users & Groups',
        'essential_tools': 'Essential Tools',
        'permissions': 'Permissions & ACLs',
        'lvm': 'LVM (Logical Volume Management)',
        'filesystems': 'File Systems',
        'networking': 'Networking',
        'selinux': 'SELinux',
        'services': 'Services (systemd)',
        'boot': 'Boot Targets',
        'processes': 'Process Management',
        'scheduling': 'Task Scheduling',
        'containers': 'Containers (Podman)'
    }
    return replacements.get(category, category.replace('_', ' ').title())


def format_difficulty(difficulty):
    """
    Format difficulty level for display.

    Args:
        difficulty (str): Difficulty level

    Returns:
        str: Formatted and colored difficulty
    """
    if difficulty == "easy":
        return success("Easy")
    elif difficulty == "exam":
        return warning("Exam")
    elif difficulty == "hard":
        return error("Hard")
    return difficulty.title()


def clear_screen():
    """Clear the terminal screen."""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')


def print_divider(char="-", width=None):
    """
    Print a divider line.

    Args:
        char (str): Character to use for divider
        width (int): Width of divider (default: terminal width)
    """
    if width is None:
        from utils.helpers import get_terminal_width
        width = get_terminal_width()
    print(char * width)


# ============================================================================
# ENHANCED DISPLAY FUNCTIONS
# ============================================================================

def print_check_result_detailed(name, passed, message, points, max_points,
                                 explanation=None, how_to_fix=None):
    """
    Print a detailed validation check result with explanation.

    Args:
        name: Check name
        passed: Whether check passed
        message: Result message
        points: Points earned
        max_points: Maximum points for this check
        explanation: Optional explanation of what was checked
        how_to_fix: Optional fix suggestion for failures
    """
    if passed:
        symbol = colorize("✓", Colors.GREEN)
        points_color = Colors.GREEN
    else:
        symbol = colorize("✗", Colors.RED)
        points_color = Colors.RED

    points_str = colorize(f"({points}/{max_points} pts)", points_color)

    print(f"  {symbol} {message} {points_str}")

    if explanation:
        print(f"      {dim(explanation)}")

    if not passed and how_to_fix:
        print(f"      {warning('Fix:')} {how_to_fix}")


def print_partial_credit_bar(earned, maximum, width=20):
    """
    Print a visual partial credit bar.

    Args:
        earned: Points earned
        maximum: Maximum points
        width: Bar width
    """
    if maximum == 0:
        percentage = 0
    else:
        percentage = earned / maximum

    filled = int(width * percentage)
    empty = width - filled

    # Color based on percentage
    if percentage >= 0.7:
        bar_color = Colors.GREEN
    elif percentage >= 0.4:
        bar_color = Colors.YELLOW
    else:
        bar_color = Colors.RED

    bar = colorize("█" * filled, bar_color) + dim("░" * empty)
    pct_str = f"{percentage*100:.0f}%"

    print(f"    [{bar}] {earned}/{maximum} ({pct_str})")


def print_task_result_card(task_id, category, passed, score, max_score, checks):
    """
    Print a detailed task result card.

    Args:
        task_id: Task identifier
        category: Task category
        passed: Whether task passed
        score: Score earned
        max_score: Maximum score
        checks: List of (name, passed, points, max_points) tuples
    """
    status = success("PASSED") if passed else error("FAILED")
    percentage = (score / max_score * 100) if max_score > 0 else 0

    print()
    print(f"┌{'─' * 58}┐")
    print(f"│ {bold(task_id):<40} {status:>15} │")
    print(f"│ {dim(format_category_name(category)):<56} │")
    print(f"├{'─' * 58}┤")

    for check_name, check_passed, points, max_points in checks:
        symbol = success("✓") if check_passed else error("✗")
        pts = f"{points}/{max_points}"
        # Truncate check name if too long
        name_display = check_name[:35] + "..." if len(check_name) > 38 else check_name
        print(f"│   {symbol} {name_display:<40} {pts:>10} │")

    print(f"├{'─' * 58}┤")
    print(f"│ {'Total Score:':<45} {bold(f'{score}/{max_score}'):>10} │")
    print(f"│ {'Percentage:':<45} {bold(f'{percentage:.0f}%'):>10} │")
    print(f"└{'─' * 58}┘")


def print_recommendation_card(recommendation):
    """
    Print a recommendation card.

    Args:
        recommendation: Dict with type, target, reason, priority, suggestion
    """
    priority = recommendation.get('priority', 'medium')

    if priority == 'high':
        border_color = Colors.RED
        priority_badge = error("[HIGH]")
    elif priority == 'medium':
        border_color = Colors.YELLOW
        priority_badge = warning("[MEDIUM]")
    else:
        border_color = Colors.GREEN
        priority_badge = success("[LOW]")

    print()
    print(colorize(f"┌{'─' * 56}┐", border_color))
    print(colorize(f"│", border_color) + f" {priority_badge} {recommendation.get('suggestion', '')[:43]:<43}" + colorize(" │", border_color))
    print(colorize(f"│", border_color) + f" {dim(recommendation.get('reason', '')[:54]):<54}" + colorize(" │", border_color))
    print(colorize(f"└{'─' * 56}┘", border_color))


def print_scenario_progress(scenario_title, current_step, total_steps, earned_points, total_points):
    """
    Print scenario progress display.

    Args:
        scenario_title: Title of the scenario
        current_step: Current step number
        total_steps: Total number of steps
        earned_points: Points earned so far
        total_points: Total possible points
    """
    step_pct = (current_step / total_steps * 100) if total_steps > 0 else 0
    points_pct = (earned_points / total_points * 100) if total_points > 0 else 0

    print()
    print(f"┌{'─' * 58}┐")
    print(f"│ {bold(scenario_title):<56} │")
    print(f"├{'─' * 58}┤")
    print(f"│ Step Progress: {current_step}/{total_steps} ({step_pct:.0f}%){' ' * 27} │")

    # Step progress bar
    step_filled = int(40 * current_step / total_steps) if total_steps > 0 else 0
    step_bar = success("█" * step_filled) + dim("░" * (40 - step_filled))
    print(f"│   [{step_bar}]   │")

    print(f"│ Points: {earned_points}/{total_points} ({points_pct:.0f}%){' ' * 33} │")

    # Points progress bar
    points_filled = int(40 * earned_points / total_points) if total_points > 0 else 0
    if points_pct >= 70:
        points_bar = success("█" * points_filled)
    elif points_pct >= 50:
        points_bar = warning("█" * points_filled)
    else:
        points_bar = error("█" * points_filled)
    points_bar += dim("░" * (40 - points_filled))
    print(f"│   [{points_bar}]   │")

    print(f"└{'─' * 58}┘")


def print_weak_area_summary(weak_areas):
    """
    Print a summary of weak areas.

    Args:
        weak_areas: List of dicts with category, success_rate, attempts, failures
    """
    if not weak_areas:
        print(success("No significant weak areas detected!"))
        return

    print()
    print(bold("Areas Needing Improvement:"))
    print()

    for area in weak_areas:
        cat = format_category_name(area['category'])
        rate = area['success_rate'] * 100
        attempts = area['attempts']
        failures = area['failures']

        # Color based on success rate
        if rate >= 70:
            rate_str = success(f"{rate:.0f}%")
        elif rate >= 50:
            rate_str = warning(f"{rate:.0f}%")
        else:
            rate_str = error(f"{rate:.0f}%")

        print(f"  • {cat}")
        print(f"    Success Rate: {rate_str} ({attempts} attempts, {failures} failures)")

        # Visual bar
        bar_width = 30
        filled = int(bar_width * area['success_rate'])
        bar = ("█" * filled) + ("░" * (bar_width - filled))
        if rate >= 70:
            bar = success(bar)
        elif rate >= 50:
            bar = warning(bar)
        else:
            bar = error(bar)
        print(f"    [{bar}]")
        print()


def print_explanation(check_name, passed, explanation_data):
    """
    Print a detailed explanation for a check result.

    Args:
        check_name: Name of the check
        passed: Whether check passed
        explanation_data: Dict with explanation, how_checked, why_matters, common_issues
    """
    print()
    header = success("✓ Why this passed:") if passed else error("✗ Why this failed:")
    print(f"  {header}")

    if 'explanation' in explanation_data:
        print(f"    {explanation_data['explanation']}")

    if 'how_checked' in explanation_data and explanation_data['how_checked']:
        print(f"    {dim('Verified by:')} {explanation_data['how_checked']}")

    if 'why_matters' in explanation_data and explanation_data['why_matters']:
        print(f"    {dim('Why it matters:')} {explanation_data['why_matters']}")

    if not passed and 'common_issues' in explanation_data:
        print(f"    {warning('Common issues:')}")
        for issue in explanation_data['common_issues']:
            print(f"      • {issue}")


def print_diff(expected, actual, label="Configuration"):
    """
    Print a diff-style comparison.

    Args:
        expected: Expected content/value
        actual: Actual content/value
        label: Label for the comparison
    """
    print()
    print(f"  {bold(label)} Comparison:")
    print(f"    {error('- Expected:')} {expected}")
    print(f"    {success('+ Actual:  ')} {actual}")


def print_timer_status(remaining_str, is_critical=False, is_warning=False):
    """
    Print timer status.

    Args:
        remaining_str: Formatted remaining time string
        is_critical: True if time is critical (< 5 min)
        is_warning: True if time is warning (< 15 min)
    """
    if is_critical:
        icon = "⚠️ "
        time_display = error(remaining_str)
    elif is_warning:
        icon = "⏰ "
        time_display = warning(remaining_str)
    else:
        icon = "⏱  "
        time_display = success(remaining_str)

    print(f"  {icon}{time_display} remaining")


def page_output(text: str) -> None:
    """
    Display text through less if it is taller than the terminal.
    Preserves ANSI color codes (-R), exits immediately if content
    fits on one screen (-F), and does not clear the screen on exit (-X).
    Falls back to plain print if less is not available.
    """
    import os
    import subprocess
    pager = os.environ.get('PAGER', 'less')
    try:
        proc = subprocess.Popen(
            [pager, '-R', '-F', '-X'],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=text.encode('utf-8', errors='replace'))
    except (FileNotFoundError, OSError):
        print(text)
