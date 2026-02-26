"""
E2E tests for AdaptiveMode - SM-2 category selection, difficulty adaptation.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.adaptive import AdaptiveMode
from core.validator import ValidationResult, ValidationCheck


pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def mock_subprocess():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_result):
        yield


class TestCategorySelection:
    """Test adaptive category selection logic."""

    def test_no_history_selects_random(self, initialized_registry, tmp_db):
        mode = AdaptiveMode()
        mode.db = tmp_db
        cats, source = mode._select_categories()
        assert len(cats) > 0
        assert "random" in source.lower()

    def test_weak_categories_selected(self, initialized_registry, tmp_db):
        from datetime import datetime, timedelta
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        future = (datetime.now() + timedelta(days=30)).isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("lvm", 5, 1, 10, 50, 0.2, now, future, 1.5, 1, 0))
        conn.commit()
        conn.close()

        mode = AdaptiveMode()
        mode.db = tmp_db
        cats, source = mode._select_categories()
        assert "lvm" in cats
        assert "weak" in source.lower()

    def test_due_categories_take_priority(self, initialized_registry, tmp_db):
        from datetime import datetime, timedelta
        conn = tmp_db._get_conn()
        past = (datetime.now() - timedelta(days=2)).isoformat()
        future = (datetime.now() + timedelta(days=30)).isoformat()

        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("selinux", 5, 3, 30, 50, 0.6, past, past, 2.5, 1, 3))

        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("networking", 5, 1, 10, 50, 0.2, past, future, 1.5, 1, 0))
        conn.commit()
        conn.close()

        mode = AdaptiveMode()
        mode.db = tmp_db
        cats, source = mode._select_categories()
        assert "selinux" in cats
        assert "due" in source.lower()


class TestDifficultyAdaptation:
    """Test difficulty selection based on success rate."""

    def test_low_success_rate_gives_easy(self, tmp_db):
        from datetime import datetime
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("lvm", 10, 3, 30, 100, 0.3, now, now, 1.5, 1, 0))
        conn.commit()
        conn.close()

        mode = AdaptiveMode()
        mode.db = tmp_db
        assert mode._get_adaptive_difficulty("lvm") == "easy"

    def test_medium_success_rate_gives_exam(self, tmp_db):
        from datetime import datetime
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("boot", 10, 6, 60, 100, 0.6, now, now, 2.0, 1, 3))
        conn.commit()
        conn.close()

        mode = AdaptiveMode()
        mode.db = tmp_db
        assert mode._get_adaptive_difficulty("boot") == "exam"

    def test_high_success_rate_gives_hard(self, tmp_db):
        from datetime import datetime
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("selinux", 10, 9, 90, 100, 0.9, now, now, 2.8, 6, 5))
        conn.commit()
        conn.close()

        mode = AdaptiveMode()
        mode.db = tmp_db
        assert mode._get_adaptive_difficulty("selinux") == "hard"

    def test_few_attempts_defaults_to_exam(self, tmp_db):
        mode = AdaptiveMode()
        mode.db = tmp_db
        assert mode._get_adaptive_difficulty("containers") == "exam"
