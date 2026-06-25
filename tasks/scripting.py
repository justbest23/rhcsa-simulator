"""
Shell scripting tasks for RHCSA exam.
"""

import random
import os
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists


logger = logging.getLogger(__name__)


@TaskRegistry.register("scripting")
class CreateBasicScriptTask(BaseTask):
    """Create a basic shell script."""

    def __init__(self):
        super().__init__(
            id="script_basic_001",
            category="scripting",
            difficulty="easy",
            points=8
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "Always start with #!/bin/bash shebang",
            "Make executable: chmod +x script.sh",
            "Test syntax: bash -n script.sh",
        ]
        self.script_path = None
        self.script_purpose = None

    def generate(self, **params):
        """Generate basic script task."""
        purposes = [
            ('list_users', 'print all usernames from /etc/passwd to stdout, one per line'),
            ('disk_usage', 'display the disk usage summary of the /home directory'),
            ('system_info', 'display the system hostname followed by the kernel version'),
        ]

        self.script_purpose, purpose_desc = params.get('purpose', random.choice(purposes))
        self.script_path = params.get('path', f'/usr/local/bin/{self.script_purpose}.sh')

        if self.script_purpose == 'list_users':
            expected_content = "cut -d: -f1 /etc/passwd"
        elif self.script_purpose == 'disk_usage':
            expected_content = "du -sh /home"
        else:
            expected_content = "hostname; uname -r"

        self.description = (
            f"Create a shell script at '{self.script_path}' that:\n"
            f"  - Starts with a proper shebang line\n"
            f"  - When executed, will {purpose_desc}\n"
            f"  - Is executable by root"
        )

        self.hints = [
            f"Create with: vim {self.script_path}",
            "A shebang line identifies the interpreter (first line of every bash script)",
            f"Make executable: chmod +x {self.script_path}",
            f"Test syntax without running: bash -n {self.script_path}",
            f"Run to verify output: {self.script_path}",
        ]

        self._expected_content = expected_content

        return self

    def validate(self):
        """Validate basic script creation."""
        checks = []
        total_points = 0

        # Check 1: Script file exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message=f"Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Script file not found: {self.script_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script has shebang (2 points)
        try:
            with open(self.script_path, 'r') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#!/bin/bash') or first_line.startswith('#!/usr/bin/bash'):
                    checks.append(ValidationCheck(
                        name="has_shebang",
                        passed=True,
                        points=2,
                        message="Script has proper shebang"
                    ))
                    total_points += 2
                elif first_line.startswith('#!'):
                    checks.append(ValidationCheck(
                        name="has_shebang",
                        passed=True,
                        points=1,
                        message=f"Script has shebang but not bash: {first_line}"
                    ))
                    total_points += 1
                else:
                    checks.append(ValidationCheck(
                        name="has_shebang",
                        passed=False,
                        points=0,
                        max_points=2,
                        message="Script missing shebang (#!/bin/bash)"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="has_shebang",
                passed=False,
                points=0,
                max_points=2,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Script is executable (2 points)
        if os.access(self.script_path, os.X_OK):
            checks.append(ValidationCheck(
                name="is_executable",
                passed=True,
                points=2,
                message="Script is executable"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="is_executable",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable (chmod +x)"
            ))

        # Check 4: Script runs without error (2 points)
        result = execute_safe(['bash', '-n', self.script_path])
        if result.success:
            checks.append(ValidationCheck(
                name="valid_syntax",
                passed=True,
                points=2,
                message="Script has valid bash syntax"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="valid_syntax",
                passed=False,
                points=0,
                max_points=2,
                message=f"Script has syntax errors: {result.stderr}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scripting")
class ScriptWithArgumentsTask(BaseTask):
    """Create a script that uses command-line arguments."""

    def __init__(self):
        super().__init__(
            id="script_args_001",
            category="scripting",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "$1, $2 are positional arguments; $@ is all arguments",
            "$# gives the number of arguments",
            "Always validate arguments before using them",
        ]
        self.script_path = None
        self.task_type = None

    def generate(self, **params):
        """Generate script with arguments task."""
        tasks = [
            ('greet', 'Accept a name as argument and print a greeting'),
            ('file_check', 'Accept a filename and check if it exists'),
            ('user_info', 'Accept a username and display their info from /etc/passwd'),
        ]

        self.task_type, task_desc = params.get('task', random.choice(tasks))
        self.script_path = params.get('path', f'/usr/local/bin/{self.task_type}.sh')

        self.description = (
            f"Create a script that accepts arguments:\n"
            f"  - Script path: {self.script_path}\n"
            f"  - Task: {task_desc}\n"
            f"  - Use $1 for the first argument\n"
            f"  - Check if argument is provided, exit with error if not"
        )

        if self.task_type == 'greet':
            example = 'echo "Hello, $1!"'
        elif self.task_type == 'file_check':
            example = 'if [ -f "$1" ]; then echo "exists"; else echo "not found"; fi'
        else:
            example = 'grep "^$1:" /etc/passwd'

        self.hints = [
            "$1 = first argument, $2 = second, $@ = all arguments",
            "$# = number of arguments",
            f"Example content: {example}",
            'Check args: if [ $# -eq 0 ]; then echo "Usage: $0 <arg>"; exit 1; fi',
            f"Test: {self.script_path} testvalue"
        ]

        return self

    def validate(self):
        """Validate script with arguments."""
        checks = []
        total_points = 0

        # Check 1: Script exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message="Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Script not found: {self.script_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script uses arguments (4 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                if '$1' in content or '$@' in content or '${1}' in content:
                    checks.append(ValidationCheck(
                        name="uses_arguments",
                        passed=True,
                        points=4,
                        message="Script uses positional arguments"
                    ))
                    total_points += 4
                else:
                    checks.append(ValidationCheck(
                        name="uses_arguments",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Script doesn't use $1 or positional arguments"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="uses_arguments",
                passed=False,
                points=0,
                max_points=4,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Script checks for missing arguments (2 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                if '$#' in content or '-z "$1"' in content or '-z "${1}"' in content or '[ $# ' in content:
                    checks.append(ValidationCheck(
                        name="checks_args",
                        passed=True,
                        points=2,
                        message="Script validates argument count"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="checks_args",
                        passed=True,
                        points=1,
                        message="Script works but doesn't validate args (partial)"
                    ))
                    total_points += 1
        except Exception:
            pass

        # Check 4: Script is executable and valid (2 points)
        if os.access(self.script_path, os.X_OK):
            result = execute_safe(['bash', '-n', self.script_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="executable_valid",
                    passed=True,
                    points=2,
                    message="Script is executable with valid syntax"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="executable_valid",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Syntax error: {result.stderr}"
                ))
        else:
            checks.append(ValidationCheck(
                name="executable_valid",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scripting")
class ScriptWithConditionalsTask(BaseTask):
    """Create a script with if/else conditionals."""

    def __init__(self):
        super().__init__(
            id="script_cond_001",
            category="scripting",
            difficulty="medium",
            points=12
        )
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "if [ condition ]; then ... elif ... else ... fi",
            "File tests: -f (file), -d (dir), -e (exists), -r (readable)",
            "String: -z (empty), -n (not empty), = (equal)",
            "Numeric: -eq, -ne, -lt, -gt",
        ]
        self.script_path = None
        self.condition_type = None

    def generate(self, **params):
        """Generate conditional script task."""
        conditions = [
            ('file_type', 'Check if a path is a file, directory, or does not exist'),
            ('user_exists', 'Check if a user exists in /etc/passwd'),
            ('service_status', 'Check if a service is running and report status'),
        ]

        self.condition_type, cond_desc = params.get('condition', random.choice(conditions))
        self.script_path = params.get('path', f'/usr/local/bin/check_{self.condition_type}.sh')

        self.description = (
            f"Create a script with conditionals:\n"
            f"  - Script path: {self.script_path}\n"
            f"  - Task: {cond_desc}\n"
            f"  - Use if/then/else/fi structure\n"
            f"  - Accept input as command-line argument"
        )

        self.hints = [
            "File tests: -f (file), -d (directory), -e (exists)",
            "String tests: -z (empty), -n (not empty), = (equal)",
            "Numeric: -eq, -ne, -lt, -gt, -le, -ge",
            'Structure: if [ condition ]; then ... elif [ ]; then ... else ... fi',
            "Exit codes: exit 0 (success), exit 1 (failure)"
        ]

        return self

    def validate(self):
        """Validate conditional script."""
        checks = []
        total_points = 0

        # Check 1: Script exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message="Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Script not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script has conditionals (5 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                has_if = 'if ' in content or 'if[' in content
                has_then = 'then' in content
                has_fi = 'fi' in content

                if has_if and has_then and has_fi:
                    checks.append(ValidationCheck(
                        name="has_conditionals",
                        passed=True,
                        points=5,
                        message="Script has if/then/fi structure"
                    ))
                    total_points += 5
                elif has_if:
                    checks.append(ValidationCheck(
                        name="has_conditionals",
                        passed=True,
                        points=2,
                        message="Script has if but incomplete structure"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="has_conditionals",
                        passed=False,
                        points=0,
                        max_points=5,
                        message="Script missing if/then/fi conditionals"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="has_conditionals",
                passed=False,
                points=0,
                max_points=5,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Script has else or elif (3 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                if 'else' in content or 'elif' in content:
                    checks.append(ValidationCheck(
                        name="has_else",
                        passed=True,
                        points=3,
                        message="Script handles multiple conditions"
                    ))
                    total_points += 3
                else:
                    checks.append(ValidationCheck(
                        name="has_else",
                        passed=True,
                        points=1,
                        message="Script has if but no else branch (partial)"
                    ))
                    total_points += 1
        except Exception:
            pass

        # Check 4: Valid syntax and executable (2 points)
        if os.access(self.script_path, os.X_OK):
            result = execute_safe(['bash', '-n', self.script_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=True,
                    points=2,
                    message="Script is executable with valid syntax"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Syntax error: {result.stderr}"
                ))
        else:
            checks.append(ValidationCheck(
                name="valid_executable",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scripting")
class ScriptWithLoopsTask(BaseTask):
    """Create a script with for or while loops."""

    def __init__(self):
        super().__init__(
            id="script_loop_001",
            category="scripting",
            difficulty="medium",
            points=12
        )
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "for item in list; do ... done",
            "while [ condition ]; do ... done",
            "C-style: for ((i=0; i<10; i++)); do ... done",
        ]
        self.script_path = None
        self.loop_type = None

    def generate(self, **params):
        """Generate loop script task."""
        loops = [
            ('for_files', 'Loop through all .conf files in /etc and count them'),
            ('for_users', 'Loop through users in /etc/passwd and print usernames'),
            ('for_args', 'Loop through all command-line arguments and print each'),
        ]

        self.loop_type, loop_desc = params.get('loop', random.choice(loops))
        self.script_path = params.get('path', f'/usr/local/bin/loop_{self.loop_type}.sh')

        self.description = (
            f"Create a script with loops:\n"
            f"  - Script path: {self.script_path}\n"
            f"  - Task: {loop_desc}\n"
            f"  - Use for or while loop\n"
            f"  - Script must be executable"
        )

        self.hints = [
            'for loop: for item in list; do ... done',
            'for files: for f in /etc/*.conf; do echo "$f"; done',
            'for args: for arg in "$@"; do echo "$arg"; done',
            'while loop: while [ condition ]; do ... done',
            'C-style: for ((i=1; i<=10; i++)); do echo $i; done'
        ]

        return self

    def validate(self):
        """Validate loop script."""
        checks = []
        total_points = 0

        # Check 1: Script exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message="Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Script not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script has loop structure (6 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                has_for = 'for ' in content and 'do' in content and 'done' in content
                has_while = 'while ' in content and 'do' in content and 'done' in content
                has_until = 'until ' in content and 'do' in content and 'done' in content

                if has_for or has_while or has_until:
                    loop_type = 'for' if has_for else ('while' if has_while else 'until')
                    checks.append(ValidationCheck(
                        name="has_loop",
                        passed=True,
                        points=6,
                        message=f"Script has {loop_type} loop structure"
                    ))
                    total_points += 6
                elif 'do' in content and 'done' in content:
                    checks.append(ValidationCheck(
                        name="has_loop",
                        passed=True,
                        points=3,
                        message="Script has do/done but incomplete loop"
                    ))
                    total_points += 3
                else:
                    checks.append(ValidationCheck(
                        name="has_loop",
                        passed=False,
                        points=0,
                        max_points=6,
                        message="Script missing loop structure (for/while/until)"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="has_loop",
                passed=False,
                points=0,
                max_points=6,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Loop uses iteration variable (2 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                # Look for variable usage inside loop
                if '$' in content:
                    checks.append(ValidationCheck(
                        name="uses_variable",
                        passed=True,
                        points=2,
                        message="Script uses variables in loop"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="uses_variable",
                        passed=False,
                        points=0,
                        max_points=2,
                        message="Loop doesn't use variables"
                    ))
        except Exception:
            pass

        # Check 4: Valid syntax and executable (2 points)
        if os.access(self.script_path, os.X_OK):
            result = execute_safe(['bash', '-n', self.script_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=True,
                    points=2,
                    message="Script is executable with valid syntax"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Syntax error: {result.stderr}"
                ))
        else:
            checks.append(ValidationCheck(
                name="valid_executable",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scripting")
class ScriptExitCodesTask(BaseTask):
    """Create a script that handles exit codes properly."""

    def __init__(self):
        super().__init__(
            id="script_exit_001",
            category="scripting",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "exit 0 = success, exit 1 = general error",
            "$? holds the exit code of the last command",
            "Use different exit codes for different error conditions",
        ]
        self.script_path = None

    def generate(self, **params):
        """Generate exit code handling task."""
        self.script_path = params.get('path', '/usr/local/bin/check_and_exit.sh')

        self.description = (
            f"Create a script that handles exit codes:\n"
            f"  - Script path: {self.script_path}\n"
            f"  - Accept a file path as argument\n"
            f"  - Exit 0 if file exists and is readable\n"
            f"  - Exit 1 if file doesn't exist\n"
            f"  - Exit 2 if file exists but isn't readable\n"
            f"  - Print appropriate message for each case"
        )

        self.hints = [
            "Check exit code of last command: $?",
            "Exit with code: exit 0, exit 1, exit 2",
            "Test readability: [ -r \"$1\" ]",
            "Test existence: [ -e \"$1\" ]",
            "Combine: cmd && echo success || echo failed"
        ]

        return self

    def validate(self):
        """Validate exit code script."""
        checks = []
        total_points = 0

        # Check 1: Script exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message="Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Script not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script uses exit command (4 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                exit_count = content.count('exit ')
                if exit_count >= 2:
                    checks.append(ValidationCheck(
                        name="uses_exit",
                        passed=True,
                        points=4,
                        message=f"Script uses multiple exit codes ({exit_count} found)"
                    ))
                    total_points += 4
                elif exit_count == 1:
                    checks.append(ValidationCheck(
                        name="uses_exit",
                        passed=True,
                        points=2,
                        message="Script uses exit but only one code"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="uses_exit",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Script doesn't use exit command"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="uses_exit",
                passed=False,
                points=0,
                max_points=4,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Script checks conditions (2 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                has_file_test = '-e' in content or '-f' in content or '-r' in content
                if has_file_test:
                    checks.append(ValidationCheck(
                        name="checks_conditions",
                        passed=True,
                        points=2,
                        message="Script tests file conditions"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="checks_conditions",
                        passed=False,
                        points=0,
                        max_points=2,
                        message="Script doesn't test file conditions"
                    ))
        except Exception:
            pass

        # Check 4: Valid syntax and executable (2 points)
        if os.access(self.script_path, os.X_OK):
            result = execute_safe(['bash', '-n', self.script_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=True,
                    points=2,
                    message="Script is executable with valid syntax"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Syntax error: {result.stderr}"
                ))
        else:
            checks.append(ValidationCheck(
                name="valid_executable",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("scripting")
class ScriptCommandSubstitutionTask(BaseTask):
    """Create a script using command substitution."""

    def __init__(self):
        super().__init__(
            id="script_cmdsub_001",
            category="scripting",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "Modern syntax: VAR=$(command) - preferred",
            "Legacy syntax: VAR=`command` - avoid nesting issues",
            "Can be nested: $(command1 $(command2))",
        ]
        self.script_path = None
        self.task_type = None

    def generate(self, **params):
        """Generate command substitution task."""
        tasks = [
            ('count_users', 'Count the number of users and store in a variable'),
            ('current_date', 'Get current date and include in a filename'),
            ('disk_free', 'Get available disk space and check if below threshold'),
        ]

        self.task_type, task_desc = params.get('task', random.choice(tasks))
        self.script_path = params.get('path', f'/usr/local/bin/{self.task_type}.sh')

        self.description = (
            f"Create a script using command substitution:\n"
            f"  - Script path: {self.script_path}\n"
            f"  - Task: {task_desc}\n"
            f"  - Use $(command) or `command` syntax\n"
            f"  - Store command output in a variable"
        )

        self.hints = [
            "Modern syntax: VAR=$(command)  — preferred over backticks",
            "Legacy syntax: VAR=`command`",
            "Make the script executable: chmod +x " + self.script_path,
            'Use the variable after assignment: echo "$VAR"',
        ]

        return self

    def validate(self):
        """Validate command substitution script."""
        checks = []
        total_points = 0

        # Check 1: Script exists (2 points)
        if validate_file_exists(self.script_path):
            checks.append(ValidationCheck(
                name="script_exists",
                passed=True,
                points=2,
                message="Script file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="script_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Script not found"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Script uses command substitution (4 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                has_modern = '$(' in content and ')' in content
                has_legacy = '`' in content

                if has_modern:
                    checks.append(ValidationCheck(
                        name="uses_cmd_sub",
                        passed=True,
                        points=4,
                        message="Script uses $() command substitution"
                    ))
                    total_points += 4
                elif has_legacy:
                    checks.append(ValidationCheck(
                        name="uses_cmd_sub",
                        passed=True,
                        points=3,
                        message="Script uses backticks (prefer $() syntax)"
                    ))
                    total_points += 3
                else:
                    checks.append(ValidationCheck(
                        name="uses_cmd_sub",
                        passed=False,
                        points=0,
                        max_points=4,
                        message="Script doesn't use command substitution"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="uses_cmd_sub",
                passed=False,
                points=0,
                max_points=4,
                message=f"Could not read script: {e}"
            ))

        # Check 3: Stores in variable (2 points)
        try:
            with open(self.script_path, 'r') as f:
                content = f.read()
                # Look for VAR=$( or VAR=`
                import re
                if re.search(r'[A-Z_][A-Z_0-9]*=\$\(', content) or re.search(r'[A-Z_][A-Z_0-9]*=`', content):
                    checks.append(ValidationCheck(
                        name="stores_variable",
                        passed=True,
                        points=2,
                        message="Script stores command output in variable"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="stores_variable",
                        passed=True,
                        points=1,
                        message="Command substitution used but not stored in variable"
                    ))
                    total_points += 1
        except Exception:
            pass

        # Check 4: Valid syntax and executable (2 points)
        if os.access(self.script_path, os.X_OK):
            result = execute_safe(['bash', '-n', self.script_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=True,
                    points=2,
                    message="Script is executable with valid syntax"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="valid_executable",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Syntax error: {result.stderr}"
                ))
        else:
            checks.append(ValidationCheck(
                name="valid_executable",
                passed=False,
                points=0,
                max_points=2,
                message="Script is not executable"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
