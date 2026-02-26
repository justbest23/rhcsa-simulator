"""
Tests for core.reboot_engine - Boot checks, persistence re-validation, RebootResult.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.reboot_engine import RebootEngine
from core.validator import ValidationResult, RebootResult


pytestmark = pytest.mark.unit


@pytest.fixture
def engine():
    return RebootEngine()


class TestBootChecks:
    """Test boot-critical validation."""

    @patch("core.reboot_engine.execute_safe")
    def test_boot_success_when_all_pass(self, mock_exec, engine):
        mock_exec.return_value = MagicMock(
            success=True, stdout="multi-user.target", stderr=""
        )
        success, blockers = engine._check_boot_critical()
        assert success is True
        assert blockers == []

    @patch("core.reboot_engine.execute_safe")
    def test_boot_failure_with_fstab_error(self, mock_exec, engine):
        def side_effect(cmd, *args, **kwargs):
            if "findmnt" in cmd:
                return MagicMock(success=True, stderr="error in fstab", stdout="")
            elif "systemctl" in cmd:
                return MagicMock(success=True, stdout="multi-user.target", stderr="")
            elif "test" in cmd:
                return MagicMock(success=True, stdout="", stderr="")
            return MagicMock(success=True, stdout="", stderr="")

        mock_exec.side_effect = side_effect
        success, blockers = engine._check_boot_critical()
        assert success is False
        assert any("fstab" in b.lower() for b in blockers)


class TestPersistenceRevalidation:
    """Test persistence re-validation during reboot simulation."""

    @patch.object(RebootEngine, "_check_boot_critical")
    def test_persistence_identifies_lost_tasks(self, mock_boot, engine, sample_task, failing_task):
        mock_boot.return_value = (True, [])

        # sample_task passes initially, failing_task fails
        initial_results = {
            sample_task.id: ValidationResult(
                task_id=sample_task.id, passed=True, score=10, max_score=10
            ),
            failing_task.id: ValidationResult(
                task_id=failing_task.id, passed=False, score=0, max_score=15
            ),
        }

        # Make sample_task require persistence but fail persistence check
        sample_task.requires_persistence = True

        def bad_persistence():
            return ValidationResult(
                task_id=sample_task.id, passed=False, score=0, max_score=10
            )
        sample_task.validate_persistence = bad_persistence

        result = engine.simulate_reboot(
            [sample_task, failing_task], initial_results
        )
        assert result.boot_success is True
        assert sample_task.id in result.tasks_lost_points

    @patch.object(RebootEngine, "_check_boot_critical")
    def test_boot_failure_returns_no_persistence(self, mock_boot, engine, sample_task):
        mock_boot.return_value = (False, ["Invalid fstab"])
        initial_results = {
            sample_task.id: ValidationResult(
                task_id=sample_task.id, passed=True, score=10, max_score=10
            ),
        }
        result = engine.simulate_reboot([sample_task], initial_results)
        assert result.boot_success is False
        assert len(result.persistence_results) == 0


class TestRebootReport:
    """Test report generation."""

    def test_boot_failure_report(self, engine):
        rr = RebootResult(
            boot_success=False,
            boot_blockers=["Invalid fstab"],
        )
        report = engine.get_reboot_report(rr, [])
        assert "FAILED TO BOOT" in report
        assert "fstab" in report.lower()

    def test_boot_success_report(self, engine, sample_task):
        vr = ValidationResult(
            task_id=sample_task.id, passed=True, score=10, max_score=10
        )
        rr = RebootResult(
            boot_success=True,
            persistence_results={sample_task.id: vr},
            tasks_lost_points=[],
        )
        report = engine.get_reboot_report(rr, [sample_task])
        assert "booted successfully" in report.lower()
        assert "Passed: 1" in report
