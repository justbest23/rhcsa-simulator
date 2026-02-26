"""
Main menu system for RHCSA Simulator v4.0.0

Streamlined 9-option interface with ResultsDB dashboard.
"""

import sys
from utils import formatters as fmt
from config import settings


class MenuSystem:
    """
    Main menu system for the application.

    v4.0.0 Features:
    - 9-option menu aligned with EX200 v10 domains
    - SM-2 adaptive mode integration
    - ResultsDB-powered dashboard
    """

    def display_main_menu(self):
        """Display main menu and get selection."""
        while True:
            fmt.clear_screen()
            self._print_header()

            # Quick Start section
            print(fmt.bold("QUICK START"))
            fmt.print_menu_option('Q', "Quick Practice", "5 random tasks")
            fmt.print_menu_option('E', "Mock Exam", f"{settings.DEFAULT_EXAM_TASKS} tasks, {settings.DEFAULT_EXAM_DURATION} min, reboot sim")
            print()

            # Learn & Practice section
            print(fmt.bold("LEARN & PRACTICE"))
            fmt.print_menu_option(1, "Learn Mode", "Domain-based study with SM-2 indicators")
            fmt.print_menu_option(2, "Practice Mode", "Category-focused with retry & hints")
            fmt.print_menu_option(3, "Adaptive Mode", "SM-2 driven weak-area practice")
            print()

            # Progress section
            print(fmt.bold("PROGRESS"))
            fmt.print_menu_option(4, "Dashboard", "Stats, history & weak areas")
            fmt.print_menu_option(5, "Export Report", "Generate progress report")
            print()

            # Footer
            print(fmt.dim("-" * 50))
            print(fmt.dim("  [S] Setup  [?] Help  [0] Exit"))
            print()

            choice = input("Select option: ").strip().lower()

            if choice == 'q':
                return 'quick_practice'
            elif choice == 'e':
                return 'exam'
            elif choice == '1':
                return 'learn'
            elif choice == '2':
                return 'practice'
            elif choice == '3':
                return 'adaptive'
            elif choice == '4':
                return 'dashboard'
            elif choice == '5':
                return 'export'
            elif choice == 's':
                return 'setup'
            elif choice in ('?', 'h'):
                return 'help'
            elif choice == '0':
                return 'exit'
            else:
                print(fmt.error("Invalid selection."))
                input("Press Enter to continue...")

    def _print_header(self):
        """Print application header."""
        fmt.print_header(f"{settings.APP_NAME} v{settings.VERSION}")

    def show_dashboard(self):
        """Show unified progress dashboard using ResultsDB."""
        from core.results_db import get_results_db

        db = get_results_db()

        fmt.clear_screen()
        fmt.print_header("PROGRESS DASHBOARD")

        # Overall Stats
        exam_count = db.get_exam_count()
        practice_count = db.get_practice_count()
        all_stats = db.get_all_category_stats()

        total_attempts = sum(s['attempts'] for s in all_stats) if all_stats else 0
        total_passes = sum(s['passes'] for s in all_stats) if all_stats else 0
        overall_rate = (total_passes / total_attempts * 100) if total_attempts > 0 else 0

        print(fmt.bold("Overall Performance"))
        print(f"  Exams Taken: {exam_count}")
        print(f"  Practice Attempts: {practice_count}")
        print(f"  Categories Practiced: {len(all_stats)}")
        print(f"  Overall Success Rate: {overall_rate:.0f}%")
        print()

        # Recent Exams
        recent = db.get_recent_exams(5)
        if recent:
            print(fmt.bold("Recent Exams"))
            for r in recent:
                date = r['start_time'][:10] if r['start_time'] else "Unknown"
                pct = r['percentage']
                status = fmt.success("PASS") if r['passed'] else fmt.error("FAIL")
                reboot = ""
                if r['reboot_passed'] is not None:
                    reboot = fmt.success(" [Reboot OK]") if r['reboot_passed'] else fmt.error(" [Boot FAIL]")
                print(f"  {date} - {pct:.0f}% {status}{reboot}")
            print()

        # Weak Areas
        weak = db.get_weak_categories(0.7)
        if weak:
            print(fmt.bold("Weak Areas (below 70%)"))
            for w in weak[:5]:
                cat_name = fmt.format_category_name(w['category'])
                rate = w['success_rate'] * 100
                attempts = w['attempts']
                print(f"  - {cat_name}: {rate:.0f}% ({attempts} attempts)")
            print()

        # Due for Review
        due = db.get_due_categories()
        if due:
            print(fmt.bold(f"Due for Review ({len(due)} categories)"))
            for d in due[:5]:
                cat_name = fmt.format_category_name(d['category'])
                print(f"  - {cat_name}")
            print()

        # Persistence Failures
        pf = db.get_persistence_failure_tasks()
        if pf:
            print(fmt.bold("Frequent Persistence Failures"))
            for p in pf[:3]:
                print(f"  - {p['task_id']} ({p['category']}) - {p['failures']} failures")
            print()

        if not recent and not all_stats:
            print(fmt.info("No data yet. Start practicing to see your progress!"))
            print()

        print(fmt.dim("Press Enter to return..."))
        input()

    def show_help(self):
        """Display help information."""
        fmt.clear_screen()
        fmt.print_header("HELP")

        help_text = f"""
{settings.APP_NAME} v{settings.VERSION} - Quick Guide

QUICK START
  Q - Quick Practice: 5 random tasks with validation.
      Perfect for daily practice sessions.

  E - Mock Exam: {settings.DEFAULT_EXAM_TASKS}-task exam with {settings.DEFAULT_EXAM_DURATION}-min timer.
      Domain-balanced, includes reboot simulation.

LEARN & PRACTICE
  1. Learn Mode - Study EX200 v10 domains with explanations,
     commands, exam tips. SM-2 indicators show weak areas.
  2. Practice Mode - Pick a category, choose difficulty,
     get instant feedback with retry & solution hints.
  3. Adaptive Mode - SM-2 selects your weakest/due categories.
     Difficulty adjusts to your performance. Best for review.

PROGRESS
  4. Dashboard - View exam history, success rates, weak areas,
     spaced repetition due dates, persistence failures.
  5. Export Report - Generate a progress report.

EXAM DOMAINS (EX200 v10)
  1. Software Management    2. System Setup & Boot
  3. Users & Permissions    4. Storage & Filesystems
  5. Network & DNS          6. Systemd & Services
  7. SELinux & Firewall     8. Automation & Scripting
  9. Container Management

TIPS
  - Run as root (sudo) for full functionality
  - Practice daily for best results - SM-2 will schedule reviews
  - Adaptive mode is the most effective for exam prep
  - Persistence tasks require config that survives reboot

For RHCSA exam info: https://www.redhat.com/rhcsa
        """

        print(help_text)
        input("Press Enter to return to menu...")

    def show_setup(self):
        """Show setup and configuration options."""
        fmt.clear_screen()
        fmt.print_header("SETUP")

        print(fmt.bold("Options"))
        print("  1. Setup Practice Disks (loop devices for LVM)")
        print("  2. View Task Statistics")
        print("  3. Network Backup/Restore")
        print("  0. Return to Menu")
        print()

        choice = input("Select option: ").strip()

        if choice == '1':
            self.setup_practice_disks()
        elif choice == '2':
            self.show_stats()
        elif choice == '3':
            self.network_management()

    def show_stats(self):
        """Show task statistics."""
        from tasks.registry import TaskRegistry

        fmt.clear_screen()
        fmt.print_header("TASK STATISTICS")

        TaskRegistry.initialize()
        TaskRegistry.print_statistics()

        print()
        input("Press Enter to return...")

    def export_report(self):
        """Export progress report."""
        from core.results_db import get_results_db

        fmt.clear_screen()
        fmt.print_header("EXPORT REPORT")

        db = get_results_db()

        # Generate a text report from ResultsDB
        print("Generating progress report...")
        print()

        exam_count = db.get_exam_count()
        practice_count = db.get_practice_count()
        recent = db.get_recent_exams(10)
        all_stats = db.get_all_category_stats()
        weak = db.get_weak_categories(0.7)

        # Build report
        lines = []
        lines.append(f"{settings.APP_NAME} v{settings.VERSION} - Progress Report")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Exams Taken: {exam_count}")
        lines.append(f"Practice Attempts: {practice_count}")
        lines.append(f"Categories Practiced: {len(all_stats)}")
        lines.append("")

        if recent:
            lines.append("Recent Exams:")
            for r in recent:
                date = r['start_time'][:10] if r['start_time'] else "Unknown"
                status = "PASS" if r['passed'] else "FAIL"
                lines.append(f"  {date} - {r['percentage']:.0f}% {status}")
            lines.append("")

        if all_stats:
            lines.append("Category Performance:")
            for s in all_stats:
                rate = s['success_rate'] * 100
                lines.append(f"  {s['category']}: {rate:.0f}% ({s['attempts']} attempts)")
            lines.append("")

        if weak:
            lines.append("Weak Areas:")
            for w in weak:
                rate = w['success_rate'] * 100
                lines.append(f"  {w['category']}: {rate:.0f}%")
            lines.append("")

        report_text = "\n".join(lines)

        # Save to file
        report_path = settings.DATA_DIR / "progress_report.txt"
        try:
            with open(report_path, 'w') as f:
                f.write(report_text)
            print(fmt.success(f"Report saved to: {report_path}"))
        except Exception as e:
            print(fmt.error(f"Error saving report: {e}"))
            print()
            print("Report content:")
            print(report_text)

        print()
        input("Press Enter to return...")

    def setup_practice_disks(self):
        """Set up or manage practice loop devices for LVM."""
        from utils.helpers import (
            get_available_block_devices, get_loop_devices,
            create_practice_devices, cleanup_practice_devices
        )

        fmt.clear_screen()
        fmt.print_header("PRACTICE DISK SETUP")

        print("This tool creates virtual disks (loop devices) for LVM practice.")
        print("No real disks required!")
        print()

        # Show current status
        print(fmt.bold("Current Status:"))
        try:
            real_devices = get_available_block_devices()
            loop_devices = get_loop_devices()

            if real_devices:
                print(f"  Real disks available: {', '.join(real_devices)}")
            else:
                print("  Real disks available: None")

            if loop_devices:
                print(f"  Practice disks (loop): {', '.join(loop_devices)}")
            else:
                print("  Practice disks (loop): None")
        except Exception:
            print("  (Could not detect devices - are you running as root?)")

        print()
        print(fmt.bold("Options:"))
        print("  1. Create practice disks (2 x 500MB)")
        print("  2. Create custom practice disks")
        print("  3. Clean up all practice disks")
        print("  0. Return to menu")
        print()

        choice = input("Select option [1]: ").strip() or '1'

        if choice == '1':
            print()
            print("Creating 2 x 500MB practice disks...")
            devices = create_practice_devices(count=2, size_mb=500)
            if devices:
                print(fmt.success(f"Created devices: {', '.join(devices)}"))
            else:
                print(fmt.error("Failed to create practice disks"))

        elif choice == '2':
            try:
                count = int(input("Number of disks [2]: ").strip() or '2')
                size = int(input("Size per disk in MB [500]: ").strip() or '500')
                print()
                print(f"Creating {count} x {size}MB practice disks...")
                devices = create_practice_devices(count=count, size_mb=size)
                if devices:
                    print(fmt.success(f"Created devices: {', '.join(devices)}"))
                else:
                    print(fmt.error("Failed to create practice disks"))
            except ValueError:
                print(fmt.error("Invalid input"))

        elif choice == '3':
            from utils.helpers import confirm_action
            print()
            print(fmt.warning("This will remove all LVM structures on practice disks!"))
            if confirm_action("Are you sure?", default=False):
                print("Cleaning up practice disks...")
                if cleanup_practice_devices():
                    print(fmt.success("Practice disks cleaned up"))
                else:
                    print(fmt.error("Cleanup failed"))

        print()
        input("Press Enter to return...")

    def network_management(self):
        """Network backup and restore management."""
        try:
            from device import get_network_manager
        except ImportError:
            print(fmt.warning("Network management module not available."))
            input("Press Enter to return...")
            return

        from utils.helpers import confirm_action

        nm = get_network_manager()

        fmt.clear_screen()
        fmt.print_header("NETWORK BACKUP/RESTORE")

        # Show current state
        print(fmt.bold("Current Network State:"))
        try:
            print(f"  Primary Interface: {nm.get_primary_interface() or 'Unknown'}")
            print(f"  Primary IP: {nm.get_primary_ip() or 'Unknown'}")
        except Exception:
            print("  (Could not detect network state)")
        print()

        print(fmt.warning("WARNING: Network practice can disconnect SSH!"))
        print(fmt.dim("Always backup before practicing networking tasks."))
        print()

        # List existing backups
        try:
            backups = nm.list_backups()
        except Exception:
            backups = []

        if backups:
            print(fmt.bold(f"Available Backups ({len(backups)}):"))
            for i, b in enumerate(backups[:5], 1):
                print(f"  {i}. {b['timestamp'][:19]} - {b['hostname']} ({b['primary_ip']})")
        else:
            print(fmt.dim("No backups found."))
        print()

        print(fmt.bold("Options:"))
        print("  1. Backup Current State")
        print("  2. Show Recovery Commands")
        print("  3. Cleanup Practice Connections")
        print("  4. Full Restore from Backup")
        print("  0. Return to Setup")
        print()

        choice = input("Select option: ").strip()

        if choice == '1':
            print()
            print("Backing up network state...")
            filepath = nm.backup_state("manual")
            print(fmt.success("Backup saved!"))
            print(f"  Location: {filepath}")
            print()
            nm.print_recovery_commands()

        elif choice == '2':
            nm.print_recovery_commands()

        elif choice == '3':
            print()
            print("This will remove connections matching: lab-*, test-*, practice-*, team0, team1")
            if confirm_action("Proceed with cleanup?", default=True):
                removed = nm.cleanup_practice_connections()
                if removed:
                    print(fmt.success(f"Removed {len(removed)} connections:"))
                    for conn in removed:
                        print(f"  - {conn}")
                else:
                    print(fmt.info("No practice connections found to remove."))

        elif choice == '4':
            if not backups:
                print(fmt.error("No backups available!"))
            else:
                print()
                print("Available backups:")
                for i, b in enumerate(backups[:5], 1):
                    print(f"  {i}. {b['timestamp'][:19]} - {b['hostname']}")
                print()
                sel = input("Select backup number [1]: ").strip() or '1'
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(backups):
                        if confirm_action("This will restore network settings. Continue?", default=False):
                            print()
                            print("Restoring network state...")
                            result = nm.full_cleanup(backups[idx]['file'])
                            if 'error' in result:
                                print(fmt.error(result['error']))
                            else:
                                print(fmt.success("Cleanup complete!"))
                                if result.get('connections_removed'):
                                    print(f"  Removed connections: {', '.join(result['connections_removed'])}")
                                if result.get('hostname_restored'):
                                    print("  Hostname restored")
                    else:
                        print(fmt.error("Invalid selection"))
                except ValueError:
                    print(fmt.error("Invalid input"))

        print()
        input("Press Enter to return...")
