"""
E2E tests for PracticeSession - category selection, validation, SM-2 tracking.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.practice import PracticeSession
from core.validator import ValidationResult, ValidationCheck


pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def mock_subprocess():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_result):
        yield


class TestCategorySelection:
    """Test practice category selection."""

    def test_select_category_menu(self, initialized_registry):
        session = PracticeSession()
        with patch("builtins.input", side_effect=["q"]), \
             patch("core.practice.fmt"):
            session.start()


class TestPracticeTask:
    """Test running practice tasks."""

    def test_passed_task_saves_to_db(self, initialized_registry, tmp_db):
        session = PracticeSession()
        session.task_count = 1

        mock_result = ValidationResult(
            task_id="lvm-test", passed=True, score=10, max_score=10,
            checks=[ValidationCheck(name="c", passed=True, points=10, message="ok")],
        )

        # Mock _select_category and _select_difficulty to skip input
        with patch.object(session, "_select_category", return_value="lvm"), \
             patch.object(session, "_select_difficulty", return_value="exam"), \
             patch("builtins.input", side_effect=["", ""]), \
             patch("core.practice.get_validator") as mock_val, \
             patch("core.practice.get_results_db", return_value=tmp_db), \
             patch("core.practice.confirm_action", side_effect=[False, True]), \
             patch("core.practice.fmt"):
            mock_engine = MagicMock()
            mock_engine.validate_task.return_value = mock_result
            mock_val.return_value = mock_engine
            session.start()

        assert tmp_db.get_practice_count() == 1

    def test_failed_task_offers_retry(self, initialized_registry, tmp_db):
        session = PracticeSession()
        session.task_count = 1

        fail_result = ValidationResult(
            task_id="lvm-test", passed=False, score=0, max_score=10,
            checks=[ValidationCheck(name="c", passed=False, points=0, message="fail", max_points=10)],
        )
        pass_result = ValidationResult(
            task_id="lvm-test", passed=True, score=10, max_score=10,
            checks=[ValidationCheck(name="c", passed=True, points=10, message="ok")],
        )

        # fail -> retry -> pass -> continue
        with patch.object(session, "_select_category", return_value="lvm"), \
             patch.object(session, "_select_difficulty", return_value="exam"), \
             patch("builtins.input", side_effect=["", "r", "", ""]), \
             patch("core.practice.get_validator") as mock_val, \
             patch("core.practice.get_results_db", return_value=tmp_db), \
             patch("core.practice.confirm_action", side_effect=[False, False, True]), \
             patch("core.practice.fmt"):
            mock_engine = MagicMock()
            mock_engine.validate_task.side_effect = [fail_result, pass_result]
            mock_val.return_value = mock_engine
            session.start()

        assert tmp_db.get_practice_count() == 2

    def test_passed_task_shows_exam_tips(self, initialized_registry):
        session = PracticeSession()
        session.task_count = 1

        mock_result = ValidationResult(
            task_id="lvm-test", passed=True, score=10, max_score=10,
            checks=[],
        )

        with patch.object(session, "_select_category", return_value="lvm"), \
             patch.object(session, "_select_difficulty", return_value="exam"), \
             patch("builtins.input", side_effect=["", ""]), \
             patch("core.practice.get_validator") as mock_val, \
             patch("core.practice.get_results_db") as mock_db, \
             patch("core.practice.confirm_action", side_effect=[False, True]), \
             patch("core.practice.fmt") as mock_fmt:
            mock_fmt.bold.side_effect = lambda x: x
            mock_fmt.success.side_effect = lambda x: x
            mock_fmt.format_category_name.side_effect = lambda x: x
            mock_fmt.format_difficulty.side_effect = lambda x: x
            mock_fmt.info.side_effect = lambda x: x

            mock_engine = MagicMock()
            mock_engine.validate_task.return_value = mock_result
            mock_val.return_value = mock_engine
            mock_db.return_value = MagicMock()
            session.start()
