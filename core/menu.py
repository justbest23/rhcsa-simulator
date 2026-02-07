"""
Main menu system for RHCSA Simulator v2.0.0

Streamlined interface with quick-access modes.
"""

import sys
from utils import formatters as fmt
from config import settings


class MenuSystem:
    """
    Main menu system for the application.

    v2.0.0 Features:
    - Simplified 9-option menu (down from 15)
    - Quick-access keys for common actions
    - Auto-cleanup status display
    """

    def __init__(self):
        """Initialize menu system."""
        self._device_info = None

    def _get_device_info(self):
        """Get practice device info for display."""
        if self._device_info is None:
            try:
                from device import get_device_manager
                dm = get_device_manager()
                device = dm.get_practice_device()
                self._device_info = device if device else "No practice device"
            except Exception:
                self._device_info = "Unknown"
        return self._device_info

    def display_main_menu(self):
        """Display main menu and get selection."""
        while True:
            fmt.clear_screen()
            self._print_header()

            # Quick Start section
            print(fmt.bold("QUICK START"))
            fmt.print_menu_option('Q', "Quick Practice", "5 random tasks with auto-cleanup")
            fmt.print_menu_option('E', "Mock Exam", "Full 15-task timed exam")
            print()

            # Learning section
            print(fmt.bold("LEARN"))
            fmt.print_menu_option(1, "Guided Practice", "Practice with hints & feedback")
            fmt.print_menu_option(2, "Learn Mode", "Study concepts with examples")
            fmt.print_menu_option(3, "Command Recall", "Build muscle memory")
            print()

            # Practice section
            print(fmt.bold("PRACTICE"))
            fmt.print_menu_option(4, "Category Practice", "Practice specific topics")
            fmt.print_menu_option(5, "Scenario Mode", "Multi-step challenges")
            fmt.print_menu_option(6, "Troubleshooting", "Fix broken systems")
            print()

            # Progress section
            print(fmt.bold("PROGRESS"))
            fmt.print_menu_option(7, "Dashboard", "View stats & history")
            fmt.print_menu_option(8, "Export Report", "Generate progress report")
            print()

            # Footer
            print(fmt.dim("─" * 50))
            device = self._get_device_info()
            if device and device != "No practice device":
                print(fmt.dim(f"  Practice Device: {device} (auto-cleanup enabled)"))
            print(fmt.dim(f"  [S] Setup  [?] Help  [0] Exit"))
            print()

            choice = input("Select option: ").strip().lower()

            # Quick access keys
            if choice == 'q':
                return 'quick_practice'
            elif choice == 'e':
                return 'exam'

            # Learning options
            elif choice == '1':
                return 'guided_practice'
            elif choice == '2':
                return 'learn'
            elif choice == '3':
                return 'command_recall'

            # Practice options
            elif choice == '4':
                return 'practice'
            elif choice == '5':
                return 'scenario'
            elif choice == '6':
                return 'troubleshoot'

            # Progress options
            elif choice == '7':
                return 'dashboard'
            elif choice == '8':
                return 'export'

            # Utility options
            elif choice == 's':
                return 'setup'
            elif choice == '?' or choice == 'h':
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
        """Show unified progress dashboard."""
        from core.results import get_results_manager
        from core.bookmarks import get_weak_area_analyzer, get_bookmark_manager

        fmt.clear_screen()
        fmt.print_header("PROGRESS DASHBOARD")

        results_mgr = get_results_manager()
        analyzer = get_weak_area_analyzer()
        bookmarks = get_bookmark_manager()

        # Overall Stats
        report = analyzer.get_summary_report()
        print(fmt.bold("Overall Performance"))
        print(f"  Total Attempts: {report['total_attempts']}")
        print(f"  Success Rate: {report['overall_success_rate']*100:.1f}%")
        print(f"  Categories Practiced: {report['categories_practiced']}")
        print()

        # Recent Exams
        recent = results_mgr.get_recent_results(5)
        if recent:
            print(fmt.bold("Recent Exams"))
            for r in recent:
                status = fmt.success("PASS") if r.passed else fmt.error("FAIL")
                print(f"  {r.end_time[:10]} - {r.percentage:.0f}% {status}")
            print()

        # Weak Areas
        if report['weak_categories']:
            print(fmt.bold("Areas to Improve"))
            for cat in report['weak_categories'][:3]:
                print(f"  - {fmt.format_category_name(cat['category'])}: {cat['score_rate']*100:.0f}%")
            print()

        # Bookmarks
        bm_list = bookmarks.get_all()
        if bm_list:
            print(fmt.bold(f"Bookmarked Tasks ({len(bm_list)})"))
            for bm in bm_list[:3]:
                print(f"  - {bm.task_id}")
            print()

        print(fmt.dim("Options: [W] Weak areas  [B] Bookmarks  [Enter] Return"))
        choice = input().strip().lower()

        if choice == 'w':
            self.show_weak_areas()
        elif choice == 'b':
            self.show_bookmarks()

    def show_help(self):
        """Display help information."""
        fmt.clear_screen()
        fmt.print_header("HELP")

        help_text = """
RHCSA Simulator v2.0.0 - Quick Guide

QUICK START
  Q - Quick Practice: 5 random tasks with auto-cleanup between each.
      Perfect for daily practice sessions.

  E - Mock Exam: Full 15-task exam simulation with timer.
      Tests all RHCSA objectives.

LEARNING MODES
  1. Guided Practice - Practice with 3-level progressive hints
  2. Learn Mode - Study concepts with explanations & examples
  3. Command Recall - Type commands to build muscle memory

PRACTICE MODES
  4. Category Practice - Focus on specific topics (LVM, users, etc.)
  5. Scenario Mode - Multi-step real-world challenges
  6. Troubleshooting - Diagnose and fix broken systems

PROGRESS
  7. Dashboard - View your stats, history, and weak areas
  8. Export Report - Generate PDF/HTML progress report

AUTO-CLEANUP (NEW in v2.0.0!)
  Resources are automatically cleaned up between tasks.
  No more manual disk wiping! The simulator handles:
  - Unmounting filesystems
  - Deactivating swap
  - Removing LVM structures (LVs, VGs, PVs)
  - Wiping device signatures
  - Cleaning /etc/fstab entries

SETUP
  Press 'S' to configure practice devices and options.

TIPS
  - Run as root (sudo) for full functionality
  - Practice daily for best results
  - Use bookmarks to save difficult tasks

For detailed RHCSA exam info: https://www.redhat.com/rhcsa
        """

        print(help_text)
        input("\nPress Enter to return to menu...")

    def show_setup(self):
        """Show setup and configuration options."""
        from device import get_device_manager, get_network_manager

        fmt.clear_screen()
        fmt.print_header("SETUP")

        dm = get_device_manager()
        nm = get_network_manager()
        device = dm.get_practice_device()

        print(fmt.bold("Current Configuration"))
        print(f"  Practice Device: {device or 'Not detected'}")
        print(f"  Auto-Cleanup: {'Enabled' if dm._cleanup_enabled else 'Disabled'}")
        print(f"  Primary Network: {nm.get_primary_interface() or 'Unknown'} ({nm.get_primary_ip() or 'No IP'})")
        print()

        print(fmt.bold("Options"))
        print("  1. Setup Practice Disks")
        print("  2. Toggle Auto-Cleanup")
        print("  3. View Task Statistics")
        print("  4. Refresh Device Detection")
        print("  5. Network Backup/Restore")
        print("  0. Return to Menu")
        print()

        choice = input("Select option: ").strip()

        if choice == '1':
            self.setup_practice_disks()
        elif choice == '2':
            if dm._cleanup_enabled:
                dm.disable_cleanup()
                print(fmt.warning("Auto-cleanup disabled"))
            else:
                dm.enable_cleanup()
                print(fmt.success("Auto-cleanup enabled"))
            input("Press Enter to continue...")
        elif choice == '3':
            self.show_stats()
        elif choice == '4':
            dm._practice_device = None
            dm._detect_practice_device()
            new_device = dm.get_practice_device()
            print(fmt.info(f"Practice device: {new_device or 'None detected'}"))
            input("Press Enter to continue...")
        elif choice == '5':
            self.network_management()

    def show_stats(self):
        """Show task statistics."""
        from tasks.registry import TaskRegistry

        fmt.clear_screen()
        fmt.print_header("TASK STATISTICS")

        # Initialize registry
        TaskRegistry.initialize()

        # Print statistics
        TaskRegistry.print_statistics()

        print()
        input("Press Enter to return...")

    def show_weak_areas(self):
        """Show weak areas analysis and recommendations."""
        from core.bookmarks import get_weak_area_analyzer

        fmt.clear_screen()
        fmt.print_header("WEAK AREA ANALYSIS")

        analyzer = get_weak_area_analyzer()
        report = analyzer.get_summary_report()

        # Overall stats
        print(fmt.bold("Overall Performance:"))
        print(f"  Total Attempts: {report['total_attempts']}")
        print(f"  Success Rate: {report['overall_success_rate']*100:.1f}%")
        print(f"  Score Rate: {report['overall_score_rate']*100:.1f}%")
        print(f"  Categories Practiced: {report['categories_practiced']}")
        print()

        # Weak areas
        if report['weak_categories']:
            fmt.print_weak_area_summary(report['weak_categories'])
        else:
            print(fmt.success("No significant weak areas detected!"))
            print("Keep practicing to gather more data.")

        print()

        # Recommendations
        if report['recommendations']:
            print(fmt.bold("Recommendations:"))
            for rec in report['recommendations']:
                fmt.print_recommendation_card(rec)

        print()
        input("Press Enter to return...")

    def show_bookmarks(self):
        """Show and manage bookmarks."""
        from core.bookmarks import get_bookmark_manager

        fmt.clear_screen()
        fmt.print_header("BOOKMARKS")

        manager = get_bookmark_manager()
        bookmarks = manager.get_all()

        if not bookmarks:
            print("No bookmarks saved yet.")
            print()
            print("You can bookmark tasks during practice sessions")
            print("to revisit them later.")
        else:
            print(fmt.bold(f"Saved Bookmarks ({len(bookmarks)}):"))
            print()

            for i, bm in enumerate(bookmarks, 1):
                print(f"  {fmt.bold(str(i) + '.')} {bm.task_id}")
                print(f"      Category: {fmt.format_category_name(bm.category)}")
                print(f"      Difficulty: {fmt.format_difficulty(bm.difficulty)}")
                if bm.note:
                    print(f"      Note: {fmt.dim(bm.note)}")
                print()

            # Options
            print()
            print("Options:")
            print("  C - Clear all bookmarks")
            print("  R - Return to menu")
            print()

            choice = input("Select option: ").strip().lower()
            if choice == 'c':
                from utils.helpers import confirm_action
                if confirm_action("Clear all bookmarks?", default=False):
                    manager.clear()
                    print(fmt.success("Bookmarks cleared."))

        print()
        input("Press Enter to return...")

    def export_report(self):
        """Export progress report."""
        from core.export import get_report_generator
        from core.bookmarks import get_weak_area_analyzer
        from core.mistakes_tracker import get_mistakes_tracker

        fmt.clear_screen()
        fmt.print_header("EXPORT REPORT")

        print("Generate a progress report in various formats.")
        print()
        print("Available formats:")
        print("  1. Text file (.txt)")
        print("  2. HTML file (.html)")
        print("  3. PDF file (.pdf) - requires reportlab")
        print("  0. Cancel")
        print()

        choice = input("Select format [1-3]: ").strip()

        if choice == '0':
            return

        format_map = {'1': 'text', '2': 'html', '3': 'pdf'}
        if choice not in format_map:
            print(fmt.error("Invalid selection"))
            input("Press Enter to continue...")
            return

        fmt_choice = format_map[choice]

        print()
        print("Generating report...")

        try:
            generator = get_report_generator()
            analyzer = get_weak_area_analyzer()
            tracker = get_mistakes_tracker()

            perf_data = analyzer.get_summary_report()
            mistakes_data = {'patterns': tracker.get_mistake_patterns()}

            filepath = generator.generate_progress_report(
                perf_data, mistakes_data, format=fmt_choice
            )

            print()
            print(fmt.success(f"Report generated successfully!"))
            print(f"  Location: {filepath}")
        except Exception as e:
            print()
            print(fmt.error(f"Error generating report: {e}"))

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
        real_devices = get_available_block_devices()
        loop_devices = get_loop_devices()

        if real_devices:
            print(f"  Real disks available: {', '.join(real_devices)}")
        else:
            print(f"  Real disks available: None")

        if loop_devices:
            print(f"  Practice disks (loop): {', '.join(loop_devices)}")
        else:
            print(f"  Practice disks (loop): None")

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
                print()
                print("You can now use these for LVM practice:")
                for dev in devices:
                    print(f"  - {dev}")
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
        from device import get_network_manager
        from utils.helpers import confirm_action

        nm = get_network_manager()

        fmt.clear_screen()
        fmt.print_header("NETWORK BACKUP/RESTORE")

        # Show current state
        print(fmt.bold("Current Network State:"))
        print(f"  Primary Interface: {nm.get_primary_interface() or 'Unknown'}")
        print(f"  Primary IP: {nm.get_primary_ip() or 'Unknown'}")
        print()

        # Show warning
        print(fmt.warning("WARNING: Network practice can disconnect SSH!"))
        print(fmt.dim("Always backup before practicing networking tasks."))
        print()

        # List existing backups
        backups = nm.list_backups()
        if backups:
            print(fmt.bold(f"Available Backups ({len(backups)}):"))
            for i, b in enumerate(backups[:5], 1):
                print(f"  {i}. {b['timestamp'][:19]} - {b['hostname']} ({b['primary_ip']})")
            if len(backups) > 5:
                print(fmt.dim(f"     ... and {len(backups) - 5} more"))
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
            print(fmt.success(f"Backup saved!"))
            print(f"  Location: {filepath}")
            print()
            # Also show recovery commands
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
                                if result['connections_removed']:
                                    print(f"  Removed connections: {', '.join(result['connections_removed'])}")
                                if result['hostname_restored']:
                                    print(f"  Hostname restored")
                                fw = result.get('firewall_cleaned', {})
                                if any(fw.values()):
                                    print(f"  Firewall rules cleaned")
                    else:
                        print(fmt.error("Invalid selection"))
                except ValueError:
                    print(fmt.error("Invalid input"))

        print()
        input("Press Enter to return...")
