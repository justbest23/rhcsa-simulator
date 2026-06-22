"""
Practice mode for RHCSA Simulator v4.0.0

Features:
- ResultsDB tracking with SM-2 updates
- Exam tips display after task completion
- Domain info alongside category
- Retry with solution hints
"""

import logging
from tasks.registry import TaskRegistry
from core.validator import get_validator
from core.results_db import get_results_db
from utils import formatters as fmt
from utils.helpers import confirm_action
from config import settings


logger = logging.getLogger(__name__)


class PracticeSession:
    """Practice mode session with ResultsDB tracking."""

    def __init__(self):
        self.category = None
        self.difficulty = "exam"
        self.task_count = settings.DEFAULT_PRACTICE_TASKS
        self.skip_reboot = False

    def start(self):
        """Start practice session."""
        TaskRegistry.initialize()

        self.category = self._select_category()
        if not self.category:
            return

        self.difficulty = self._select_difficulty()
        self.skip_reboot = self._select_reboot_filter()

        tasks = TaskRegistry.get_practice_tasks(
            self.category,
            self.difficulty,
            self.task_count,
            skip_reboot=self.skip_reboot,
        )

        if not tasks:
            print(fmt.error(f"No tasks available for {self.category} with current filters"))
            return

        label = " [no-reboot mode]" if self.skip_reboot else ""
        print(fmt.info(f"\nStarting {len(tasks)}-task practice session{label}"))

        # Practice each task
        try:
            for i, task in enumerate(tasks, 1):
                self._run_practice_task(task, i, len(tasks))
            print(fmt.success("\nPractice session complete!"))
        except StopIteration:
            print(fmt.info("\nPractice session ended early."))

    def _select_category(self):
        """Select practice category."""
        fmt.clear_screen()
        fmt.print_header("PRACTICE MODE - Select Category")

        categories = TaskRegistry.get_all_categories()

        if not categories:
            print(fmt.error("No task categories available"))
            return None

        for i, cat in enumerate(sorted(categories), 1):
            count = TaskRegistry.get_task_count(cat)
            domain = settings.CATEGORY_TO_DOMAIN.get(cat, "?")
            domain_name = settings.EXAM_DOMAINS.get(domain, "")
            label = f"{fmt.format_category_name(cat)} [D{domain}]"
            fmt.print_menu_option(i, label, f"{count} tasks")

        fmt.print_menu_option('Q', "Quit", "Return to main menu")

        while True:
            choice = input("\nSelect category (number or Q): ").strip()

            if choice.lower() == 'q':
                return None

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(categories):
                    return sorted(categories)[idx]
                else:
                    print(fmt.error("Invalid selection"))
            except ValueError:
                print(fmt.error("Please enter a number or Q"))

    def _select_difficulty(self):
        """Select difficulty level."""
        print()
        print(fmt.bold("Select Difficulty:"))
        fmt.print_menu_option(1, "Easy", "Simpler tasks")
        fmt.print_menu_option(2, "Exam", "Exam-level difficulty (recommended)")
        fmt.print_menu_option(3, "Hard", "Challenging tasks")

        while True:
            choice = input("\nSelect difficulty [2]: ").strip() or '2'

            if choice == '1':
                return 'easy'
            elif choice == '2':
                return 'exam'
            elif choice == '3':
                return 'hard'
            else:
                print(fmt.error("Invalid selection"))

    def _select_reboot_filter(self):
        """Ask whether to exclude tasks that require rebooting the system."""
        print()
        print(fmt.bold("Reboot-required tasks:"))
        fmt.print_menu_option(1, "Include all tasks", "Including tasks that require a system reboot (recommended for full exam prep)")
        fmt.print_menu_option(2, "Skip reboot tasks", "Exclude tasks that require rebooting — safe for a live system you're actively using")

        while True:
            choice = input("\nSelect [1]: ").strip() or '1'
            if choice == '1':
                return False
            elif choice == '2':
                return True
            else:
                print(fmt.error("Invalid selection"))

    def _run_practice_task(self, task, current, total):
        """Run a single practice task with ResultsDB tracking."""
        attempt = 1
        db = get_results_db()

        while True:
            fmt.clear_screen()
            print(f"Practice Task {current}/{total}" + (f" (Attempt {attempt})" if attempt > 1 else ""))
            print("=" * 60)
            print()

            # Display task with domain info
            print(fmt.bold("Task:"))
            print(task.description)
            print()
            print(fmt.bold(f"Category: {fmt.format_category_name(task.category)}"))
            domain = getattr(task, 'exam_domain', 0)
            domain_name = settings.EXAM_DOMAINS.get(domain, "")
            if domain_name:
                print(fmt.bold(f"Domain: {domain} - {domain_name}"))
            print(fmt.bold(f"Points: {task.points}"))
            print(fmt.bold(f"Difficulty: {fmt.format_difficulty(task.difficulty)}"))
            persistence = getattr(task, 'requires_persistence', False)
            if persistence:
                print(fmt.info("  Requires persistence (survives reboot)"))
            print()

            # Show hints
            if task.hints and confirm_action("Show hints?", default=False):
                print()
                print(fmt.bold("Hints:"))
                for i, hint in enumerate(task.hints, 1):
                    print(f"  {i}. {hint}")
                print()

            input("Complete this task on your system, then press Enter to validate...")

            # Validate
            validator = get_validator()
            result = validator.validate_task(task)

            # Display result
            print()
            print(fmt.bold("Validation Results:"))
            print("=" * 60)
            for check in result.checks:
                fmt.print_check_result(
                    check.name,
                    check.passed,
                    check.message,
                    check.points,
                    check.max_points
                )
                if not check.passed:
                    self._show_fix_suggestion(check, task)

            print("=" * 60)
            fmt.print_result_summary(result.passed, result.score, result.max_score, result.percentage)

            # Save to ResultsDB (triggers SM-2 update)
            db.save_practice_attempt(
                task_id=task.id,
                category=task.category,
                difficulty=task.difficulty,
                domain=getattr(task, 'exam_domain', 0),
                score=result.score,
                max_score=result.max_score,
                passed=result.passed,
                mode='practice'
            )

            # Show exam tips
            exam_tips = getattr(task, 'exam_tips', [])
            if exam_tips:
                print()
                print(fmt.bold("Exam Tips:"))
                for tip in exam_tips:
                    print(f"  * {tip}")

            if not result.passed:
                print()
                print(fmt.bold("Options:"))
                print("  R - Retry this task")
                print("  S - Show solution hints")
                print("  C - Continue to next task")
                print("  Q - Quit practice session")
                print()

                choice = input("Select option [R]: ").strip().lower() or 'r'

                if choice == 'r':
                    attempt += 1
                    continue
                elif choice == 's':
                    self._show_solution(task)
                    retry = confirm_action("Try again?", default=True)
                    if retry:
                        attempt += 1
                        continue
                    else:
                        break
                elif choice == 'q':
                    raise StopIteration
                else:
                    break
            else:
                print(fmt.success("\nGreat job!"))
                input("Press Enter to continue...")
                break

        if current < total:
            if not confirm_action("Continue to next task?", default=True):
                raise StopIteration

    def _show_fix_suggestion(self, check, task):
        """Show specific suggestions for fixing failed checks."""
        suggestions = {
            "user_exists": "useradd -m USERNAME",
            "correct_uid": "usermod -u UID USERNAME",
            "correct_groups": "usermod -aG group1,group2 USERNAME",
            "permissions": "chmod OCTAL file",
            "service_active": "systemctl start SERVICE",
            "service_enabled": "systemctl enable SERVICE",
        }
        if check.name in suggestions:
            print(f"   How to fix: {suggestions[check.name]}")

    def _show_solution(self, task):
        """Show all hints as solution."""
        print()
        print("=" * 60)
        print("SOLUTION / HINTS")
        print("=" * 60)
        if task.hints:
            for i, hint in enumerate(task.hints, 1):
                print(f"  {i}. {hint}")
        exam_tips = getattr(task, 'exam_tips', [])
        if exam_tips:
            print()
            print("EXAM TIPS:")
            for tip in exam_tips:
                print(f"  * {tip}")
        print("=" * 60)
        print()


def run_practice_mode():
    """Run practice mode (convenience function)."""
    session = PracticeSession()
    session.start()
