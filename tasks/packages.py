"""
Package management tasks for RHCSA EX200 v10 exam.
DNF/RPM operations only - repos, flatpak, modules are in separate files.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe

logger = logging.getLogger(__name__)


@TaskRegistry.register("packages")
class InstallPackageTask(BaseTask):
    """Install a package using dnf."""

    def __init__(self):
        super().__init__(id="pkg_install_001", category="packages", difficulty="easy", points=6)
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf install <package> -y to install without prompting",
            "rpm -q <package> to verify installation",
        ]
        self.package_name = None

    def generate(self, **params):
        packages = ['tree', 'wget', 'vim-enhanced', 'tmux', 'htop', 'net-tools', 'bind-utils', 'bash-completion']
        self.package_name = params.get('package', random.choice(packages))
        self.description = (
            f"Install a package using dnf:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Verify installation with rpm -q"
        )
        self.hints = [
            f"Install: dnf install {self.package_name} -y",
            f"Verify: rpm -q {self.package_name}",
            "List installed: dnf list installed",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['rpm', '-q', self.package_name])
        if result.success and self.package_name in result.stdout:
            checks.append(ValidationCheck("package_installed", True, 6, f"Package {self.package_name} is installed"))
            total_points += 6
        else:
            checks.append(ValidationCheck("package_installed", False, 0, f"Package {self.package_name} is not installed", max_points=6))
        return ValidationResult(self.id, total_points >= 4, total_points, self.points, checks)


@TaskRegistry.register("packages")
class RemovePackageTask(BaseTask):
    """Remove a package using dnf."""

    def __init__(self):
        super().__init__(id="pkg_remove_001", category="packages", difficulty="easy", points=6)
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf remove <package> -y to remove",
            "rpm -q <package> should show 'not installed' after removal",
        ]
        self.package_name = None

    def generate(self, **params):
        packages = ['tree', 'wget', 'tmux', 'htop']
        self.package_name = params.get('package', random.choice(packages))
        self.description = (
            f"Remove a package using dnf:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Ensure package is completely removed"
        )
        self.hints = [
            f"Remove: dnf remove {self.package_name} -y",
            f"Verify: rpm -q {self.package_name}",
        ]
        return self

    def validate(self):
        checks = []
        result = execute_safe(['rpm', '-q', self.package_name])
        if not result.success or 'not installed' in result.stdout.lower():
            checks.append(ValidationCheck("package_removed", True, 6, f"Package {self.package_name} removed"))
            return ValidationResult(self.id, True, 6, self.points, checks)
        checks.append(ValidationCheck("package_removed", False, 0, f"Package {self.package_name} still installed", max_points=6))
        return ValidationResult(self.id, False, 0, self.points, checks)


@TaskRegistry.register("packages")
class InstallPackageGroupTask(BaseTask):
    """Install a package group."""

    def __init__(self):
        super().__init__(id="pkg_group_001", category="packages", difficulty="medium", points=8)
        self.tags = ['v10-new']
        self.exam_tips = [
            'dnf group install "Group Name" to install a group',
            "dnf group list to see available groups",
            "Use quotes around group names with spaces",
        ]
        self.group_name = None
        self.group_id = None

    def generate(self, **params):
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
            f'Install: dnf group install "{self.group_name}" -y',
            "List groups: dnf group list",
            f'Group info: dnf group info "{self.group_name}"',
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['dnf', 'group', 'list', 'installed'])
        if result.success and (self.group_name.lower() in result.stdout.lower() or
                               self.group_id in result.stdout.lower()):
            checks.append(ValidationCheck("group_installed", True, 8, f"Package group '{self.group_name}' installed"))
            total_points = 8
        else:
            checks.append(ValidationCheck("group_installed", False, 0, f"Package group '{self.group_name}' not installed", max_points=8))
        return ValidationResult(self.id, total_points >= 6, total_points, self.points, checks)


@TaskRegistry.register("packages")
class QueryPackageInfoTask(BaseTask):
    """Query package information using rpm."""

    def __init__(self):
        super().__init__(id="pkg_query_001", category="packages", difficulty="easy", points=5)
        self.tags = ['v10-new']
        self.exam_tips = [
            "rpm -qi <package> shows detailed info",
            "rpm -ql <package> lists all files in package",
            "dnf info <package> also works",
        ]
        self.package_name = None
        self.output_file = None

    def generate(self, **params):
        packages = ['bash', 'coreutils', 'systemd', 'kernel', 'openssh-server']
        self.package_name = params.get('package', random.choice(packages))
        self.output_file = params.get('output', '/tmp/pkg_info.txt')

        self.description = (
            f"Query detailed package information:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Save package info (name, version, release, summary) to: {self.output_file}\n"
            f"  - Use rpm or dnf info"
        )
        self.hints = [
            f"RPM query: rpm -qi {self.package_name}",
            f"DNF info: dnf info {self.package_name}",
            f"Save: rpm -qi {self.package_name} > {self.output_file}",
            f"List files: rpm -ql {self.package_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['test', '-f', self.output_file])
        if result.success:
            checks.append(ValidationCheck("output_exists", True, 2, "Output file exists"))
            total_points += 2
            result2 = execute_safe(['cat', self.output_file])
            if result2.success and (self.package_name in result2.stdout or 'Name' in result2.stdout):
                checks.append(ValidationCheck("has_info", True, 3, "File contains package info"))
                total_points += 3
            else:
                checks.append(ValidationCheck("has_info", False, 0, "File missing package info", max_points=3))
        else:
            checks.append(ValidationCheck("output_exists", False, 0, "Output file not found", max_points=2))
        return ValidationResult(self.id, total_points >= 3, total_points, self.points, checks)


@TaskRegistry.register("packages")
class FindPackageProviderTask(BaseTask):
    """Find which package provides a file or command."""

    def __init__(self):
        super().__init__(id="pkg_provides_001", category="packages", difficulty="easy", points=6)
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf provides <file_path> finds which package owns a file",
            "rpm -qf <file_path> for installed files only",
        ]
        self.search_target = None
        self.output_file = None

    def generate(self, **params):
        targets = [
            ('/usr/bin/vim', 'the vim command'),
            ('/usr/bin/wget', 'the wget command'),
            ('/usr/sbin/httpd', 'the httpd binary'),
            ('/etc/passwd', 'the passwd file'),
            ('/usr/bin/dig', 'the dig command'),
        ]
        target_choice = params.get('target', random.choice(targets))
        if isinstance(target_choice, tuple):
            self.search_target, self.target_desc = target_choice
        else:
            self.search_target = target_choice
            self.target_desc = target_choice
        self.output_file = params.get('output', '/tmp/package_provider.txt')

        self.description = (
            f"Find which package provides {self.target_desc}:\n"
            f"  - Search for: {self.search_target}\n"
            f"  - Save the result to: {self.output_file}\n"
            f"  - Use dnf provides or rpm -qf"
        )
        self.hints = [
            f"dnf provides {self.search_target}",
            f"rpm -qf {self.search_target} (for installed files)",
            f"Save: dnf provides {self.search_target} > {self.output_file}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['test', '-f', self.output_file])
        if result.success:
            checks.append(ValidationCheck("output_exists", True, 3, "Output file exists"))
            total_points += 3
            result2 = execute_safe(['cat', self.output_file])
            if result2.success and result2.stdout.strip():
                checks.append(ValidationCheck("has_results", True, 3, "File contains search results"))
                total_points += 3
            else:
                checks.append(ValidationCheck("has_results", False, 0, "File is empty", max_points=3))
        else:
            checks.append(ValidationCheck("output_exists", False, 0, "Output file not found", max_points=3))
        return ValidationResult(self.id, total_points >= 4, total_points, self.points, checks)


@TaskRegistry.register("packages")
class PackageHistoryTask(BaseTask):
    """Use dnf history to view and manage transactions."""

    def __init__(self):
        super().__init__(id="pkg_history_001", category="packages", difficulty="medium", points=8)
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf history shows transaction log",
            "dnf history info <id> shows details of a transaction",
            "dnf history undo <id> reverses a transaction",
        ]
        self.output_file = None

    def generate(self, **params):
        self.output_file = params.get('output', '/tmp/dnf_history.txt')
        self.description = (
            f"Work with package transaction history:\n"
            f"  - View dnf transaction history\n"
            f"  - Save the last 10 transactions to: {self.output_file}\n"
            f"  - Include transaction ID, date, and action"
        )
        self.hints = [
            "View history: dnf history",
            f"Save: dnf history | head -20 > {self.output_file}",
            "View specific: dnf history info <id>",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0
        result = execute_safe(['test', '-f', self.output_file])
        if result.success:
            checks.append(ValidationCheck("output_exists", True, 4, "History file exists"))
            total_points += 4
            result2 = execute_safe(['cat', self.output_file])
            if result2.success and ('ID' in result2.stdout or 'Command' in result2.stdout or result2.stdout.strip()):
                checks.append(ValidationCheck("valid_history", True, 4, "File contains history"))
                total_points += 4
            else:
                checks.append(ValidationCheck("valid_history", False, 0, "File is empty", max_points=4))
        else:
            checks.append(ValidationCheck("output_exists", False, 0, "Output file not found", max_points=4))
        return ValidationResult(self.id, total_points >= 5, total_points, self.points, checks)


@TaskRegistry.register("packages")
class VerifyPackageIntegrityTask(BaseTask):
    """Verify package file integrity using rpm."""

    def __init__(self):
        super().__init__(id="pkg_verify_001", category="packages", difficulty="medium", points=8)
        self.tags = ['v10-new']
        self.exam_tips = [
            "rpm -V <package> verifies file integrity",
            "No output means all files match originals",
            "S=size, M=mode, 5=MD5, T=mtime changed",
        ]
        self.package_name = None
        self.output_file = None

    def generate(self, **params):
        packages = ['coreutils', 'bash', 'openssh-server', 'systemd', 'sudo']
        self.package_name = params.get('package', random.choice(packages))
        self.output_file = params.get('output', '/tmp/rpm_verify.txt')

        self.description = (
            f"Verify package file integrity:\n"
            f"  - Package: {self.package_name}\n"
            f"  - Run rpm -V (verify) on the package\n"
            f"  - Save verification output to: {self.output_file}\n"
            f"  - Identify any modified files"
        )
        self.hints = [
            f"Verify: rpm -V {self.package_name}",
            f"Save: rpm -V {self.package_name} > {self.output_file} 2>&1",
            "No output = all files match original",
            "S = size, M = mode, 5 = MD5, T = mtime, U = user, G = group",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check package is installed
        result = execute_safe(['rpm', '-q', self.package_name])
        if result.success:
            checks.append(ValidationCheck("pkg_installed", True, 3, f"{self.package_name} is installed"))
            total_points += 3
        else:
            checks.append(ValidationCheck("pkg_installed", False, 0, f"{self.package_name} not installed", max_points=3))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check output file
        result = execute_safe(['test', '-f', self.output_file])
        if result.success:
            checks.append(ValidationCheck("output_exists", True, 5, "Verification output saved"))
            total_points += 5
        else:
            checks.append(ValidationCheck("output_exists", False, 0, "Output file not found", max_points=5))

        return ValidationResult(self.id, total_points >= 5, total_points, self.points, checks)


@TaskRegistry.register("packages")
class DowngradePackageTask(BaseTask):
    """Downgrade a package to a previous version."""

    def __init__(self):
        super().__init__(id="pkg_downgrade_001", category="packages", difficulty="hard", points=12)
        self.tags = ['v10-new']
        self.package_name = None
        self.exam_tips = [
            "Use 'dnf downgrade <package>' to revert to previous version",
            "Check available versions with 'dnf --showduplicates list <package>'",
            "Use 'dnf history undo <id>' to undo a specific update",
        ]

    def generate(self, **params):
        packages = ['vim-enhanced', 'wget', 'bash-completion', 'nano', 'man-db']
        self.package_name = params.get('package', random.choice(packages))

        self.description = (
            f"Downgrade a package to the previous version:\n"
            f"  - Package: {self.package_name}\n"
            f"  - First, ensure the package is installed and note current version\n"
            f"  - Downgrade to the previous available version\n"
            f"  - Verify the downgrade was successful"
        )
        self.hints = [
            f"Check current: rpm -q {self.package_name}",
            f"List versions: dnf --showduplicates list {self.package_name}",
            f"Downgrade: dnf downgrade {self.package_name} -y",
            f"Or undo last update: dnf history undo last -y",
            f"Verify: rpm -q {self.package_name}",
        ]
        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check package is installed
        result = execute_safe(['rpm', '-q', self.package_name])
        if result.success:
            checks.append(ValidationCheck("pkg_installed", True, 4, f"{self.package_name} is installed"))
            total_points += 4

            # Check dnf history for downgrade action
            result2 = execute_safe(['dnf', 'history'])
            if result2.success and ('downgrad' in result2.stdout.lower() or 'undo' in result2.stdout.lower()):
                checks.append(ValidationCheck("downgrade_done", True, 8, "Downgrade action found in history"))
                total_points += 8
            else:
                checks.append(ValidationCheck("downgrade_done", False, 0, "No downgrade action found in dnf history", max_points=8))
        else:
            checks.append(ValidationCheck("pkg_installed", False, 0, f"{self.package_name} not installed", max_points=4))

        return ValidationResult(self.id, total_points >= 8, total_points, self.points, checks)
