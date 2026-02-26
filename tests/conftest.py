"""
Shared fixtures for RHCSA Simulator v4.0.0 test suite.
"""

import sys
import os
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary ResultsDB backed by a temp SQLite file."""
    from core.results_db import ResultsDB
    db_path = tmp_path / "test_results.db"
    return ResultsDB(db_path=db_path)


@pytest.fixture
def sample_task():
    """Return a SimpleTask instance with known properties."""
    from tasks.base import SimpleTask
    from core.validator import ValidationResult, ValidationCheck

    def validation_func():
        return ValidationResult(
            task_id="test-task-001",
            passed=True,
            score=10,
            max_score=10,
            checks=[
                ValidationCheck(
                    name="test_check",
                    passed=True,
                    points=10,
                    message="Test passed",
                )
            ],
        )

    task = SimpleTask(
        id="test-task-001",
        category="users_groups",
        difficulty="exam",
        points=10,
        description="Create user testuser with UID 1500",
        validation_func=validation_func,
    )
    task.tags = ["user-management", "exam-critical"]
    task.exam_tips = ["Always verify with 'id' command"]
    task.requires_persistence = True
    return task


@pytest.fixture
def failing_task():
    """Return a SimpleTask that always fails validation."""
    from tasks.base import SimpleTask
    from core.validator import ValidationResult, ValidationCheck

    def validation_func():
        return ValidationResult(
            task_id="test-task-fail",
            passed=False,
            score=0,
            max_score=15,
            checks=[
                ValidationCheck(
                    name="fail_check",
                    passed=False,
                    points=0,
                    message="User not found",
                    max_points=15,
                )
            ],
        )

    task = SimpleTask(
        id="test-task-fail",
        category="lvm",
        difficulty="hard",
        points=15,
        description="Create LV data on vg_test",
        validation_func=validation_func,
    )
    return task


@pytest.fixture(scope="session")
def initialized_registry():
    """Initialize the TaskRegistry once per test session."""
    from tasks.registry import TaskRegistry
    TaskRegistry.initialize()
    return TaskRegistry
