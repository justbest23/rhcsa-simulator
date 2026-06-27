"""
Tests for core.results_db - SQLite backend with SM-2 spaced repetition.
"""

import pytest
from datetime import datetime, timedelta


pytestmark = pytest.mark.unit


class TestSaveAndRetrieve:
    """Test basic CRUD operations."""

    def test_save_exam_result(self, tmp_db):
        tmp_db.save_exam_result(
            exam_id="exam-001",
            start_time="2025-01-01T10:00:00",
            end_time="2025-01-01T13:00:00",
            duration_seconds=10800,
            total_score=250,
            max_score=300,
            passed=True,
            reboot_passed=True,
            task_count=12,
        )
        exams = tmp_db.get_recent_exams(5)
        assert len(exams) == 1
        assert exams[0]["exam_id"] == "exam-001"
        assert exams[0]["total_score"] == 250
        assert exams[0]["passed"] == 1

    def test_save_practice_attempt(self, tmp_db):
        tmp_db.save_practice_attempt(
            task_id="task-lvm-001",
            category="lvm",
            difficulty="exam",
            domain=4,
            score=10,
            max_score=10,
            passed=True,
        )
        count = tmp_db.get_practice_count()
        assert count == 1

    def test_save_task_result(self, tmp_db):
        tmp_db.save_exam_result(
            exam_id="exam-002",
            start_time="2025-01-02T10:00:00",
            end_time="2025-01-02T13:00:00",
            duration_seconds=10800,
            total_score=200,
            max_score=300,
            passed=False,
        )
        tmp_db.save_task_result(
            exam_id="exam-002",
            task_id="task-net-001",
            category="networking",
            difficulty="exam",
            domain=5,
            description="Configure static IP",
            score=15,
            max_score=20,
            passed=True,
            persistence_passed=True,
            checks=[{"name": "ip_check", "passed": True}],
        )
        # No assertion error means save succeeded


class TestExamCount:
    """Test exam and practice counting."""

    def test_exam_count_empty(self, tmp_db):
        assert tmp_db.get_exam_count() == 0

    def test_exam_count_after_saves(self, tmp_db):
        for i in range(3):
            tmp_db.save_exam_result(
                exam_id=f"exam-{i:03d}",
                start_time="2025-01-01T10:00:00",
                end_time="2025-01-01T13:00:00",
                duration_seconds=10800,
                total_score=200,
                max_score=300,
                passed=False,
            )
        assert tmp_db.get_exam_count() == 3

    def test_practice_count_empty(self, tmp_db):
        assert tmp_db.get_practice_count() == 0

    def test_practice_count_after_saves(self, tmp_db):
        for i in range(5):
            tmp_db.save_practice_attempt(
                task_id=f"task-{i}",
                category="lvm",
                difficulty="exam",
                domain=4,
                score=10,
                max_score=10,
                passed=True,
            )
        assert tmp_db.get_practice_count() == 5


class TestSM2Algorithm:
    """Test SM-2 spaced repetition via weak_areas table."""

    def test_passing_increases_interval(self, tmp_db):
        # First pass: interval should be 1
        tmp_db.save_practice_attempt(
            task_id="t1", category="lvm", difficulty="exam", domain=4,
            score=10, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("lvm")
        assert stats["interval_days"] == 1
        assert stats["repetitions"] == 1

        # Second pass: interval should be 6
        tmp_db.save_practice_attempt(
            task_id="t2", category="lvm", difficulty="exam", domain=4,
            score=10, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("lvm")
        assert stats["interval_days"] == 6
        assert stats["repetitions"] == 2

    def test_passing_increases_easiness(self, tmp_db):
        tmp_db.save_practice_attempt(
            task_id="t1", category="selinux", difficulty="exam", domain=7,
            score=10, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("selinux")
        # Perfect score -> quality=5: ef = 2.5 + (0.1 - 0*(...)) = 2.6.
        # (A perfect recall must be able to grow EF; q<=4 can only hold/shrink it.)
        assert stats["easiness_factor"] == pytest.approx(2.6, abs=0.01)

    def test_quality_scoring_perfect(self, tmp_db):
        """A perfect score maps to SM-2 quality 5 and grows the easiness factor."""
        for i in range(3):
            tmp_db.save_practice_attempt(
                task_id=f"t{i}", category="repos", difficulty="exam", domain=1,
                score=10, max_score=10, passed=True,
            )
        stats = tmp_db.get_category_stats("repos")
        # Three perfect passes -> EF climbs above the 2.5 starting point.
        assert stats["easiness_factor"] > 2.5

    def test_failing_resets_interval(self, tmp_db):
        # Build up interval
        tmp_db.save_practice_attempt(
            task_id="t1", category="boot", difficulty="exam", domain=2,
            score=10, max_score=10, passed=True,
        )
        tmp_db.save_practice_attempt(
            task_id="t2", category="boot", difficulty="exam", domain=2,
            score=10, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("boot")
        assert stats["interval_days"] == 6

        # Fail: interval should reset to 1, reps to 0
        tmp_db.save_practice_attempt(
            task_id="t3", category="boot", difficulty="exam", domain=2,
            score=2, max_score=10, passed=False,
        )
        stats = tmp_db.get_category_stats("boot")
        assert stats["interval_days"] == 1
        assert stats["repetitions"] == 0

    def test_quality_scoring_high(self, tmp_db):
        """90%+ score gives quality 4."""
        tmp_db.save_practice_attempt(
            task_id="t1", category="swap", difficulty="exam", domain=4,
            score=9, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("swap")
        # quality=4 -> ef = 2.5 + (0.1 - 1*(0.08+1*0.02)) = 2.5 + 0.0 = 2.5
        assert stats["easiness_factor"] == pytest.approx(2.5, abs=0.01)

    def test_quality_scoring_pass_below_90(self, tmp_db):
        """Passed but <90% gives quality 3."""
        tmp_db.save_practice_attempt(
            task_id="t1", category="firewall", difficulty="exam", domain=7,
            score=7, max_score=10, passed=True,
        )
        stats = tmp_db.get_category_stats("firewall")
        # quality=3 -> ef = 2.5 + (0.1 - 2*(0.08+2*0.02)) = 2.5 + 0.1 - 0.24 = 2.36
        assert stats["easiness_factor"] == pytest.approx(2.36, abs=0.01)

    def test_quality_scoring_fail(self, tmp_db):
        """Failed gives quality 1."""
        tmp_db.save_practice_attempt(
            task_id="t1", category="scripting", difficulty="exam", domain=8,
            score=2, max_score=10, passed=False,
        )
        stats = tmp_db.get_category_stats("scripting")
        # quality=1 -> ef = 2.5 + (0.1 - 4*(0.08+4*0.02)) = 2.5 + 0.1 - 0.64 = 1.96
        assert stats["easiness_factor"] == pytest.approx(1.96, abs=0.01)


class TestDueAndWeakCategories:
    """Test due/weak category queries."""

    def test_get_due_categories_returns_past_due(self, tmp_db):
        # Manually insert a past-due entry
        conn = tmp_db._get_conn()
        past = (datetime.now() - timedelta(days=1)).isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("lvm", 5, 3, 50, 80, 0.6, past, past, 2.5, 1, 3))
        conn.commit()
        conn.close()

        due = tmp_db.get_due_categories()
        assert len(due) >= 1
        assert due[0]["category"] == "lvm"

    def test_get_due_categories_excludes_future(self, tmp_db):
        conn = tmp_db._get_conn()
        future = (datetime.now() + timedelta(days=10)).isoformat()
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("selinux", 5, 4, 80, 100, 0.8, future, future, 2.5, 6, 3))
        conn.commit()
        conn.close()

        due = tmp_db.get_due_categories()
        cats = [d["category"] for d in due]
        assert "selinux" not in cats

    def test_get_weak_categories_threshold(self, tmp_db):
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        # Weak: 40% with 5 attempts
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("networking", 5, 2, 30, 50, 0.4, now, now, 2.1, 1, 0))
        conn.commit()
        conn.close()

        weak = tmp_db.get_weak_categories(0.7)
        assert len(weak) >= 1
        assert weak[0]["category"] == "networking"

    def test_get_weak_categories_requires_min_attempts(self, tmp_db):
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        # Only 2 attempts - should NOT appear
        conn.execute("""
            INSERT INTO weak_areas
            (category, attempts, passes, total_score, total_max_score,
             success_rate, last_attempt, spaced_repetition_due,
             easiness_factor, interval_days, repetitions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("containers", 2, 0, 0, 20, 0.0, now, now, 2.5, 1, 0))
        conn.commit()
        conn.close()

        weak = tmp_db.get_weak_categories(0.7)
        cats = [w["category"] for w in weak]
        assert "containers" not in cats


class TestCategoryStats:
    """Test category stats queries."""

    def test_get_all_category_stats_sorted_by_success_rate(self, tmp_db):
        conn = tmp_db._get_conn()
        now = datetime.now().isoformat()
        for cat, rate in [("lvm", 0.3), ("boot", 0.8), ("selinux", 0.5)]:
            conn.execute("""
                INSERT INTO weak_areas
                (category, attempts, passes, total_score, total_max_score,
                 success_rate, last_attempt, spaced_repetition_due,
                 easiness_factor, interval_days, repetitions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat, 5, int(rate * 5), 50, 100, rate, now, now, 2.5, 1, 0))
        conn.commit()
        conn.close()

        stats = tmp_db.get_all_category_stats()
        rates = [s["success_rate"] for s in stats]
        assert rates == sorted(rates)

    def test_multiple_attempts_accumulate(self, tmp_db):
        for i in range(4):
            tmp_db.save_practice_attempt(
                task_id=f"t{i}", category="permissions", difficulty="exam",
                domain=3, score=8, max_score=10, passed=True,
            )
        stats = tmp_db.get_category_stats("permissions")
        assert stats["attempts"] == 4
        assert stats["passes"] == 4
        assert stats["total_score"] == 32
        assert stats["total_max_score"] == 40


class TestPersistenceFailures:
    """Test persistence failure tracking."""

    def test_get_persistence_failure_tasks(self, tmp_db):
        tmp_db.save_exam_result(
            exam_id="exam-pf",
            start_time="2025-01-01T10:00:00",
            end_time="2025-01-01T13:00:00",
            duration_seconds=10800,
            total_score=200,
            max_score=300,
            passed=False,
        )
        # Save 3 failures for same task
        for i in range(3):
            tmp_db.save_task_result(
                exam_id="exam-pf",
                task_id="task-fstab-001",
                category="filesystems",
                difficulty="exam",
                domain=4,
                description="Mount filesystem",
                score=0,
                max_score=15,
                passed=False,
                persistence_passed=False,
            )
        failures = tmp_db.get_persistence_failure_tasks()
        assert len(failures) >= 1
        assert failures[0]["task_id"] == "task-fstab-001"
        assert failures[0]["failures"] == 3
