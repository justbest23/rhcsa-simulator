"""
Flatpak management tasks for RHCSA EX200 v10 exam.
Covers installing runtimes, adding remotes, managing Flatpak applications.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


@TaskRegistry.register("flatpak")
class InstallFlatpakRuntimeTask(BaseTask):
    """Install the Flatpak runtime package."""

    def __init__(self):
        super().__init__(
            id="flatpak_runtime_001",
            category="flatpak",
            difficulty="easy",
            points=6
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "Flatpak is a universal packaging system for Linux",
            "Install with: dnf install flatpak -y",
            "The flatpak package provides the flatpak command-line tool",
        ]

    def generate(self, **params):
        """Generate Flatpak runtime installation task."""
        self.description = (
            "Install the Flatpak runtime on this system:\n"
            "  - Install the 'flatpak' package using dnf\n"
            "  - Verify the flatpak command is available\n"
            "  - Ensure the Flatpak service is functional"
        )

        self.hints = [
            "Install: dnf install flatpak -y",
            "Verify: rpm -q flatpak",
            "Check command: flatpak --version",
            "The flatpak package is in the AppStream repository",
        ]

        return self

    def validate(self):
        """Validate that Flatpak runtime is installed."""
        checks = []
        total_points = 0

        # Check 1: flatpak package installed (3 points)
        result = execute_safe(['rpm', '-q', 'flatpak'])
        if result.success and 'flatpak' in result.stdout:
            checks.append(ValidationCheck(
                name="flatpak_package",
                passed=True,
                points=3,
                message="Flatpak package is installed"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="flatpak_package",
                passed=False,
                points=0,
                max_points=3,
                message="Flatpak package is not installed"
            ))

        # Check 2: flatpak command available (3 points)
        result = execute_safe(['flatpak', '--version'])
        if result.success:
            checks.append(ValidationCheck(
                name="flatpak_command",
                passed=True,
                points=3,
                message=f"Flatpak command available: {result.stdout.strip()}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="flatpak_command",
                passed=False,
                points=0,
                max_points=3,
                message="flatpak command not available"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("flatpak")
class AddFlathubRepoTask(BaseTask):
    """Add the Flathub remote repository for Flatpak."""

    def __init__(self):
        super().__init__(
            id="flatpak_flathub_001",
            category="flatpak",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "Flathub is the largest Flatpak repository",
            "flatpak remote-add --if-not-exists flathub <url>",
            "The --if-not-exists flag prevents errors if already added",
            "Use flatpak remotes to verify the remote was added",
        ]
        self.remote_name = None
        self.remote_url = None

    def generate(self, **params):
        """Generate Flathub remote addition task."""
        remote_configs = [
            {
                'remote_name': 'flathub',
                'remote_url': 'https://flathub.org/repo/flathub.flatpakrepo',
            },
            {
                'remote_name': 'flathub',
                'remote_url': 'https://dl.flathub.org/repo/flathub.flatpakrepo',
            },
            {
                'remote_name': 'flathub-beta',
                'remote_url': 'https://flathub.org/beta-repo/flathub-beta.flatpakrepo',
            },
            {
                'remote_name': 'fedora',
                'remote_url': 'oci+https://registry.fedoraproject.org',
            },
        ]

        config = params.get('config', random.choice(remote_configs))
        self.remote_name = config['remote_name']
        self.remote_url = config['remote_url']

        self.description = (
            f"Add a Flatpak remote repository:\n"
            f"  - Remote name: {self.remote_name}\n"
            f"  - Remote URL: {self.remote_url}\n"
            f"  - Ensure the flatpak package is installed first\n"
            f"  - The remote should be available system-wide\n"
            f"  - Verify the remote is listed"
        )

        self.hints = [
            "First ensure flatpak is installed: dnf install flatpak -y",
            f"Add remote: flatpak remote-add --if-not-exists {self.remote_name} {self.remote_url}",
            "Verify: flatpak remotes",
            "For system-wide (default): no extra flags needed (or use --system)",
            f"List available apps: flatpak remote-ls {self.remote_name}",
        ]

        return self

    def validate(self):
        """Validate that the Flatpak remote has been added."""
        checks = []
        total_points = 0

        # Check 1: flatpak installed (3 points)
        result = execute_safe(['rpm', '-q', 'flatpak'])
        if result.success and 'flatpak' in result.stdout:
            checks.append(ValidationCheck(
                name="flatpak_installed",
                passed=True,
                points=3,
                message="Flatpak package is installed"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="flatpak_installed",
                passed=False,
                points=0,
                max_points=3,
                message="Flatpak package is not installed (prerequisite)"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: Remote is configured (5 points)
        result = execute_safe(['flatpak', 'remotes'])
        if result.success:
            if self.remote_name in result.stdout:
                checks.append(ValidationCheck(
                    name="remote_configured",
                    passed=True,
                    points=5,
                    message=f"Remote '{self.remote_name}' is configured"
                ))
                total_points += 5
            else:
                checks.append(ValidationCheck(
                    name="remote_configured",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Remote '{self.remote_name}' not found in flatpak remotes"
                ))
        else:
            checks.append(ValidationCheck(
                name="remote_configured",
                passed=False,
                points=0,
                max_points=5,
                message="Could not list Flatpak remotes"
            ))

        # Check 3: Remote is system-wide (not user-only) (4 points)
        result = execute_safe(['flatpak', 'remotes', '--system'])
        if result.success and self.remote_name in result.stdout:
            checks.append(ValidationCheck(
                name="remote_system_wide",
                passed=True,
                points=4,
                message=f"Remote '{self.remote_name}' is available system-wide"
            ))
            total_points += 4
        else:
            # Check if it exists as user-only
            result2 = execute_safe(['flatpak', 'remotes', '--user'])
            if result2.success and self.remote_name in result2.stdout:
                checks.append(ValidationCheck(
                    name="remote_system_wide",
                    passed=False,
                    points=2,
                    max_points=4,
                    message=f"Remote '{self.remote_name}' exists but only for current user, not system-wide"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="remote_system_wide",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Remote '{self.remote_name}' not found as system-wide remote"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("flatpak")
class InstallFlatpakAppTask(BaseTask):
    """Install a Flatpak application from a remote."""

    def __init__(self):
        super().__init__(
            id="flatpak_install_app_001",
            category="flatpak",
            difficulty="exam",
            points=10
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "flatpak install <remote> <app-id> -y",
            "Use full application ID: org.vendor.AppName",
            "Search with: flatpak search <keyword>",
            "List installed: flatpak list",
        ]
        self.app_id = None
        self.app_name = None
        self.remote_name = None

    def generate(self, **params):
        """Generate Flatpak application installation task."""
        apps = [
            {
                'app_id': 'org.gnome.Calculator',
                'app_name': 'GNOME Calculator',
                'remote': 'flathub',
            },
            {
                'app_id': 'org.gnome.TextEditor',
                'app_name': 'GNOME Text Editor',
                'remote': 'flathub',
            },
            {
                'app_id': 'org.gnome.clocks',
                'app_name': 'GNOME Clocks',
                'remote': 'flathub',
            },
            {
                'app_id': 'org.freedesktop.Platform',
                'app_name': 'Freedesktop Platform Runtime',
                'remote': 'flathub',
            },
            {
                'app_id': 'org.gnome.Evince',
                'app_name': 'Evince Document Viewer',
                'remote': 'flathub',
            },
            {
                'app_id': 'org.mozilla.firefox',
                'app_name': 'Firefox Web Browser',
                'remote': 'flathub',
            },
        ]

        app = params.get('app', random.choice(apps))
        self.app_id = app['app_id']
        self.app_name = app['app_name']
        self.remote_name = app['remote']

        self.description = (
            f"Install a Flatpak application:\n"
            f"  - Application: {self.app_name}\n"
            f"  - Application ID: {self.app_id}\n"
            f"  - Remote: {self.remote_name}\n"
            f"  - Ensure the Flatpak remote is configured first\n"
            f"  - Verify the application is installed"
        )

        self.hints = [
            f"Install: flatpak install {self.remote_name} {self.app_id} -y",
            f"Verify: flatpak list | grep {self.app_id}",
            f"Info: flatpak info {self.app_id}",
            f"Search: flatpak search {self.app_name.split()[0]}",
            "You may need to add the remote first: flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo",
        ]

        return self

    def validate(self):
        """Validate that the Flatpak application is installed."""
        checks = []
        total_points = 0

        # Check 1: flatpak command available (2 points)
        result = execute_safe(['rpm', '-q', 'flatpak'])
        if result.success and 'flatpak' in result.stdout:
            checks.append(ValidationCheck(
                name="flatpak_available",
                passed=True,
                points=2,
                message="Flatpak is installed"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="flatpak_available",
                passed=False,
                points=0,
                max_points=2,
                message="Flatpak is not installed"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: Remote is configured (3 points)
        result = execute_safe(['flatpak', 'remotes'])
        if result.success and self.remote_name in result.stdout:
            checks.append(ValidationCheck(
                name="remote_available",
                passed=True,
                points=3,
                message=f"Remote '{self.remote_name}' is available"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="remote_available",
                passed=False,
                points=0,
                max_points=3,
                message=f"Remote '{self.remote_name}' is not configured"
            ))

        # Check 3: Application is installed (5 points)
        result = execute_safe(['flatpak', 'list', '--app'])
        if result.success and self.app_id in result.stdout:
            checks.append(ValidationCheck(
                name="app_installed",
                passed=True,
                points=5,
                message=f"Application {self.app_id} is installed"
            ))
            total_points += 5
        else:
            # Also check runtimes (for org.freedesktop.Platform etc)
            result2 = execute_safe(['flatpak', 'list', '--runtime'])
            if result2.success and self.app_id in result2.stdout:
                checks.append(ValidationCheck(
                    name="app_installed",
                    passed=True,
                    points=5,
                    message=f"Runtime {self.app_id} is installed"
                ))
                total_points += 5
            else:
                checks.append(ValidationCheck(
                    name="app_installed",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Application {self.app_id} is not installed"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("flatpak")
class ListFlatpakAppsTask(BaseTask):
    """List installed Flatpak applications and save output."""

    def __init__(self):
        super().__init__(
            id="flatpak_list_001",
            category="flatpak",
            difficulty="easy",
            points=5
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "flatpak list shows all installed apps and runtimes",
            "flatpak list --app shows only applications",
            "flatpak list --runtime shows only runtimes",
        ]
        self.output_file = None
        self.list_type = None

    def generate(self, **params):
        """Generate Flatpak list task."""
        list_types = [
            ('all', 'all installed Flatpak applications and runtimes'),
            ('apps', 'only installed Flatpak applications'),
            ('runtimes', 'only installed Flatpak runtimes'),
        ]

        choice = params.get('list_type', random.choice(list_types))
        if isinstance(choice, tuple):
            self.list_type, list_desc = choice
        else:
            self.list_type = choice
            list_desc = choice

        self.output_file = params.get('output', f'/tmp/flatpak_{self.list_type}.txt')

        self.description = (
            f"List Flatpak applications and save the output:\n"
            f"  - List: {list_desc}\n"
            f"  - Save the output to: {self.output_file}\n"
            f"  - Ensure the file contains the listing"
        )

        flag_map = {'all': '', 'apps': ' --app', 'runtimes': ' --runtime'}
        flag = flag_map.get(self.list_type, '')

        self.hints = [
            f"List command: flatpak list{flag}",
            f"Save to file: flatpak list{flag} > {self.output_file}",
            "Columns shown: Name, Application ID, Version, Branch, Origin",
            "Use flatpak info <app-id> for detailed info",
        ]

        return self

    def validate(self):
        """Validate Flatpak listing output."""
        checks = []
        total_points = 0

        # Check 1: Output file exists (2 points)
        result = execute_safe(['test', '-f', self.output_file])
        if result.success:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=2,
                message=f"Output file {self.output_file} exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Output file {self.output_file} not found"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: File has content (3 points)
        result = execute_safe(['test', '-s', self.output_file])
        if result.success:
            checks.append(ValidationCheck(
                name="output_has_content",
                passed=True,
                points=3,
                message="Output file contains Flatpak listing data"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="output_has_content",
                passed=False,
                points=0,
                max_points=3,
                message="Output file is empty"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("flatpak")
class RemoveFlatpakAppTask(BaseTask):
    """Remove an installed Flatpak application."""

    def __init__(self):
        super().__init__(
            id="flatpak_remove_001",
            category="flatpak",
            difficulty="medium",
            points=8
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "flatpak uninstall <app-id> to remove an application",
            "Use flatpak list to find installed application IDs",
            "Add -y flag to skip confirmation",
            "flatpak uninstall --unused removes unused runtimes",
        ]
        self.app_id = None
        self.app_name = None

    def generate(self, **params):
        """Generate Flatpak application removal task."""
        apps = [
            {
                'app_id': 'org.gnome.Calculator',
                'app_name': 'GNOME Calculator',
            },
            {
                'app_id': 'org.gnome.TextEditor',
                'app_name': 'GNOME Text Editor',
            },
            {
                'app_id': 'org.gnome.clocks',
                'app_name': 'GNOME Clocks',
            },
            {
                'app_id': 'org.gnome.Evince',
                'app_name': 'Evince Document Viewer',
            },
            {
                'app_id': 'org.mozilla.firefox',
                'app_name': 'Firefox Web Browser',
            },
        ]

        app = params.get('app', random.choice(apps))
        self.app_id = app['app_id']
        self.app_name = app['app_name']

        self.description = (
            f"Remove a Flatpak application:\n"
            f"  - Application: {self.app_name}\n"
            f"  - Application ID: {self.app_id}\n"
            f"  - Completely remove the application\n"
            f"  - Optionally remove unused runtimes"
        )

        self.hints = [
            f"Remove: flatpak uninstall {self.app_id} -y",
            f"Verify removed: flatpak list | grep {self.app_id}",
            "Remove unused runtimes: flatpak uninstall --unused -y",
            "List installed before removing: flatpak list --app",
        ]

        return self

    def validate(self):
        """Validate that the Flatpak application has been removed."""
        checks = []
        total_points = 0

        # Check 1: flatpak available (2 points)
        result = execute_safe(['rpm', '-q', 'flatpak'])
        if result.success and 'flatpak' in result.stdout:
            checks.append(ValidationCheck(
                name="flatpak_available",
                passed=True,
                points=2,
                message="Flatpak is installed"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="flatpak_available",
                passed=False,
                points=0,
                max_points=2,
                message="Flatpak is not installed; cannot verify removal"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: Application is NOT installed (6 points)
        result = execute_safe(['flatpak', 'list'])
        if result.success:
            if self.app_id not in result.stdout:
                checks.append(ValidationCheck(
                    name="app_removed",
                    passed=True,
                    points=6,
                    message=f"Application {self.app_id} has been removed"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="app_removed",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Application {self.app_id} is still installed"
                ))
        else:
            checks.append(ValidationCheck(
                name="app_removed",
                passed=False,
                points=0,
                max_points=6,
                message="Could not list Flatpak applications"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
