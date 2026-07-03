#!/usr/bin/env python3
"""
RHCSA EX200 v10 Exam Simulator v4.0.0 - Main Entry Point

Features:
- 188 tasks across 25 categories, 8 EX200 v10 domains
- SM-2 spaced repetition for adaptive practice
- Reboot simulation with persistence validation
- SQLite-backed progress tracking (ResultsDB)
"""

import sys
import os
import logging
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f'{settings.APP_NAME} v{settings.VERSION}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Start Examples:
  %(prog)s --quick              5 random tasks
  %(prog)s --quick lvm          5 LVM tasks
  %(prog)s --exam               Full mock exam with reboot sim
  %(prog)s --learn              Domain-based study mode
  %(prog)s --practice lvm       Practice LVM category
  %(prog)s --adaptive           SM-2 driven weak-area practice
        """
    )

    parser.add_argument('--quick', nargs='?', const='all', metavar='CATEGORY',
                        help='Quick practice (5 tasks). Optionally specify category.')
    parser.add_argument('--exam', action='store_true',
                        help='Start mock exam immediately')
    parser.add_argument('--learn', nargs='?', const='all', metavar='CATEGORY',
                        help='Learn mode. Optionally specify category.')
    parser.add_argument('--practice', metavar='CATEGORY',
                        help='Start practice mode for a category')
    parser.add_argument('--adaptive', action='store_true',
                        help='Start adaptive practice (SM-2 driven)')
    parser.add_argument('--list-categories', action='store_true',
                        help='List available categories and domains')
    parser.add_argument('--export-code', action='store_true',
                        help='Print a portable progress code (backup) and exit')
    parser.add_argument('--import-code', metavar='CODE',
                        help='Restore progress from a code (use "-" to read from stdin)')
    parser.add_argument('--import-mode', choices=['replace', 'merge'],
                        default='replace',
                        help='How --import-code applies (default: replace)')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {settings.VERSION}')

    return parser.parse_args()


def run_quick_practice(category=None):
    """Run quick practice - 5 tasks with ResultsDB tracking."""
    from tasks.registry import TaskRegistry
    from core.validator import get_validator
    from core.results_db import get_results_db
    from core import task_env
    from utils import formatters as fmt
    from utils.helpers import confirm_action

    TaskRegistry.initialize()
    db = get_results_db()

    fmt.clear_screen()
    fmt.print_header("QUICK PRACTICE")

    if category and category != 'all':
        print(f"5 {fmt.format_category_name(category)} tasks.")
    else:
        print("5 random tasks across all categories.")
    print()

    if not confirm_action("Ready to start?", default=True):
        return

    # Get tasks
    if category and category != 'all':
        tasks = TaskRegistry.get_practice_tasks(category, 'exam', 5)
    else:
        tasks = TaskRegistry.get_exam_tasks(5)

    if not tasks:
        print(fmt.error("Could not generate tasks"))
        return

    validator = get_validator()
    completed = 0
    passed = 0

    # Put the box into the same real state exam/practice/adaptive modes do:
    # fresh practice disks + no leftover artifacts up front, then inject each
    # task's fault / negative precondition per iteration (and reverse it after).
    # Without this, quick practice validates against default state — troubleshooting
    # tasks have nothing to fix and positive-config tasks pass with no work done.
    print(fmt.dim("Preparing a clean practice environment..."))
    task_env.session_reset()

    for i, task in enumerate(tasks, 1):
        # Break something to fix / establish the precondition BEFORE the candidate
        # works on it. Wipe screen after so setup chatter doesn't precede the task.
        env_state = task_env.setup_task(task)
        stop = False
        try:
            fmt.clear_screen()
            print(f"Quick Practice - Task {i}/{len(tasks)}")
            print("=" * 60)
            print()
            print(fmt.bold("Task:"))
            print(task.description)
            print()

            cat_name = fmt.format_category_name(task.category)
            domain = getattr(task, 'exam_domain', 0)
            domain_name = settings.EXAM_DOMAINS.get(domain, "")
            print(fmt.bold(f"Category: {cat_name} [D{domain}]"))
            if domain_name:
                print(fmt.bold(f"Domain: {domain_name}"))
            print(fmt.bold(f"Points: {task.points}"))
            print()

            if task.hints and confirm_action("Show hints?", default=False):
                print()
                for j, hint in enumerate(task.hints, 1):
                    print(f"  {j}. {hint}")
                print()

            input("Complete the task, then press Enter to validate...")

            result = validator.validate_task(task)
            completed += 1

            print()
            if result.passed:
                passed += 1
                print(fmt.success(f"PASSED - {result.score}/{result.max_score} points"))
            else:
                print(fmt.error(f"FAILED - {result.score}/{result.max_score} points"))
                for check in result.checks:
                    if not check.passed:
                        print(f"    - {check.message}")

            # Save to ResultsDB
            db.save_practice_attempt(
                task_id=task.id,
                category=task.category,
                difficulty=task.difficulty,
                domain=getattr(task, 'exam_domain', 0),
                score=result.score,
                max_score=result.max_score,
                passed=result.passed,
                mode='quick'
            )

            # Show exam tips
            exam_tips = getattr(task, 'exam_tips', [])
            if exam_tips:
                print()
                print(fmt.bold("Exam Tips:"))
                for tip in exam_tips:
                    print(f"  * {tip}")

            print()
            stop = i < len(tasks) and not confirm_action("Continue to next task?", default=True)
        finally:
            # Always reverse this task's system changes, even on error / early
            # exit, then wipe practice disks if the task consumed one.
            print(fmt.dim("Restoring system..."))
            task_env.teardown_task(task, env_state)
            task_env.reset_after_task(task)

        if stop:
            break

    # Summary
    print()
    fmt.print_header("QUICK PRACTICE COMPLETE")
    print(f"Tasks completed: {completed}/{len(tasks)}")
    print(f"Tasks passed: {passed}/{completed}")
    if completed > 0:
        print(f"Success rate: {passed / completed * 100:.0f}%")
    print()


def main():
    """Main application entry point."""
    from utils.logging import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()

    # Handle --list-categories without root
    if args.list_categories:
        from tasks.registry import TaskRegistry
        TaskRegistry.initialize()

        print(f"\n{settings.APP_NAME} v{settings.VERSION}")
        print(f"Available categories ({TaskRegistry.get_task_count()} tasks total):\n")

        for domain_num in sorted(settings.EXAM_DOMAINS.keys()):
            domain_name = settings.EXAM_DOMAINS[domain_num]
            domain_cats = [
                cat for cat, dom in settings.CATEGORY_TO_DOMAIN.items()
                if dom == domain_num and cat in TaskRegistry.get_all_categories()
            ]
            if domain_cats:
                print(f"  Domain {domain_num}: {domain_name}")
                for cat in sorted(domain_cats):
                    count = TaskRegistry.get_task_count(cat)
                    print(f"    {cat}: {count} tasks")
                print()
        return 0

    # Progress snapshot codes — operate only on the local results DB, so they
    # run without the full root/system checks (handy for scripting a snapshot
    # save/restore around a VM revert or reinstall).
    if getattr(args, 'export_code', False):
        from core import progress_code
        try:
            print(progress_code.export_code())
            return 0
        except Exception as e:
            print(f"Error exporting progress code: {e}", file=sys.stderr)
            return 1

    if getattr(args, 'import_code', None):
        from core import progress_code
        code = args.import_code
        if code == '-':
            code = sys.stdin.read()
        try:
            counts, summary = progress_code.import_code(
                code, mode=getattr(args, 'import_mode', 'replace'))
        except progress_code.ProgressCodeError as e:
            print(f"Invalid progress code: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error importing progress code: {e}", file=sys.stderr)
            return 1
        print(f"Imported ({args.import_mode}): {counts['exams']} exams, "
              f"{counts['tasks']} exam tasks, {counts['practice']} attempts, "
              f"{counts['weak']} categories.")
        return 0

    # Check root privileges
    try:
        from utils.helpers import require_root
        require_root()
    except SystemExit:
        return 1

    # Best-effort: capture a known-good /etc/fstab baseline so the fstab guard
    # (tools/rhcsa-fstab-guard.sh) can strip leftover practice/fault entries if a
    # session is ever interrupted. Only captures when none exists and fstab is
    # clean; never fails the launch.
    try:
        import subprocess as _sp
        _guard = '/usr/local/sbin/rhcsa-fstab-guard.sh'
        if os.path.exists(_guard):
            _sp.run([_guard, 'ensure'], capture_output=True, timeout=15)
    except Exception:
        pass

    # Preflight: warn about exam-relevant packages (httpd, vsftpd, nfs-utils,
    # ...) that aren't installed, so a task that assumes one is present
    # doesn't silently fail to set up its scenario. Best-effort, never fails
    # the launch.
    try:
        from core import preflight
        preflight.warn_missing()
    except Exception:
        pass

    # CLI quick modes
    if args.quick:
        run_quick_practice(args.quick)
        return 0

    if args.exam:
        from core.exam import run_exam_mode
        run_exam_mode()
        return 0

    if args.learn:
        from core.learn import run_learn_mode
        if args.learn != 'all':
            from tasks.registry import TaskRegistry
            TaskRegistry.initialize()
            if args.learn in TaskRegistry.get_all_categories():
                run_learn_mode(category=args.learn)
            else:
                print(f"Unknown category: {args.learn}")
                print("Use --list-categories to see available categories")
                return 1
        else:
            run_learn_mode()
        return 0

    if args.practice:
        from tasks.registry import TaskRegistry
        TaskRegistry.initialize()
        if args.practice in TaskRegistry.get_all_categories():
            from core.practice import PracticeSession
            session = PracticeSession()
            session.category = args.practice
            session.difficulty = 'exam'
            session.start()
        else:
            print(f"Unknown category: {args.practice}")
            print("Use --list-categories to see available categories")
            return 1
        return 0

    if args.adaptive:
        from core.adaptive import run_adaptive_mode
        run_adaptive_mode()
        return 0

    # Warn if a troubleshooting fault was left active (e.g. simulator crashed)
    try:
        from tasks.troubleshooting import load_fault_state
        stale = load_fault_state()
        if stale:
            from utils import formatters as fmt
            print(fmt.warning(
                f"\n! Active fault detected from a previous session: {stale.get('task_id')}"
            ))
            print(fmt.warning("  Run System Reset to restore the system, or it will be"))
            print(fmt.warning("  restored automatically when the next troubleshooting task ends.\n"))
    except Exception:
        pass

    # Interactive menu mode
    from core.menu import MenuSystem
    from core.exam import run_exam_mode
    from core.practice import run_practice_mode
    from core.learn import run_learn_mode
    from core.adaptive import run_adaptive_mode

    menu = MenuSystem()

    while True:
        try:
            choice = menu.display_main_menu()

            if choice == 'learn':
                run_learn_mode()

            elif choice == 'quick_practice':
                run_quick_practice()
                input("\nPress Enter to return to menu...")

            elif choice == 'exam':
                run_exam_mode()
                input("\nPress Enter to return to menu...")

            elif choice == 'practice':
                run_practice_mode()
                input("\nPress Enter to return to menu...")

            elif choice == 'adaptive':
                run_adaptive_mode()

            elif choice == 'dashboard':
                menu.show_dashboard()

            elif choice == 'export':
                menu.export_report()

            elif choice == 'history':
                menu.show_result_history()

            elif choice == 'snapshot':
                menu.progress_snapshot()

            elif choice == 'setup':
                menu.show_setup()

            elif choice == 'help':
                menu.show_help()

            elif choice == 'exit':
                print(f"\nThank you for using {settings.APP_NAME}!")
                print("Good luck with your certification!")
                return 0

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            confirm = input("Are you sure you want to exit? [y/N]: ").strip().lower()
            if confirm in ['y', 'yes']:
                return 0

        except Exception as e:
            logger.exception("Unexpected error in main loop")
            print(f"\nError: {e}")
            print("Please report this issue if it persists.")
            input("Press Enter to return to menu...")


if __name__ == '__main__':
    sys.exit(main())
