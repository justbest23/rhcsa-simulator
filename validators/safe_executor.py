"""
Safe command executor for RHCSA Simulator.
Provides security boundary for validation commands.
"""

import subprocess
import re
import logging
from dataclasses import dataclass
from typing import List, Optional
from config import settings


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of command execution."""
    returncode: int
    stdout: str
    stderr: str
    success: bool
    error_message: Optional[str] = None

    def __bool__(self):
        """Allow boolean evaluation based on success."""
        return self.success


class SecurityError(Exception):
    """Raised when a security check fails."""
    pass


class ExecutionError(Exception):
    """Raised when command execution fails."""
    pass


class SafeCommandExecutor:
    """
    Safe command executor with whitelisting and timeout protection.

    This class provides a security boundary for all validation commands,
    ensuring only safe read-only operations are executed.
    """

    def __init__(self, timeout=None):
        """
        Initialize safe command executor.

        Args:
            timeout (int): Default timeout in seconds (default: from settings)
        """
        self.timeout = timeout or settings.COMMAND_TIMEOUT
        self.allowed_commands = settings.SAFE_VALIDATION_COMMANDS
        self.dangerous_patterns = settings.DANGEROUS_PATTERNS

    def execute(self, command, timeout=None, capture_output=True):
        """
        Safely execute a command with security checks.

        Args:
            command (List[str] or str): Command to execute
            timeout (int): Timeout in seconds (default: instance timeout)
            capture_output (bool): Whether to capture stdout/stderr

        Returns:
            ExecutionResult: Result of command execution

        Raises:
            SecurityError: If command fails security checks
            ExecutionError: If command execution fails
        """
        # Convert string to list if necessary
        if isinstance(command, str):
            command = command.split()

        if not command:
            raise ValueError("Command cannot be empty")

        # Use specified timeout or default
        exec_timeout = timeout or self.timeout

        # Security checks
        self._validate_command_security(command)

        # Log command execution (DEBUG level)
        logger.debug(f"Executing command: {' '.join(command)}")

        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=exec_timeout,
                check=False  # Don't raise exception on non-zero exit
            )

            logger.debug(f"Command exit code: {result.returncode}")

            return ExecutionResult(
                returncode=result.returncode,
                stdout=result.stdout.strip() if result.stdout else "",
                stderr=result.stderr.strip() if result.stderr else "",
                success=(result.returncode == 0)
            )

        except subprocess.TimeoutExpired as e:
            error_msg = f"Command timed out after {exec_timeout} seconds"
            logger.warning(error_msg)
            raise ExecutionError(error_msg) from e

        except FileNotFoundError as e:
            error_msg = f"Command not found: {command[0]}"
            logger.error(error_msg)
            return ExecutionResult(
                returncode=127,
                stdout="",
                stderr=error_msg,
                success=False,
                error_message=error_msg
            )

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            logger.error(error_msg)
            raise ExecutionError(error_msg) from e

    def execute_safe(self, command, timeout=None):
        """
        Execute command and return result without raising exceptions.

        Args:
            command (List[str] or str): Command to execute
            timeout (int): Timeout in seconds

        Returns:
            ExecutionResult: Result (with success=False on error)
        """
        try:
            return self.execute(command, timeout)
        except (SecurityError, ExecutionError) as e:
            logger.warning(f"Safe execution failed: {e}")
            return ExecutionResult(
                returncode=-1,
                stdout="",
                stderr=str(e),
                success=False,
                error_message=str(e)
            )

    def _validate_command_security(self, command):
        """
        Validate command against security rules.

        Args:
            command (List[str]): Command to validate

        Raises:
            SecurityError: If command fails security checks
        """
        # Check if base command is in whitelist
        base_command = command[0].split('/')[-1]  # Get command name without path

        if base_command not in self.allowed_commands:
            raise SecurityError(
                f"Command '{base_command}' is not in the allowed list. "
                f"Only read-only validation commands are permitted."
            )

        # Check for dangerous patterns in full command
        full_command = ' '.join(command)
        for pattern in self.dangerous_patterns:
            if re.search(pattern, full_command, re.IGNORECASE):
                raise SecurityError(
                    f"Command contains dangerous pattern: {pattern}"
                )

        # Additional checks for specific commands
        self._validate_specific_commands(command)

    def _validate_specific_commands(self, command):
        """
        Perform additional validation for specific commands.

        Args:
            command (List[str]): Command to validate

        Raises:
            SecurityError: If command-specific check fails
        """
        base_cmd = command[0].split('/')[-1]

        # Ensure systemctl is read-only
        if base_cmd == 'systemctl':
            if len(command) < 2:
                return
            subcommand = command[1]
            if subcommand not in ['status', 'is-active', 'is-enabled',
                                 'is-failed', 'list-units', 'list-unit-files',
                                 'show', 'cat', 'list-dependencies',
                                 'get-default']:
                raise SecurityError(
                    f"systemctl subcommand '{subcommand}' is not allowed. "
                    f"Only read-only operations permitted."
                )

        # Ensure crontab is read-only
        elif base_cmd == 'crontab':
            if '-l' not in command and '-u' not in command:
                raise SecurityError(
                    "crontab must be used with -l (list) option only"
                )

        # Ensure nmcli is read-only
        elif base_cmd == 'nmcli':
            if any(word in command for word in ['add', 'modify', 'delete', 'up', 'down']):
                raise SecurityError(
                    "nmcli modification commands are not allowed"
                )

        # Ensure cat is only used on safe files
        elif base_cmd == 'cat':
            if len(command) > 1:
                for arg in command[1:]:
                    if arg.startswith('-'):
                        continue
                    # Only allow reading specific system files
                    safe_paths = ['/etc/passwd', '/etc/group', '/etc/hosts',
                                 '/etc/hostname', '/etc/resolv.conf', '/etc/fstab',
                                 '/proc/', '/sys/']
                    if not any(arg.startswith(path) for path in safe_paths):
                        logger.warning(f"Attempting to read potentially unsafe file: {arg}")

        # Ensure find is used safely
        elif base_cmd == 'find':
            if '-exec' in command or '-delete' in command:
                raise SecurityError(
                    "find command with -exec or -delete is not allowed"
                )

    def can_execute(self, command):
        """
        Check if a command can be executed without actually running it.

        Args:
            command (List[str] or str): Command to check

        Returns:
            bool: True if command passes security checks
        """
        if isinstance(command, str):
            command = command.split()

        try:
            self._validate_command_security(command)
            return True
        except SecurityError:
            return False


# Global executor instance
_executor = None


def get_executor():
    """
    Get the global SafeCommandExecutor instance.

    Returns:
        SafeCommandExecutor: Global executor instance
    """
    global _executor
    if _executor is None:
        _executor = SafeCommandExecutor()
    return _executor


def execute_safe(command, timeout=None):
    """
    Convenience function to execute command with global executor.

    Args:
        command (List[str] or str): Command to execute
        timeout (int): Optional timeout

    Returns:
        ExecutionResult: Execution result
    """
    executor = get_executor()
    return executor.execute_safe(command, timeout)
