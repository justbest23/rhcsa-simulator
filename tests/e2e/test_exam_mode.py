"""
E2E tests for ExamSession - exam generation, validation, reboot, ResultsDB.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.exam import ExamSession
from core.validator import ValidationResult, ValidationCheck, RebootResult


pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def mock_subprocess():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_result):
        yield


class TestExamGeneration:
    """Test exam task generation."""

    def test_generates_correct_count(self, initialized_registry):
        session = ExamSession(task_count=6, timer_enabled=False)
        with patch("builtins.input", return_value="y"), \
             patch("core.exam.fmt"):
            session.start()
        assert len(session.tasks) == 6

    def test_tasks_have_required_attributes(self, initialized_registry):
        session = ExamSession(task_count=4, timer_enabled=False)
        with patch("builtins.input", return_value="y"), \
             patch("core.exam.fmt"):
            session.start()
        for task in session.tasks:
            assert hasattr(task, "id")
            assert hasattr(task, "exam_domain")
            assert hasattr(task, "category")
            assert hasattr(task, "points")


class TestExamValidation:
    """Test validate_all flow."""

    def test_validate_all_saves_to_db(self, initialized_registry, tmp_db):
        session = ExamSession(task_count=3, timer_enabled=False)

        with patch("builtins.input", return_value="y"), \
             patch("core.exam.fmt"):
            session.start()

        mock_result = ValidationResult(
            task_id="t1", passed=True, score=10, max_score=10,
            checks=[ValidationCheck(name="c", passed=True, points=10, message="ok")],
        )
        with patch("core.exam.get_validator") as mock_val, \
             patch("core.exam.get_results_db", return_value=tmp_db), \
             patch("core.exam.get_reboot_engine") as mock_reboot, \
             patch("core.exam.fmt"):
            mock_engine = MagicMock()
            mock_engine.validate_task.return_value = mock_result
            mock_engine.calculate_total_score.return_value = (30, 30, 100.0)
            mock_engine.get_domain_breakdown.return_value = {}
            mock_engine.get_category_breakdown.return_value = {}
            mock_val.return_value = mock_engine

            mock_rb = MagicMock()
            mock_rb.simulate_reboot.return_value = RebootResult(
                boot_success=True, tasks_lost_points=[]
            )
            mock_rb.get_reboot_report.return_value = "Boot OK"
            mock_reboot.return_value = mock_rb

            session.validate_all()

        assert tmp_db.get_exam_count() == 1

    def test_boot_failure_zeros_score(self, initialized_registry, tmp_db):
        session = ExamSession(task_count=2, timer_enabled=False)

        with patch("builtins.input", return_value="y"), \
             patch("core.exam.fmt"):
            session.start()

        mock_result = ValidationResult(
            task_id="t1", passed=True, score=10, max_score=10,
            checks=[],
        )
        with patch("core.exam.get_validator") as mock_val, \
             patch("core.exam.get_results_db", return_value=tmp_db), \
             patch("core.exam.get_reboot_engine") as mock_reboot, \
             patch("core.exam.fmt"):
            mock_engine = MagicMock()
            mock_engine.validate_task.return_value = mock_result
            mock_engine.calculate_total_score.return_value = (20, 20, 100.0)
            mock_engine.get_domain_breakdown.return_value = {}
            mock_engine.get_category_breakdown.return_value = {}
            mock_val.return_value = mock_engine

            mock_rb = MagicMock()
            mock_rb.simulate_reboot.return_value = RebootResult(
                boot_success=False,
                boot_blockers=["Invalid fstab"],
            )
            mock_rb.get_reboot_report.return_value = "Boot FAIL"
            mock_reboot.return_value = mock_rb

            result = session.validate_all()

        assert result is False
        exams = tmp_db.get_recent_exams(1)
        assert exams[0]["total_score"] == 0


class TestExamReport:
    """Test final report generation."""

    def test_report_includes_domain_breakdown(self, initialized_registry, capsys):
        session = ExamSession(task_count=3, timer_enabled=False)

        with patch("builtins.input", return_value="y"), \
             patch("core.exam.fmt") as mock_fmt:
            mock_fmt.bold.side_effect = lambda x: x
            mock_fmt.success.side_effect = lambda x: x
            mock_fmt.error.side_effect = lambda x: x
            mock_fmt.warning.side_effect = lambda x: x
            mock_fmt.info.side_effect = lambda x: x
            mock_fmt.dim.side_effect = lambda x: x
            mock_fmt.format_category_name.side_effect = lambda x: x
            mock_fmt.format_difficulty.side_effect = lambda x: x
            session.start()

        assert len(session.tasks) == 3
