"""
Package management tasks for RHCSA exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("packages")
class InstallPackageTask(BaseTask):
    """Install a package using dnf."""

    def __init__(self):
        super().__init__(
            id="pkg_install_001",
            category="packages",
            difficulty="easy",
            points=6
        )
        self.package_name = None

    def generate(self, **params):
        """Generate package installation task."""
        # Safe packages that can be installed for practice
        packages = ['tree', 'wget', 'vim-enhanced', 'tmux', 'htop', 'net-tools']
        self.package_name = params.get('package', random.choice(packages))

        self.description = (
            f"Install a package using dnf:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Use dnf command\n"
            f"  - Verify installation"
        )

        self.hints = [
            f"Install: dnf install {self.package_name} -y",
            f"Verify: rpm -q {self.package_name}",
            "Search for packages: dnf search <keyword>",
            "Get package info: dnf info <package>",
            "List installed: dnf list installed"
        ]

        return self

    def validate(self):
        """Validate package installation."""
        checks = []
        total_points = 0

        # Check: Package is installed
        result = execute_safe(['rpm', '-q', self.package_name])
        if result.success and self.package_name in result.stdout:
            checks.append(ValidationCheck(
                name="package_installed",
                passed=True,
                points=6,
                message=f"Package {self.package_name} is installed"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="package_installed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Package {self.package_name} is not installed"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class RemovePackageTask(BaseTask):
    """Remove a package using dnf."""

    def __init__(self):
        super().__init__(
            id="pkg_remove_001",
            category="packages",
            difficulty="easy",
            points=6
        )
        self.package_name = None

    def generate(self, **params):
        """Generate package removal task."""
        packages = ['tree', 'wget', 'tmux', 'htop']
        self.package_name = params.get('package', random.choice(packages))

        self.description = (
            f"Remove a package using dnf:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Ensure package is completely removed\n"
            f"  - Verify removal"
        )

        self.hints = [
            f"Remove: dnf remove {self.package_name} -y",
            f"Verify removed: rpm -q {self.package_name}",
            "Remove with dependencies: dnf autoremove",
            "Clean cache: dnf clean all"
        ]

        return self

    def validate(self):
        """Validate package removal."""
        checks = []
        total_points = 0

        # Check: Package is NOT installed
        result = execute_safe(['rpm', '-q', self.package_name])
        if not result.success or 'not installed' in result.stdout.lower():
            checks.append(ValidationCheck(
                name="package_removed",
                passed=True,
                points=6,
                message=f"Package {self.package_name} is not installed (removed)"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="package_removed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Package {self.package_name} is still installed"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class InstallPackageGroupTask(BaseTask):
    """Install a package group."""

    def __init__(self):
        super().__init__(
            id="pkg_group_001",
            category="packages",
            difficulty="medium",
            points=8
        )
        self.group_name = None

    def generate(self, **params):
        """Generate package group installation task."""
        groups = [
            ('Development Tools', 'development'),
            ('System Tools', 'system-tools'),
            ('Security Tools', 'security-tools'),
        ]

        group_choice = params.get('group', random.choice(groups))
        if isinstance(group_choice, tuple):
            self.group_name, self.group_id = group_choice
        else:
            self.group_name = group_choice
            self.group_id = group_choice.lower().replace(' ', '-')

        self.description = (
            f"Install a package group:\n"
            f"  - Group: {self.group_name}\n"
            f"  - Use dnf group install command\n"
            f"  - Verify installation"
        )

        self.hints = [
            f'Install group: dnf group install "{self.group_name}" -y',
            "Or: dnf groupinstall (older syntax)",
            "List available groups: dnf group list",
            "List hidden groups: dnf group list hidden",
            f'Group info: dnf group info "{self.group_name}"'
        ]

        return self

    def validate(self):
        """Validate package group installation."""
        checks = []
        total_points = 0

        # Check: Group is installed
        result = execute_safe(['dnf', 'group', 'list', 'installed'])
        if result.success and (self.group_name.lower() in result.stdout.lower() or
                               self.group_id in result.stdout.lower()):
            checks.append(ValidationCheck(
                name="group_installed",
                passed=True,
                points=8,
                message=f"Package group '{self.group_name}' is installed"
            ))
            total_points += 8
        else:
            # Check if at least some packages from group are installed
            result2 = execute_safe(['dnf', 'group', 'info', self.group_name])
            if result2.success and 'Installed' in result2.stdout:
                checks.append(ValidationCheck(
                    name="group_installed",
                    passed=True,
                    points=5,
                    message=f"Some packages from '{self.group_name}' installed (partial)"
                ))
                total_points += 5
            else:
                checks.append(ValidationCheck(
                    name="group_installed",
                    passed=False,
                    points=0,
                    max_points=8,
                    message=f"Package group '{self.group_name}' is not installed"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class ConfigureRepoTask(BaseTask):
    """Configure a new package repository."""

    def __init__(self):
        super().__init__(
            id="pkg_repo_001",
            category="packages",
            difficulty="medium",
            points=10
        )
        self.repo_name = None
        self.repo_url = None

    def generate(self, **params):
        """Generate repository configuration task."""
        self.repo_name = params.get('name', 'myrepo')
        self.repo_url = params.get('url', 'http://mirror.example.com/rhel9/BaseOS')

        self.description = (
            f"Configure a new package repository:\n"
            f"  - Repository ID: {self.repo_name}\n"
            f"  - Base URL: {self.repo_url}\n"
            f"  - Create file: /etc/yum.repos.d/{self.repo_name}.repo\n"
            f"  - Enable the repository\n"
            f"  - Disable GPG check (for practice only)"
        )

        self.hints = [
            f"Create /etc/yum.repos.d/{self.repo_name}.repo",
            f"Required format:\n[{self.repo_name}]\nname={self.repo_name}\nbaseurl={self.repo_url}\nenabled=1\ngpgcheck=0",
            f"Or use: dnf config-manager --add-repo {self.repo_url}",
            "Verify: dnf repolist",
            "Enable repo: dnf config-manager --enable <repo>"
        ]

        return self

    def validate(self):
        """Validate repository configuration."""
        checks = []
        total_points = 0

        repo_file = f'/etc/yum.repos.d/{self.repo_name}.repo'

        # Check 1: Repo file exists (4 points)
        if validate_file_exists(repo_file):
            checks.append(ValidationCheck(
                name="repo_file_exists",
                passed=True,
                points=4,
                message=f"Repository file exists"
            ))
            total_points += 4

            # Check 2: File has correct section (3 points)
            if validate_file_contains(repo_file, f'[{self.repo_name}]'):
                checks.append(ValidationCheck(
                    name="repo_section",
                    passed=True,
                    points=3,
                    message=f"Repository section [{self.repo_name}] found"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="repo_section",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Repository section [{self.repo_name}] not found"
                ))

            # Check 3: Has baseurl (3 points)
            if validate_file_contains(repo_file, 'baseurl='):
                checks.append(ValidationCheck(
                    name="has_baseurl",
                    passed=True,
                    points=3,
                    message="Repository has baseurl configured"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="has_baseurl",
                    passed=False,
                    points=0,
                    max_points=3,
                    message="Repository missing baseurl"
                ))
        else:
            checks.append(ValidationCheck(
                name="repo_file_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Repository file not found: {repo_file}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class EnableDisableRepoTask(BaseTask):
    """Enable or disable a repository."""

    def __init__(self):
        super().__init__(
            id="pkg_repo_enable_001",
            category="packages",
            difficulty="easy",
            points=6
        )
        self.repo_name = None
        self.action = None

    def generate(self, **params):
        """Generate enable/disable repo task."""
        # Use repos that commonly exist
        repos = ['epel', 'crb', 'baseos', 'appstream']
        self.repo_name = params.get('repo', random.choice(repos))
        self.action = params.get('action', random.choice(['enable', 'disable']))

        self.description = (
            f"{'Enable' if self.action == 'enable' else 'Disable'} a repository:\n"
            f"  - Repository: {self.repo_name}\n"
            f"  - Action: {self.action}\n"
            f"  - Make change persistent"
        )

        self.hints = [
            f"Using dnf: dnf config-manager --{self.action} {self.repo_name}",
            "Or edit /etc/yum.repos.d/<repo>.repo and set enabled=1 or enabled=0",
            "List all repos: dnf repolist all",
            "Show repo status: dnf repoinfo <repo>"
        ]

        return self

    def validate(self):
        """Validate repository enable/disable."""
        checks = []
        total_points = 0

        # Check repo status
        result = execute_safe(['dnf', 'repolist', 'all'])
        if result.success:
            # Look for repo in output
            for line in result.stdout.splitlines():
                if self.repo_name in line.lower():
                    if self.action == 'enable' and 'enabled' in line.lower():
                        checks.append(ValidationCheck(
                            name="repo_status",
                            passed=True,
                            points=6,
                            message=f"Repository {self.repo_name} is enabled"
                        ))
                        total_points += 6
                    elif self.action == 'disable' and 'disabled' in line.lower():
                        checks.append(ValidationCheck(
                            name="repo_status",
                            passed=True,
                            points=6,
                            message=f"Repository {self.repo_name} is disabled"
                        ))
                        total_points += 6
                    else:
                        checks.append(ValidationCheck(
                            name="repo_status",
                            passed=False,
                            points=0,
                            max_points=6,
                            message=f"Repository {self.repo_name} is not {self.action}d"
                        ))
                    break
            else:
                checks.append(ValidationCheck(
                    name="repo_status",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Repository {self.repo_name} not found in repolist"
                ))
        else:
            checks.append(ValidationCheck(
                name="repo_status",
                passed=False,
                points=0,
                max_points=6,
                message="Could not check repository status"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class SearchPackageTask(BaseTask):
    """Search for packages providing a file or feature."""

    def __init__(self):
        super().__init__(
            id="pkg_search_001",
            category="packages",
            difficulty="easy",
            points=6
        )
        self.search_target = None
        self.output_file = None

    def generate(self, **params):
        """Generate package search task."""
        targets = [
            ('/usr/bin/vim', 'the vim command'),
            ('/usr/bin/wget', 'the wget command'),
            ('httpd', 'a web server'),
            ('/etc/passwd', 'the passwd file'),
        ]

        target_choice = params.get('target', random.choice(targets))
        if isinstance(target_choice, tuple):
            self.search_target, target_desc = target_choice
        else:
            self.search_target = target_choice
            target_desc = target_choice

        self.output_file = params.get('output', '/tmp/package_search.txt')

        self.description = (
            f"Find which package provides {target_desc}:\n"
            f"  - Search for: {self.search_target}\n"
            f"  - Save the package name to: {self.output_file}\n"
            f"  - Use dnf provides or similar commands"
        )

        self.hints = [
            f"Find provider: dnf provides {self.search_target}",
            f"Save output: dnf provides {self.search_target} > {self.output_file}",
            "Alternative: dnf whatprovides <file>",
            "Search by keyword: dnf search <keyword>",
            "For installed files: rpm -qf <file>"
        ]

        return self

    def validate(self):
        """Validate package search."""
        checks = []
        total_points = 0

        # Check: Output file exists and has content
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=3,
                message="Output file exists"
            ))
            total_points += 3

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=True,
                            points=3,
                            message="Search results saved to file"
                        ))
                        total_points += 3
                    else:
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=False,
                            points=0,
                            max_points=3,
                            message="Output file is empty"
                        ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="has_results",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=3,
                message="Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class PackageHistoryTask(BaseTask):
    """Use dnf history to view and manage transactions."""

    def __init__(self):
        super().__init__(
            id="pkg_history_001",
            category="packages",
            difficulty="medium",
            points=8
        )
        self.output_file = None

    def generate(self, **params):
        """Generate package history task."""
        self.output_file = params.get('output', '/tmp/dnf_history.txt')

        self.description = (
            f"Work with package transaction history:\n"
            f"  - View dnf transaction history\n"
            f"  - Save the last 10 transactions to: {self.output_file}\n"
            f"  - Include transaction ID, date, and action"
        )

        self.hints = [
            "View history: dnf history",
            "View specific transaction: dnf history info <id>",
            f"Save history: dnf history | head -20 > {self.output_file}",
            "Undo transaction: dnf history undo <id>",
            "Redo transaction: dnf history redo <id>"
        ]

        return self

    def validate(self):
        """Validate package history task."""
        checks = []
        total_points = 0

        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=4,
                message="History output file exists"
            ))
            total_points += 4

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    # Check for typical dnf history output indicators
                    if 'ID' in content or 'Command' in content or 'install' in content.lower():
                        checks.append(ValidationCheck(
                            name="valid_history",
                            passed=True,
                            points=4,
                            message="File contains transaction history"
                        ))
                        total_points += 4
                    elif content.strip():
                        checks.append(ValidationCheck(
                            name="valid_history",
                            passed=True,
                            points=2,
                            message="File has content (partial credit)"
                        ))
                        total_points += 2
                    else:
                        checks.append(ValidationCheck(
                            name="valid_history",
                            passed=False,
                            points=0,
                            max_points=4,
                            message="File is empty"
                        ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="valid_history",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=4,
                message="Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("packages")
class ModuleStreamTask(BaseTask):
    """Enable and install a module stream."""

    def __init__(self):
        super().__init__(
            id="pkg_module_001",
            category="packages",
            difficulty="medium",
            points=10
        )
        self.module_name = None
        self.stream = None

    def generate(self, **params):
        """Generate module stream task."""
        # Common modules with streams
        modules = [
            ('nodejs', '18'),
            ('php', '8.1'),
            ('python', '3.11'),
            ('ruby', '3.1'),
        ]

        module_choice = params.get('module', random.choice(modules))
        if isinstance(module_choice, tuple):
            self.module_name, self.stream = module_choice
        else:
            self.module_name = module_choice
            self.stream = 'default'

        self.description = (
            f"Enable and install a module stream:\n"
            f"  - Module: {self.module_name}\n"
            f"  - Stream: {self.stream}\n"
            f"  - Enable the stream and install the module"
        )

        self.hints = [
            f"List streams: dnf module list {self.module_name}",
            f"Enable stream: dnf module enable {self.module_name}:{self.stream} -y",
            f"Install module: dnf module install {self.module_name}:{self.stream} -y",
            f"Or combined: dnf module install {self.module_name}:{self.stream} -y",
            "Reset module: dnf module reset <module>"
        ]

        return self

    def validate(self):
        """Validate module stream."""
        checks = []
        total_points = 0

        # Check 1: Module is enabled (5 points)
        result = execute_safe(['dnf', 'module', 'list', '--enabled', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=True,
                points=5,
                message=f"Module {self.module_name} is enabled"
            ))
            total_points += 5

            # Check if correct stream (2 points)
            if self.stream in result.stdout:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=True,
                    points=2,
                    message=f"Stream {self.stream} is active"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=True,
                    points=1,
                    message="Module enabled but different stream"
                ))
                total_points += 1
        else:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=False,
                points=0,
                max_points=5,
                message=f"Module {self.module_name} is not enabled"
            ))

        # Check 2: Module packages installed (3 points)
        result = execute_safe(['dnf', 'module', 'list', '--installed', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_installed",
                passed=True,
                points=3,
                message=f"Module {self.module_name} packages installed"
            ))
            total_points += 3
        else:
            # Might still get partial credit if just enabled
            checks.append(ValidationCheck(
                name="module_installed",
                passed=False,
                points=0,
                max_points=3,
                message="Module packages not installed (run: dnf module install)"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
