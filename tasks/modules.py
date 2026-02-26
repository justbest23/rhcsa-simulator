"""
Module stream management tasks for RHCSA EX200 v10 exam.
Covers enabling, installing, and switching DNF module streams.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


@TaskRegistry.register("modules")
class EnableModuleStreamTask(BaseTask):
    """Enable a specific module stream without installing packages."""

    def __init__(self):
        super().__init__(
            id="mod_enable_001",
            category="modules",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf module enable <module>:<stream> enables a stream",
            "Enabling a stream does NOT install packages",
            "Only one stream per module can be active at a time",
            "Use dnf module list to see available modules and streams",
            "Use dnf module list --enabled to verify",
        ]
        self.module_name = None
        self.stream = None

    def generate(self, **params):
        """Generate module stream enable task."""
        modules = [
            ('nodejs', ['18', '20']),
            ('php', ['8.1', '8.2']),
            ('python', ['3.9', '3.11']),
            ('ruby', ['3.1', '3.3']),
            ('nginx', ['1.22', '1.24']),
            ('postgresql', ['13', '15']),
            ('maven', ['3.8']),
            ('redis', ['6', '7']),
        ]

        module_choice = params.get('module', random.choice(modules))
        if isinstance(module_choice, tuple):
            self.module_name = module_choice[0]
            self.stream = params.get('stream', random.choice(module_choice[1]))
        else:
            self.module_name = module_choice
            self.stream = params.get('stream', 'default')

        self.description = (
            f"Enable a module stream:\n"
            f"  - Module: {self.module_name}\n"
            f"  - Stream: {self.stream}\n"
            f"  - Enable the stream (do not install packages yet)\n"
            f"  - Verify the stream is enabled"
        )

        self.hints = [
            f"List available streams: dnf module list {self.module_name}",
            f"Enable stream: dnf module enable {self.module_name}:{self.stream} -y",
            f"Verify: dnf module list --enabled {self.module_name}",
            "Note: enabling does not install packages",
            f"Reset if needed: dnf module reset {self.module_name} -y",
        ]

        return self

    def validate(self):
        """Validate that the module stream is enabled."""
        checks = []
        total_points = 0

        # Check 1: Module stream is enabled (6 points)
        result = execute_safe(['dnf', 'module', 'list', '--enabled', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=True,
                points=6,
                message=f"Module {self.module_name} is enabled"
            ))
            total_points += 6

            # Check 2: Correct stream is active (4 points)
            if self.stream in result.stdout:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=True,
                    points=4,
                    message=f"Stream {self.stream} is active"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Module is enabled but stream {self.stream} is not the active stream"
                ))
        else:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=False,
                points=0,
                max_points=6,
                message=f"Module {self.module_name} is not enabled"
            ))
            checks.append(ValidationCheck(
                name="correct_stream",
                passed=False,
                points=0,
                max_points=4,
                message=f"Cannot check stream (module not enabled)"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("modules")
class InstallModuleProfileTask(BaseTask):
    """Install a module stream with a specific profile."""

    def __init__(self):
        super().__init__(
            id="mod_install_profile_001",
            category="modules",
            difficulty="exam",
            points=12
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "dnf module install <module>:<stream>/<profile> -y",
            "Common profiles: default, devel, server, client, common",
            "If no profile specified, the default profile is used",
            "Installing a module also enables its stream",
            "Use dnf module info <module>:<stream> to see available profiles",
        ]
        self.module_name = None
        self.stream = None
        self.profile = None

    def generate(self, **params):
        """Generate module profile installation task."""
        modules = [
            {
                'module': 'nodejs',
                'streams': ['18', '20'],
                'profiles': ['default', 'development', 'minimal', 's2i'],
            },
            {
                'module': 'php',
                'streams': ['8.1', '8.2'],
                'profiles': ['default', 'devel', 'minimal'],
            },
            {
                'module': 'python',
                'streams': ['3.9', '3.11'],
                'profiles': ['common'],
            },
            {
                'module': 'ruby',
                'streams': ['3.1', '3.3'],
                'profiles': ['default'],
            },
            {
                'module': 'nginx',
                'streams': ['1.22', '1.24'],
                'profiles': ['common'],
            },
            {
                'module': 'postgresql',
                'streams': ['13', '15'],
                'profiles': ['server', 'client'],
            },
            {
                'module': 'redis',
                'streams': ['6', '7'],
                'profiles': ['default'],
            },
        ]

        mod = params.get('module', random.choice(modules))
        self.module_name = mod['module']
        self.stream = params.get('stream', random.choice(mod['streams']))
        self.profile = params.get('profile', random.choice(mod['profiles']))

        self.description = (
            f"Install a module stream with a specific profile:\n"
            f"  - Module: {self.module_name}\n"
            f"  - Stream: {self.stream}\n"
            f"  - Profile: {self.profile}\n"
            f"  - Enable the stream and install the profile packages\n"
            f"  - Verify installation"
        )

        self.hints = [
            f"View profiles: dnf module info {self.module_name}:{self.stream}",
            f"Install: dnf module install {self.module_name}:{self.stream}/{self.profile} -y",
            f"Verify enabled: dnf module list --enabled {self.module_name}",
            f"Verify installed: dnf module list --installed {self.module_name}",
            f"Reset first if switching: dnf module reset {self.module_name} -y",
        ]

        return self

    def validate(self):
        """Validate module stream installation with profile."""
        checks = []
        total_points = 0

        # Check 1: Module is enabled (3 points)
        result = execute_safe(['dnf', 'module', 'list', '--enabled', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=True,
                points=3,
                message=f"Module {self.module_name} is enabled"
            ))
            total_points += 3

            # Check 2: Correct stream (3 points)
            if self.stream in result.stdout:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=True,
                    points=3,
                    message=f"Stream {self.stream} is the active stream"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="correct_stream",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Stream {self.stream} is not the active stream"
                ))
        else:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=False,
                points=0,
                max_points=3,
                message=f"Module {self.module_name} is not enabled"
            ))
            checks.append(ValidationCheck(
                name="correct_stream",
                passed=False,
                points=0,
                max_points=3,
                message="Cannot verify stream (module not enabled)"
            ))

        # Check 3: Module packages are installed (3 points)
        result = execute_safe(['dnf', 'module', 'list', '--installed', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_installed",
                passed=True,
                points=3,
                message=f"Module {self.module_name} packages are installed"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="module_installed",
                passed=False,
                points=0,
                max_points=3,
                message=f"Module {self.module_name} packages are not installed"
            ))

        # Check 4: Profile packages installed - check for key package (3 points)
        # Verify by checking if the main package from the module is installed
        result = execute_safe(['rpm', '-q', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="profile_packages",
                passed=True,
                points=3,
                message=f"Profile package {self.module_name} is installed"
            ))
            total_points += 3
        else:
            # For some modules the package name differs (e.g., nodejs vs node)
            # Check via dnf module info for installed profiles
            result2 = execute_safe(['dnf', 'module', 'info', '--installed',
                                    f'{self.module_name}:{self.stream}'])
            if result2.success and self.profile in result2.stdout:
                checks.append(ValidationCheck(
                    name="profile_packages",
                    passed=True,
                    points=3,
                    message=f"Profile '{self.profile}' packages appear to be installed"
                ))
                total_points += 3
            elif result2.success and 'Installed' in result2.stdout:
                checks.append(ValidationCheck(
                    name="profile_packages",
                    passed=True,
                    points=2,
                    max_points=3,
                    message="Module is installed but could not confirm exact profile"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="profile_packages",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Profile '{self.profile}' packages not found"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("modules")
class SwitchModuleStreamTask(BaseTask):
    """Switch a module from one stream to another."""

    def __init__(self):
        super().__init__(
            id="mod_switch_stream_001",
            category="modules",
            difficulty="hard",
            points=15
        )
        self.requires_persistence = False
        self.tags = ['v10-new']
        self.exam_tips = [
            "Switching streams requires: reset, then enable new stream",
            "dnf module reset <module> -y first",
            "Then: dnf module install <module>:<new-stream> -y",
            "You may need to remove old packages first with dnf distro-sync",
            "Some stream switches may require removing the module first",
        ]
        self.module_name = None
        self.from_stream = None
        self.to_stream = None

    def generate(self, **params):
        """Generate module stream switch task."""
        switch_scenarios = [
            {
                'module': 'nodejs',
                'from_stream': '18',
                'to_stream': '20',
            },
            {
                'module': 'php',
                'from_stream': '8.1',
                'to_stream': '8.2',
            },
            {
                'module': 'postgresql',
                'from_stream': '13',
                'to_stream': '15',
            },
            {
                'module': 'nginx',
                'from_stream': '1.22',
                'to_stream': '1.24',
            },
            {
                'module': 'ruby',
                'from_stream': '3.1',
                'to_stream': '3.3',
            },
            {
                'module': 'redis',
                'from_stream': '6',
                'to_stream': '7',
            },
        ]

        scenario = params.get('scenario', random.choice(switch_scenarios))
        self.module_name = scenario['module']
        self.from_stream = scenario['from_stream']
        self.to_stream = scenario['to_stream']

        self.description = (
            f"Switch a module to a different stream:\n"
            f"  - Module: {self.module_name}\n"
            f"  - Current stream: {self.from_stream}\n"
            f"  - Target stream: {self.to_stream}\n"
            f"  - The module is currently enabled with stream {self.from_stream}\n"
            f"  - Switch to stream {self.to_stream} and install its packages\n"
            f"  - Ensure the switch is complete and functional"
        )

        self.hints = [
            f"Step 1: Reset the module: dnf module reset {self.module_name} -y",
            f"Step 2: Install new stream: dnf module install {self.module_name}:{self.to_stream} -y",
            "If packages conflict: dnf module remove {module} -y first, then reset and install",
            f"Alternative: dnf module switch-to {self.module_name}:{self.to_stream} (if available)",
            f"Verify: dnf module list --enabled {self.module_name}",
            "Use dnf distro-sync if packages are outdated after switch",
        ]

        return self

    def validate(self):
        """Validate module stream switch."""
        checks = []
        total_points = 0

        # Check 1: Module is enabled (3 points)
        result = execute_safe(['dnf', 'module', 'list', '--enabled', self.module_name])
        if result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=True,
                points=3,
                message=f"Module {self.module_name} is enabled"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="module_enabled",
                passed=False,
                points=0,
                max_points=3,
                message=f"Module {self.module_name} is not enabled"
            ))
            # Early return - no point checking further
            checks.append(ValidationCheck(
                name="new_stream_active",
                passed=False,
                points=0,
                max_points=5,
                message="Cannot verify stream (module not enabled)"
            ))
            checks.append(ValidationCheck(
                name="old_stream_inactive",
                passed=False,
                points=0,
                max_points=3,
                message="Cannot verify old stream status"
            ))
            checks.append(ValidationCheck(
                name="packages_installed",
                passed=False,
                points=0,
                max_points=4,
                message="Cannot verify packages (module not enabled)"
            ))
            return ValidationResult(self.id, False, 0, self.points, checks)

        # Check 2: New stream is active (5 points)
        if self.to_stream in result.stdout:
            checks.append(ValidationCheck(
                name="new_stream_active",
                passed=True,
                points=5,
                message=f"Stream {self.to_stream} is now the active stream"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="new_stream_active",
                passed=False,
                points=0,
                max_points=5,
                message=f"Stream {self.to_stream} is not the active stream"
            ))

        # Check 3: Old stream is NOT active (3 points)
        # Parse more carefully - look for the stream marker [e] next to stream version
        old_stream_still_active = False
        for line in result.stdout.splitlines():
            if self.module_name in line and self.from_stream in line:
                if '[e]' in line or '[i' in line:
                    old_stream_still_active = True
                    break

        if not old_stream_still_active:
            checks.append(ValidationCheck(
                name="old_stream_inactive",
                passed=True,
                points=3,
                message=f"Old stream {self.from_stream} is no longer active"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="old_stream_inactive",
                passed=False,
                points=0,
                max_points=3,
                message=f"Old stream {self.from_stream} still appears to be active"
            ))

        # Check 4: Module packages installed for new stream (4 points)
        result = execute_safe(['dnf', 'module', 'list', '--installed', self.module_name])
        if result.success and self.module_name in result.stdout and self.to_stream in result.stdout:
            checks.append(ValidationCheck(
                name="packages_installed",
                passed=True,
                points=4,
                message=f"Packages for stream {self.to_stream} are installed"
            ))
            total_points += 4
        elif result.success and self.module_name in result.stdout:
            checks.append(ValidationCheck(
                name="packages_installed",
                passed=False,
                points=2,
                max_points=4,
                message="Module packages installed but could not confirm they are from the new stream"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="packages_installed",
                passed=False,
                points=0,
                max_points=4,
                message=f"Module packages for stream {self.to_stream} are not installed"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
