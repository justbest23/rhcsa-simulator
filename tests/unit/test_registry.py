"""
Tests for tasks.registry - Task auto-discovery, exam generation, and lookups.
"""

import pytest
from unittest.mock import patch, MagicMock


pytestmark = [pytest.mark.unit, pytest.mark.slow]


# Many task generate() methods call subprocess which hangs on Windows.
# Mock subprocess.run globally for tests that create task instances.
@pytest.fixture(autouse=True)
def mock_subprocess():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_result):
        yield


class TestInitialization:
    """Test registry auto-discovery."""

    def test_initialize_discovers_tasks(self, initialized_registry):
        assert initialized_registry.get_task_count() > 0

    def test_discovers_expected_task_count(self, initialized_registry):
        count = initialized_registry.get_task_count()
        # v4.0.0 has 198 tasks; allow some tolerance for legacy auto-discovered tasks
        assert count >= 190

    def test_discovers_expected_categories(self, initialized_registry):
        cats = initialized_registry.get_all_categories()
        assert len(cats) >= 21  # 21 v4 categories minimum

    def test_get_all_categories_returns_strings(self, initialized_registry):
        cats = initialized_registry.get_all_categories()
        assert all(isinstance(c, str) for c in cats)

    def test_known_categories_present(self, initialized_registry):
        cats = initialized_registry.get_all_categories()
        for expected in ["lvm", "users_groups", "selinux", "networking", "boot"]:
            assert expected in cats


class TestTaskCount:
    """Test task counting."""

    def test_total_count(self, initialized_registry):
        assert initialized_registry.get_task_count() >= 190

    def test_per_category_count(self, initialized_registry):
        count = initialized_registry.get_task_count("lvm")
        assert count >= 5  # lvm has 9 tasks

    def test_unknown_category_count_zero(self, initialized_registry):
        assert initialized_registry.get_task_count("nonexistent") == 0


class TestGetRandomTask:
    """Test random task generation."""

    def test_returns_instance_not_class(self, initialized_registry):
        task = initialized_registry.get_random_task()
        assert task is not None
        assert hasattr(task, "id")
        assert hasattr(task, "description")
        assert hasattr(task, "category")

    def test_with_category_filter(self, initialized_registry):
        task = initialized_registry.get_random_task(category="lvm")
        assert task is not None
        assert task.category == "lvm"

    def test_with_difficulty_filter(self, initialized_registry):
        task = initialized_registry.get_random_task(difficulty="exam")
        if task:
            assert task.difficulty == "exam"

    def test_unknown_category_returns_none(self, initialized_registry):
        task = initialized_registry.get_random_task(category="nonexistent")
        assert task is None


class TestGenerateExam:
    """Test balanced exam generation."""

    def test_generate_exam_returns_correct_count(self, initialized_registry):
        tasks = initialized_registry.generate_exam(12)
        assert len(tasks) == 12

    def test_generate_exam_tasks_have_exam_domain(self, initialized_registry):
        tasks = initialized_registry.generate_exam(12)
        for task in tasks:
            assert hasattr(task, "exam_domain")

    def test_generate_exam_covers_multiple_domains(self, initialized_registry):
        tasks = initialized_registry.generate_exam(12)
        domains = set(task.exam_domain for task in tasks)
        assert len(domains) >= 3

    def test_generate_exam_tasks_are_instances(self, initialized_registry):
        tasks = initialized_registry.generate_exam(6)
        for task in tasks:
            assert hasattr(task, "id")
            assert hasattr(task, "validate")


class TestGetByDomain:
    """Test domain-based queries."""

    def test_get_tasks_by_domain(self, initialized_registry):
        tasks = initialized_registry.get_tasks_by_domain(4)  # Storage
        assert len(tasks) > 0

    def test_get_practice_tasks(self, initialized_registry):
        tasks = initialized_registry.get_practice_tasks("lvm", "exam", 3)
        assert len(tasks) <= 3
        for task in tasks:
            assert task.category == "lvm"
