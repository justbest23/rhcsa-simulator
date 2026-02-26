"""
Tests for core.validator - ValidationCheck, ValidationResult, ValidationEngine.
"""

import pytest
from core.validator import (
    ValidationCheck,
    ValidationResult,
    ValidationEngine,
    RebootResult,
)


pytestmark = pytest.mark.unit


class TestValidationCheck:
    """Test ValidationCheck dataclass."""

    def test_stores_fields(self):
        check = ValidationCheck(
            name="user_exists", passed=True, points=5, message="User found"
        )
        assert check.name == "user_exists"
        assert check.passed is True
        assert check.points == 5
        assert check.message == "User found"

    def test_max_points_defaults_to_points(self):
        check = ValidationCheck(
            name="test", passed=True, points=10, message="ok"
        )
        assert check.max_points == 10

    def test_max_points_explicit(self):
        check = ValidationCheck(
            name="test", passed=False, points=0, message="fail", max_points=15
        )
        assert check.max_points == 15

    def test_to_dict(self):
        check = ValidationCheck(
            name="check1", passed=True, points=10, message="ok",
            details="extra", persistence_passed=True,
        )
        d = check.to_dict()
        assert d["name"] == "check1"
        assert d["passed"] is True
        assert d["points"] == 10
        assert d["max_points"] == 10
        assert d["message"] == "ok"
        assert d["details"] == "extra"
        assert d["persistence_passed"] is True


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_percentage_calculation(self):
        result = ValidationResult(
            task_id="t1", passed=True, score=8, max_score=10
        )
        assert result.percentage == pytest.approx(80.0)

    def test_percentage_zero_max_score(self):
        result = ValidationResult(
            task_id="t1", passed=False, score=0, max_score=0
        )
        assert result.percentage == 0.0

    def test_to_dict(self):
        check = ValidationCheck(name="c1", passed=True, points=5, message="ok")
        result = ValidationResult(
            task_id="t1", passed=True, score=5, max_score=10, checks=[check]
        )
        d = result.to_dict()
        assert d["task_id"] == "t1"
        assert d["passed"] is True
        assert d["score"] == 5
        assert d["percentage"] == pytest.approx(50.0)
        assert len(d["checks"]) == 1

    def test_get_summary_pass(self):
        result = ValidationResult(
            task_id="t1", passed=True, score=10, max_score=10
        )
        summary = result.get_summary()
        assert "PASS" in summary
        assert "10/10" in summary

    def test_get_summary_fail(self):
        result = ValidationResult(
            task_id="t1", passed=False, score=3, max_score=10
        )
        summary = result.get_summary()
        assert "FAIL" in summary


class TestRebootResult:
    """Test RebootResult dataclass."""

    def test_boot_failure(self):
        rr = RebootResult(
            boot_success=False,
            boot_blockers=["Invalid fstab"],
        )
        assert rr.boot_success is False
        assert len(rr.boot_blockers) == 1

    def test_boot_success_with_persistence(self):
        vr = ValidationResult(task_id="t1", passed=True, score=10, max_score=10)
        rr = RebootResult(
            boot_success=True,
            persistence_results={"t1": vr},
            tasks_lost_points=[],
        )
        assert rr.boot_success is True
        assert "t1" in rr.persistence_results

    def test_to_dict(self):
        rr = RebootResult(boot_success=True)
        d = rr.to_dict()
        assert d["boot_success"] is True
        assert d["boot_blockers"] == []
        assert d["tasks_lost_points"] == []


class TestValidationEngine:
    """Test ValidationEngine methods."""

    def test_validate_task_returns_result(self, sample_task):
        engine = ValidationEngine()
        result = engine.validate_task(sample_task)
        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert result.score == 10

    def test_validate_task_handles_exception(self):
        from tasks.base import SimpleTask

        def bad_validate():
            raise RuntimeError("Boom")

        task = SimpleTask(
            id="bad-task", category="lvm", difficulty="exam",
            points=10, validation_func=bad_validate,
        )
        engine = ValidationEngine()
        result = engine.validate_task(task)
        assert isinstance(result, ValidationResult)
        assert result.passed is False
        assert "Boom" in result.error_message

    def test_calculate_total_score(self, sample_task, failing_task):
        engine = ValidationEngine()
        r1 = engine.validate_task(sample_task)
        r2 = engine.validate_task(failing_task)
        total, max_s, pct = engine.calculate_total_score([r1, r2])
        assert total == 10
        assert max_s == 25
        assert pct == pytest.approx(40.0)

    def test_get_domain_breakdown(self, sample_task):
        engine = ValidationEngine()
        result = engine.validate_task(sample_task)
        breakdown = engine.get_domain_breakdown([(sample_task, result)])
        domain = sample_task.exam_domain
        assert domain in breakdown
        assert breakdown[domain]["tasks"] == 1

    def test_get_category_breakdown(self, sample_task, failing_task):
        engine = ValidationEngine()
        r1 = engine.validate_task(sample_task)
        r2 = engine.validate_task(failing_task)
        breakdown = engine.get_category_breakdown(
            [(sample_task, r1), (failing_task, r2)]
        )
        assert "users_groups" in breakdown
        assert "lvm" in breakdown
        assert breakdown["users_groups"]["passed"] == 1
        assert breakdown["lvm"]["passed"] == 0

    def test_empty_task_list_breakdown(self):
        engine = ValidationEngine()
        breakdown = engine.get_domain_breakdown([])
        assert breakdown == {}
        breakdown = engine.get_category_breakdown([])
        assert breakdown == {}
