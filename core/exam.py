"""
Exam mode orchestrator for RHCSA Simulator v4.0.0

Features:
- Domain-balanced task generation via TaskRegistry.generate_exam()
- ExamTimer integration with warnings
- Reboot simulation with persistence validation
- ResultsDB storage (SQLite)
- Domain breakdown in final report
"""

import time
import logging
from datetime import datetime, timedelta
from config import settings
from tasks.registry import TaskRegistry
from core.validator import get_validator
from core.results_db import get_results_db
from core.reboot_engine import get_reboot_engine
from core.timer import create_exam_timer, TimerDisplay
from utils import formatters as fmt
from utils.helpers import generate_id, format_timedelta, confirm_action


logger = logging.getLogger(__name__)


class ExamSession:
    """
    Exam mode session orchestrator.

    Manages domain-balanced task generation, timer, validation,
    reboot simulation, and ResultsDB persistence.
    """

    def __init__(self, task_count=None, timer_enabled=True, duration_minutes=None, reboot_simulation=None):
        self.task_count = task_count or settings.DEFAULT_EXAM_TASKS
        self.timer_enabled = timer_enabled
        self.duration_minutes = duration_minutes or settings.DEFAULT_EXAM_DURATION
        self.reboot_simulation = reboot_simulation if reboot_simulation is not None else settings.REBOOT_SIMULATION
        self.start_time = None
        self.end_time = None
        self.tasks = []
        self.exam_id = generate_id("exam")
        self.timer = None

    def start(self):
        """Start the exam session."""
        TaskRegistry.initialize()

        self._display_welcome()

        if not confirm_action("Ready to start the exam?", default=True):
            print("Exam cancelled.")
            return None

        # Generate domain-balanced tasks
        print("\nGenerating exam tasks...")
        self.tasks = TaskRegistry.generate_exam(self.task_count)

        if not self.tasks:
            print(fmt.error("Error: Could not generate exam tasks"))
            return None

        print(fmt.success(f"Generated {len(self.tasks)} tasks across {self._count_domains()} domains"))

        self._display_tasks()

        # Start timer
        self.start_time = datetime.now()

        if self.timer_enabled:
            self.timer = create_exam_timer(self.duration_minutes)
            self.timer.start()
            end_time = self.start_time + timedelta(minutes=self.duration_minutes)
            print(f"\n{fmt.warning('Timer started!')} You have {self.duration_minutes} minutes.")
            print(f"Exam ends at: {end_time.strftime('%H:%M:%S')}")
        else:
            print(f"\n{fmt.info('Exam started!')} (No time limit)")

        print("\nComplete the tasks on your system, then return here to validate your work.")
        print("=" * 60)

    def _count_domains(self):
        """Count unique domains in generated tasks."""
        domains = set()
        for task in self.tasks:
            domain = getattr(task, 'exam_domain', 0)
            if domain:
                domains.add(domain)
        return len(domains)

    def _display_welcome(self):
        """Display exam welcome screen."""
        fmt.clear_screen()
        fmt.print_header("RHCSA MOCK EXAM", char='=')

        print(fmt.bold("Exam Information:"))
        print(f"  Tasks: {self.task_count}")
        print(f"  Duration: {self.duration_minutes} minutes" if self.timer_enabled else "  Duration: No time limit")
        print(f"  Pass threshold: {settings.EXAM_PASS_THRESHOLD * 100:.0f}%")
        print(f"  Reboot simulation: {'Enabled' if self.reboot_simulation else 'Disabled'}")
        print()

        print(fmt.bold("Instructions:"))
        print("  1. Read all tasks carefully before starting")
        print("  2. Complete tasks on your Linux system")
        print("  3. Return here when ready to validate")
        print("  4. After validation, a reboot simulation checks persistence")
        print()

        print(fmt.warning("Note: This simulator only validates your work. It does NOT make changes to your system."))
        print()

    def _display_tasks(self):
        """Display all exam tasks."""
        fmt.print_header("EXAM TASKS")

        total_points = sum(task.points for task in self.tasks)

        for i, task in enumerate(self.tasks, 1):
            domain = getattr(task, 'exam_domain', 0)
            domain_name = settings.EXAM_DOMAINS.get(domain, "")
            domain_tag = f" [{domain_name}]" if domain_name else ""
            fmt.print_task(i, task.description, task.points)
            if domain_tag:
                print(fmt.dim(f"      Domain {domain}: {domain_name}"))

        print()
        print(fmt.bold(f"Total Points: {total_points}"))
        print("=" * 60)

    def validate_all(self):
        """Validate all tasks, run reboot simulation, save to ResultsDB."""
        self.end_time = datetime.now()

        # Stop timer
        if self.timer:
            self.timer.stop()

        print()
        fmt.print_header("VALIDATING YOUR WORK")

        validator = get_validator()

        # Phase 1: Initial validation
        validation_results = []
        initial_results_map = {}

        for i, task in enumerate(self.tasks, 1):
            print(f"\nValidating Task {i}/{len(self.tasks)}: {task.id}")
            result = validator.validate_task(task)
            validation_results.append(result)
            initial_results_map[task.id] = result
            self._display_task_result(i, task, result)

        # Calculate initial scores
        total_score, max_score, percentage = validator.calculate_total_score(validation_results)

        # Phase 2: Reboot simulation
        reboot_result = None
        reboot_passed = None

        if self.reboot_simulation:
            print()
            fmt.print_header("REBOOT SIMULATION")
            print("Simulating system reboot to check persistence...")
            print()

            engine = get_reboot_engine()
            reboot_result = engine.simulate_reboot(self.tasks, initial_results_map)

            # Display reboot report
            report = engine.get_reboot_report(reboot_result, self.tasks)
            print(report)

            if not reboot_result.boot_success:
                # Boot failure = automatic fail, score 0
                total_score = 0
                percentage = 0
                reboot_passed = False
            else:
                reboot_passed = True
                # Deduct points for tasks that lost persistence
                for task_id in reboot_result.tasks_lost_points:
                    result = initial_results_map.get(task_id)
                    if result:
                        total_score -= result.score
                percentage = (total_score / max_score * 100) if max_score > 0 else 0

        passed = percentage >= (settings.EXAM_PASS_THRESHOLD * 100)

        # Display final report
        duration = (self.end_time - self.start_time).total_seconds()
        self._display_final_report(
            total_score, max_score, percentage, passed,
            duration, validation_results, reboot_result
        )

        # Save to ResultsDB
        db = get_results_db()
        db.save_exam_result(
            exam_id=self.exam_id,
            start_time=self.start_time.isoformat(),
            end_time=self.end_time.isoformat(),
            duration_seconds=int(duration),
            total_score=total_score,
            max_score=max_score,
            passed=passed,
            reboot_passed=reboot_passed,
            task_count=len(self.tasks),
            mode='exam'
        )

        # Save per-task results
        for task, result in zip(self.tasks, validation_results):
            persistence_passed = None
            if reboot_result and task.id in reboot_result.persistence_results:
                persistence_passed = reboot_result.persistence_results[task.id].passed

            checks_data = [c.to_dict() for c in result.checks] if result.checks else None
            db.save_task_result(
                exam_id=self.exam_id,
                task_id=task.id,
                category=task.category,
                difficulty=task.difficulty,
                domain=getattr(task, 'exam_domain', 0),
                description=task.description,
                score=result.score,
                max_score=result.max_score,
                passed=result.passed,
                persistence_passed=persistence_passed,
                checks=checks_data
            )

        return passed

    def _display_task_result(self, task_num, task, result):
        """Display result for a single task."""
        desc = task.description[:60]
        print(f"\n{fmt.bold(f'Task {task_num}:')} {desc}...")

        for check in result.checks:
            fmt.print_check_result(
                check.name,
                check.passed,
                check.message,
                check.points,
                check.max_points
            )

        status = fmt.success("PASS") if result.passed else fmt.error("FAIL")
        print(f"  Score: {result.score}/{result.max_score} points ({result.percentage:.0f}%) - {status}")

    def _display_final_report(self, total_score, max_score, percentage, passed,
                               duration, validation_results, reboot_result):
        """Display final exam report with domain breakdown."""
        fmt.print_header("EXAM RESULTS")

        # Overall result
        print(fmt.bold("Overall Performance:"))
        print(f"  Total Score: {total_score}/{max_score} points")
        print(f"  Percentage: {percentage:.1f}%")
        tasks_passed = sum(1 for r in validation_results if r.passed)
        print(f"  Tasks Passed: {tasks_passed}/{len(validation_results)}")
        print(f"  Duration: {format_timedelta(timedelta(seconds=int(duration)))}")
        print()

        # Pass/Fail
        threshold_pct = settings.EXAM_PASS_THRESHOLD * 100
        if passed:
            print(fmt.success(f"  PASSED (Required: {threshold_pct:.0f}%)"))
        else:
            print(fmt.error(f"  FAILED (Required: {threshold_pct:.0f}%)"))
        print()

        # Reboot status
        if reboot_result:
            if not reboot_result.boot_success:
                print(fmt.error("  BOOT FAILURE - All points lost"))
            elif reboot_result.tasks_lost_points:
                lost = len(reboot_result.tasks_lost_points)
                print(fmt.warning(f"  {lost} task(s) lost points due to failed persistence"))
            else:
                print(fmt.success("  All persistence checks passed after reboot"))
            print()

        # Domain breakdown
        validator = get_validator()
        task_results = list(zip(self.tasks, validation_results))
        domain_breakdown = validator.get_domain_breakdown(task_results)

        if domain_breakdown:
            print(fmt.bold("Performance by Domain:"))
            for domain_num in sorted(domain_breakdown.keys()):
                stats = domain_breakdown[domain_num]
                pct = stats['percentage']
                name = stats['name']
                print(f"  Domain {domain_num} - {name}: "
                      f"{stats['earned_points']}/{stats['total_points']} pts ({pct:.0f}%)")
            print()

        # Category breakdown
        cat_breakdown = validator.get_category_breakdown(task_results)
        if cat_breakdown:
            print(fmt.bold("Performance by Category:"))
            for category in sorted(cat_breakdown.keys()):
                stats = cat_breakdown[category]
                pct = stats['percentage']
                cat_name = fmt.format_category_name(category)
                print(f"  {cat_name}: {stats['earned_points']}/{stats['total_points']} pts ({pct:.0f}%)")
            print()


def _select_exam_task_count():
    """Prompt user to select exam task count."""
    from utils import formatters as fmt
    print()
    print(fmt.bold("Select number of exam tasks:"))
    print("  1. 20 tasks  — standard (real exam minimum)")
    print("  2. 25 tasks  — full exam (real exam maximum)")
    print("  3. 12 tasks  — quick practice run")
    while True:
        choice = input("\nSelect [1]: ").strip() or '1'
        if choice == '1':
            return 20
        elif choice == '2':
            return 25
        elif choice == '3':
            return 12
        else:
            print(fmt.error("Invalid selection"))


def _select_reboot_simulation():
    """Prompt user to enable or disable reboot simulation."""
    from utils import formatters as fmt
    print()
    print(fmt.bold("Reboot simulation:"))
    print("  1. Enabled   — persistence tasks validated after simulated reboot (recommended)")
    print("  2. Disabled  — skip reboot phase, score initial validation only")
    while True:
        choice = input("\nSelect [1]: ").strip() or '1'
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            print(fmt.error("Invalid selection"))


def run_exam_mode():
    """Run exam mode (convenience function)."""
    task_count = _select_exam_task_count()
    reboot_sim = _select_reboot_simulation()
    session = ExamSession(task_count=task_count, reboot_simulation=reboot_sim)
    session.start()

    if not session.tasks:
        return None

    input("\nPress Enter when you're ready to validate your work...")

    result = session.validate_all()
    return result
