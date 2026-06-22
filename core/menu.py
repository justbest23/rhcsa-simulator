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
            fmt.print_menu_option('E', "Mock Exam", f"20–25 tasks, {settings.DEFAULT_EXAM_DURATION} min, reboot sim")
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
            fmt.print_menu_option(6, "Result History", "Drill into past exam results task by task")
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
            elif choice == '6':
                return 'history'
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
     validate your work and review hints.
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
        print("  4. System Reset (remove practice artifacts)")
        print("  5. Populate Practice Environment (DNF history)")
        print("  0. Return to Menu")
        print()

        choice = input("Select option: ").strip()

        if choice == '1':
            self.setup_practice_disks()
        elif choice == '2':
            self.show_stats()
        elif choice == '3':
            self.network_management()
        elif choice == '4':
            self.system_reset()
        elif choice == '5':
            self.populate_practice_environment()

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
        print("  1. Create practice disks (3 x 500MB — LVM and partition/swap practice)")
        print("  2. Create custom practice disks")
        print("  3. Clean up all practice disks")
        print("  0. Return to menu")
        print()

        choice = input("Select option [1]: ").strip() or '1'

        if choice == '1':
            print()
            print("Creating 3 x 500MB practice disks...")
            devices = create_practice_devices(count=3, size_mb=500)
            if devices:
                print(fmt.success(f"Created devices: {', '.join(devices)}"))
                print(fmt.info(f"  {devices[-1]} is available for swap partition practice"))
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

    def show_result_history(self):
        """List recent exam results and allow drilling into task-level detail."""
        import json
        from core.results_db import get_results_db

        db = get_results_db()

        while True:
            fmt.clear_screen()
            fmt.print_header("RESULT HISTORY")

            exams = db.get_recent_exams(10)

            if not exams:
                print(fmt.info("No exam results yet. Complete a mock exam to see results here."))
                print()
                input("Press Enter to return...")
                return

            print(fmt.bold(f"Last {len(exams)} exam sessions:"))
            print()
            for i, ex in enumerate(exams, 1):
                date = ex['start_time'][:16].replace('T', ' ') if ex['start_time'] else '?'
                pct = ex['percentage']
                status = fmt.success("PASS") if ex['passed'] else fmt.error("FAIL")
                tasks = ex.get('task_count', '?')
                score = f"{ex['total_score']}/{ex['max_score']}"
                print(f"  {i:2}. {date}  {score} pts  {pct:.0f}%  {status}  ({tasks} tasks)")

            print()
            print(fmt.dim("  0. Return to menu"))
            print()

            choice = input("Select a session to review (number): ").strip()
            if choice == '0' or choice.lower() == 'q':
                return

            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(exams)):
                    print(fmt.error("Invalid selection"))
                    input("Press Enter to continue...")
                    continue
            except ValueError:
                print(fmt.error("Please enter a number"))
                input("Press Enter to continue...")
                continue

            self._show_exam_detail(db, exams[idx])

    def _show_exam_detail(self, db, exam):
        """Show per-task breakdown for one exam session."""
        import json
        from config import settings

        exam_id = exam['exam_id']
        task_results = db.get_exam_task_results(exam_id)

        if not task_results:
            print(fmt.info("No per-task data saved for this session."))
            print(fmt.dim("(Per-task detail is saved starting from sessions after this update)"))
            input("\nPress Enter to return...")
            return

        task_list = list(enumerate(task_results, 1))

        while True:
            fmt.clear_screen()
            date = exam['start_time'][:16].replace('T', ' ') if exam['start_time'] else '?'
            pct = exam['percentage']
            status = fmt.success("PASS") if exam['passed'] else fmt.error("FAIL")
            fmt.print_header(f"EXAM DETAIL — {date}")
            print(f"  Result: {status}  {exam['total_score']}/{exam['max_score']} pts  ({pct:.0f}%)")
            print()

            for num, tr in task_list:
                icon = fmt.success("✓") if tr['passed'] else fmt.error("✗")
                cat = fmt.format_category_name(tr['category'])
                domain = settings.EXAM_DOMAINS.get(tr.get('domain', 0), '')
                score_str = f"{tr['score']}/{tr['max_score']}pt"
                # Show first line of description only
                first_line = tr['description'].splitlines()[0] if tr['description'] else tr['task_id']
                print(f"  {num:2}. {icon} [{score_str:>8}]  {first_line[:55]}")
                if domain:
                    d_num = tr.get('domain', '?')
                    print(f"       {fmt.dim(f'D{d_num} {domain} — {cat}')}")

            print()
            print(fmt.dim("  Enter task number for full detail, 0 to go back"))
            print()

            choice = input("Select task: ").strip()
            if choice == '0' or choice.lower() == 'q':
                return

            try:
                tidx = int(choice) - 1
                if not (0 <= tidx < len(task_list)):
                    continue
            except ValueError:
                continue

            self._show_task_detail(task_list[tidx][1])

    def _show_task_detail(self, tr):
        """Show full detail for one task result including failed checks and hints."""
        import json

        fmt.clear_screen()
        status = fmt.success("PASSED") if tr['passed'] else fmt.error("FAILED")
        cat = fmt.format_category_name(tr['category'])
        print(f"{status}  {tr['score']}/{tr['max_score']} points  [{cat} / {tr['difficulty']}]")
        print("=" * 60)
        print()

        # Task description (what was asked)
        print(fmt.bold("Task:"))
        print(tr['description'] or "(no description saved)")
        print()

        # Validation checks (what the system found)
        checks = []
        if tr.get('checks_json'):
            try:
                checks = json.loads(tr['checks_json'])
            except Exception:
                pass

        if checks:
            print(fmt.bold("Validation breakdown:"))
            for c in checks:
                icon = fmt.success("✓") if c.get('passed') else fmt.error("✗")
                pts = c.get('points', 0)
                max_pts = c.get('max_points', pts)
                msg = c.get('message', c.get('name', ''))
                print(f"  {icon} [{pts}/{max_pts}pt]  {msg}")
            print()

        # Hints / what to study (only if task failed)
        if not tr['passed']:
            hints = []
            if tr.get('hints_json'):
                try:
                    hints = json.loads(tr['hints_json'])
                except Exception:
                    pass

            exam_tips = []
            if tr.get('exam_tips_json'):
                try:
                    exam_tips = json.loads(tr['exam_tips_json'])
                except Exception:
                    pass

            if hints:
                print(fmt.bold("What to study / how to fix it:"))
                for h in hints:
                    print(f"  • {h}")
                print()

            if exam_tips:
                print(fmt.bold("Exam tips:"))
                for t in exam_tips:
                    print(f"  * {t}")
                print()

            if not hints and not exam_tips:
                print(fmt.dim("(No hints saved for this session — re-run a new exam to get hints)"))
                print()

        input("Press Enter to return to session view...")

    def populate_practice_environment(self):
        """Install/remove lightweight packages to build up DNF transaction history."""
        from utils.helpers import populate_dnf_history, confirm_action

        fmt.clear_screen()
        fmt.print_header("POPULATE PRACTICE ENVIRONMENT")

        print("This will install and immediately remove a series of small packages")
        print("to build up DNF transaction history for practice tasks.")
        print()
        print(fmt.info("Only packages NOT already installed will be touched."))
        print(fmt.info("Nothing on your system will be permanently changed."))
        print(fmt.warning("Requires active DNF repos and internet/local mirror access."))
        print(fmt.warning("Takes 2–5 minutes depending on connection speed."))
        print()

        if not confirm_action("Build DNF transaction history?", default=True):
            print(fmt.dim("Cancelled."))
            print()
            input("Press Enter to return...")
            return

        print()
        print("Working... (this may take a few minutes)")
        print()

        def progress(msg):
            print(f"  {msg}")

        cycles = populate_dnf_history(target_transactions=12, progress_callback=progress)

        print()
        if cycles > 0:
            print(fmt.success(f"Done! Completed {cycles} install/remove cycles ({cycles * 2} new DNF transactions)."))
            print(fmt.info("Run 'dnf history' to verify."))
        else:
            print(fmt.error("No cycles completed — repos may not be configured or packages unavailable."))
            print(fmt.dim("Make sure DNF repos are set up: dnf repolist"))

        print()
        input("Press Enter to return...")

    def system_reset(self):
        """Reset system to barebones practice-ready state without touching SSH or network."""
        import subprocess
        import os
        import re
        from utils.helpers import (
            cleanup_practice_devices, get_loop_devices, confirm_action
        )

        fmt.clear_screen()
        fmt.print_header("SYSTEM RESET")

        print(fmt.warning("This removes practice artifacts: LVM, swap files, practice repos,"))
        print(fmt.warning("cron/at jobs, tuned profile, and scripts in /usr/local/bin/."))
        print(fmt.info("SSH, network, firewall, SELinux, and users will NOT be touched."))
        print()

        if not confirm_action("Continue with system reset?", default=False):
            print(fmt.dim("Reset cancelled."))
            print()
            input("Press Enter to return...")
            return

        # ── Step 1: Loop devices / LVM ───────────────────────────────────────
        print()
        print(fmt.bold("Step 1: Practice Disks (loop devices / LVM)"))
        loop_devices = get_loop_devices()
        if loop_devices:
            print(f"  Found: {', '.join(loop_devices)}")
            if confirm_action("  Remove all LVM structures and practice disks?", default=True):
                if cleanup_practice_devices():
                    print(fmt.success("  Practice disks cleaned up"))
                else:
                    print(fmt.error("  Cleanup had errors — check manually"))
        else:
            print(fmt.dim("  No practice disks found"))

        # ── Step 2: Active swap (files + loop-device partitions) ─────────────
        print()
        print(fmt.bold("Step 2: Practice Swap"))
        swap_entries = []   # (device, type)
        try:
            with open('/proc/swaps', 'r') as f:
                for line in f.readlines()[1:]:   # skip header
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    device, stype = parts[0], parts[1]
                    # Remove swap files (any path) and loop-device swap partitions
                    if stype == 'file':
                        swap_entries.append((device, 'file'))
                    elif stype == 'partition' and '/loop' in device:
                        swap_entries.append((device, 'loop'))
        except Exception:
            pass

        if swap_entries:
            for device, stype in swap_entries:
                label = 'swap file' if stype == 'file' else 'loop swap'
                print(f"  Active {label}: {device}")
            if confirm_action("  Deactivate and remove these swap entries?", default=True):
                for device, stype in swap_entries:
                    subprocess.run(['swapoff', device], capture_output=True)
                    if stype == 'file' and os.path.exists(device):
                        try:
                            os.remove(device)
                            print(fmt.success(f"  Removed {device}"))
                        except OSError as e:
                            print(fmt.error(f"  Could not remove {device}: {e}"))
                    else:
                        print(fmt.success(f"  Deactivated {device}"))
        else:
            print(fmt.dim("  No practice swap found"))

        # ── Step 3: /etc/fstab cleanup ───────────────────────────────────────
        print()
        print(fmt.bold("Step 3: /etc/fstab Cleanup"))
        _fstab_patterns = [
            re.compile(r'/var/lib/rhcsa-simulator/loops/'),
            re.compile(r'/dev/loop\d+\s'),
            re.compile(r'\s/tmp/swap\S*'),
            re.compile(r'\s/root/swapfile'),
            re.compile(r'\s/opt/swap\S*'),
        ]
        try:
            with open('/etc/fstab', 'r') as f:
                fstab_lines = f.readlines()

            practice_lines, clean_lines = [], []
            for line in fstab_lines:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    clean_lines.append(line)
                    continue
                if any(p.search(line) for p in _fstab_patterns):
                    practice_lines.append(line.rstrip())
                else:
                    clean_lines.append(line)

            if practice_lines:
                print("  Practice entries to remove:")
                for pl in practice_lines:
                    print(f"    {pl}")
                if confirm_action("  Remove these entries from /etc/fstab?", default=True):
                    with open('/etc/fstab', 'w') as f:
                        f.writelines(clean_lines)
                    print(fmt.success("  /etc/fstab cleaned"))
            else:
                print(fmt.dim("  No practice entries in /etc/fstab"))
        except Exception as e:
            print(fmt.error(f"  Error reading /etc/fstab: {e}"))

        # ── Step 4: Practice repos ───────────────────────────────────────────
        print()
        print(fmt.bold("Step 4: Practice Repos (/etc/yum.repos.d/)"))
        _practice_repo_ids = {
            'localrepo', 'internalmirror', 'customrepo', 'examrepo', 'backuprepo',
        }
        repo_files_to_remove = []
        repo_dir = '/etc/yum.repos.d'
        try:
            for fname in os.listdir(repo_dir):
                if fname.endswith('.repo'):
                    repo_id = fname[:-5]
                    if repo_id in _practice_repo_ids:
                        repo_files_to_remove.append(os.path.join(repo_dir, fname))
        except Exception:
            pass

        if repo_files_to_remove:
            print("  Practice repo files found:")
            for rf in repo_files_to_remove:
                print(f"    {rf}")
            if confirm_action("  Remove these repo files?", default=True):
                for rf in repo_files_to_remove:
                    try:
                        os.remove(rf)
                    except OSError as e:
                        print(fmt.error(f"  Could not remove {rf}: {e}"))
                print(fmt.success("  Practice repos removed"))
        else:
            print(fmt.dim("  No practice repos found"))

        # ── Step 5: Root crontab ─────────────────────────────────────────────
        print()
        print(fmt.bold("Step 5: Root Crontab"))
        try:
            result = subprocess.run(
                ['crontab', '-l', '-u', 'root'],
                capture_output=True, text=True
            )
            crontab_content = result.stdout.strip()
            if result.returncode == 0 and crontab_content:
                print("  Current root crontab:")
                for line in crontab_content.splitlines():
                    print(f"    {line}")
                if confirm_action("  Clear root crontab?", default=True):
                    subprocess.run(['crontab', '-r', '-u', 'root'], capture_output=True)
                    print(fmt.success("  Root crontab cleared"))
            else:
                print(fmt.dim("  Root crontab is empty"))
        except Exception as e:
            print(fmt.error(f"  Error accessing crontab: {e}"))

        # ── Step 6: At jobs ──────────────────────────────────────────────────
        print()
        print(fmt.bold("Step 6: Scheduled 'at' Jobs"))
        try:
            result = subprocess.run(['atq'], capture_output=True, text=True)
            if result.stdout.strip():
                print("  Pending at jobs:")
                for line in result.stdout.strip().splitlines():
                    print(f"    {line}")
                if confirm_action("  Remove all pending at jobs?", default=True):
                    job_ids = [
                        line.split()[0]
                        for line in result.stdout.strip().splitlines()
                        if line.strip()
                    ]
                    for jid in job_ids:
                        subprocess.run(['atrm', jid], capture_output=True)
                    print(fmt.success("  At jobs removed"))
            else:
                print(fmt.dim("  No pending at jobs"))
        except FileNotFoundError:
            print(fmt.dim("  'at' not installed — skipping"))
        except Exception as e:
            print(fmt.error(f"  Error: {e}"))

        # ── Step 7: Tuned profile ────────────────────────────────────────────
        print()
        print(fmt.bold("Step 7: Tuned Profile"))
        try:
            active_result = subprocess.run(
                ['tuned-adm', 'active'], capture_output=True, text=True
            )
            current = active_result.stdout.strip() if active_result.returncode == 0 else "unknown"
            print(f"  Current: {current}")

            rec_result = subprocess.run(
                ['tuned-adm', 'recommend'], capture_output=True, text=True
            )
            recommended = rec_result.stdout.strip() if rec_result.returncode == 0 else 'balanced'
            print(f"  Recommended for this system: {recommended}")

            if confirm_action(f"  Reset tuned to '{recommended}'?", default=True):
                subprocess.run(['tuned-adm', 'profile', recommended], capture_output=True)
                print(fmt.success(f"  Tuned profile set to '{recommended}'"))
        except FileNotFoundError:
            print(fmt.dim("  tuned-adm not installed — skipping"))
        except Exception as e:
            print(fmt.error(f"  Error: {e}"))

        # ── Step 8: Practice scripts in /usr/local/bin ───────────────────────
        print()
        print(fmt.bold("Step 8: Practice Scripts (/usr/local/bin/*.sh)"))
        try:
            scripts = [
                os.path.join('/usr/local/bin', f)
                for f in os.listdir('/usr/local/bin')
                if f.endswith('.sh') and os.path.isfile(os.path.join('/usr/local/bin', f))
            ]
            if scripts:
                print("  Shell scripts found:")
                for s in scripts:
                    print(f"    {s}")
                if confirm_action("  Remove these scripts?", default=True):
                    for s in scripts:
                        try:
                            os.remove(s)
                        except OSError as e:
                            print(fmt.error(f"  Could not remove {s}: {e}"))
                    print(fmt.success("  Scripts removed"))
            else:
                print(fmt.dim("  No .sh scripts in /usr/local/bin"))
        except Exception as e:
            print(fmt.error(f"  Error: {e}"))

        # ── Done ─────────────────────────────────────────────────────────────
        print()
        print("=" * 50)
        print(fmt.success("System reset complete!"))
        print(fmt.info("SSH and network were not modified."))
        print(fmt.info("Firewall, SELinux, and users were not modified."))
        print()
        input("Press Enter to return...")
