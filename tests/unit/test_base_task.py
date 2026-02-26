"""
Tests for tasks.base - BaseTask and SimpleTask interfaces.
"""

import pytest
from tasks.base import SimpleTask
from core.validator import ValidationResult


pytestmark = pytest.mark.unit


class TestSimpleTask:
    """Test SimpleTask instantiation and interface."""

    def test_instantiate_with_all_v4_attributes(self):
        task = SimpleTask(
            id="test-001", category="lvm", difficulty="exam", points=15,
            description="Create logical volume",
        )
        assert task.id == "test-001"
        assert task.category == "lvm"
        assert task.difficulty == "exam"
        assert task.points == 15
        assert task.description == "Create logical volume"

    def test_default_tags_empty(self):
        task = SimpleTask(id="t", category="lvm", difficulty="easy", points=5)
        assert task.tags == []

    def test_default_exam_tips_empty(self):
        task = SimpleTask(id="t", category="lvm", difficulty="easy", points=5)
        assert task.exam_tips == []

    def test_default_requires_persistence_false(self):
        task = SimpleTask(id="t", category="lvm", difficulty="easy", points=5)
        assert task.requires_persistence is False

    def test_exam_domain_set_from_category(self):
        task = SimpleTask(id="t", category="lvm", difficulty="exam", points=10)
        # lvm maps to domain 4
        assert task.exam_domain == 4

    def test_generate_returns_self(self):
        task = SimpleTask(id="t", category="lvm", difficulty="easy", points=5)
        result = task.generate()
        assert result is task

    def test_validate_with_func(self):
        def vfunc():
            return ValidationResult(
                task_id="t1", passed=True, score=10, max_score=10
            )
        task = SimpleTask(
            id="t1", category="lvm", difficulty="exam", points=10,
            validation_func=vfunc,
        )
        result = task.validate()
        assert result.passed is True
        assert result.score == 10

    def test_validate_without_func(self):
        task = SimpleTask(
            id="t1", category="lvm", difficulty="exam", points=10,
        )
        result = task.validate()
        assert result.passed is False
        assert "No validation function" in result.error_message

    def test_to_dict(self):
        task = SimpleTask(
            id="t1", category="selinux", difficulty="hard", points=20,
            description="Set SELinux context",
        )
        task.tags = ["selinux"]
        task.exam_tips = ["Use restorecon"]
        d = task.to_dict()
        assert d["id"] == "t1"
        assert d["category"] == "selinux"
        assert d["tags"] == ["selinux"]
        assert d["exam_tips"] == ["Use restorecon"]
        assert d["exam_domain"] == 7  # selinux -> domain 7

    def test_repr(self):
        task = SimpleTask(id="t1", category="lvm", difficulty="exam", points=15)
        r = repr(task)
        assert "t1" in r
        assert "lvm" in r

    def test_validate_persistence_defaults_to_validate(self, sample_task):
        result = sample_task.validate_persistence()
        assert isinstance(result, ValidationResult)
        assert result.passed is True
