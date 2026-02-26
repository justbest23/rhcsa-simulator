"""
SQLite backend for RHCSA Simulator v4.0.0
Replaces JSON file storage with structured database.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import settings


logger = logging.getLogger(__name__)


class ResultsDB:
    """SQLite backend for exam results and practice history."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or settings.DB_PATH)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS exam_results (
                    exam_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds INTEGER,
                    total_score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    reboot_passed INTEGER,
                    task_count INTEGER,
                    mode TEXT DEFAULT 'exam',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS task_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    domain INTEGER,
                    description TEXT,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    persistence_passed INTEGER,
                    checks_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (exam_id) REFERENCES exam_results(exam_id)
                );

                CREATE TABLE IF NOT EXISTS practice_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    domain INTEGER,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    persistence_passed INTEGER,
                    mode TEXT DEFAULT 'practice',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS weak_areas (
                    category TEXT PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    passes INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0,
                    total_max_score INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    last_attempt TEXT,
                    spaced_repetition_due TEXT,
                    easiness_factor REAL DEFAULT 2.5,
                    interval_days INTEGER DEFAULT 1,
                    repetitions INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_task_results_exam
                    ON task_results(exam_id);
                CREATE INDEX IF NOT EXISTS idx_task_results_category
                    ON task_results(category);
                CREATE INDEX IF NOT EXISTS idx_practice_category
                    ON practice_history(category);
                CREATE INDEX IF NOT EXISTS idx_practice_created
                    ON practice_history(created_at);
            """)
            conn.commit()
        finally:
            conn.close()

    def save_exam_result(self, exam_id, start_time, end_time, duration_seconds,
                         total_score, max_score, passed, reboot_passed=None,
                         task_count=None, mode='exam'):
        """Save an exam result."""
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO exam_results
                (exam_id, start_time, end_time, duration_seconds, total_score,
                 max_score, percentage, passed, reboot_passed, task_count, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (exam_id, start_time, end_time, duration_seconds,
                  total_score, max_score, percentage,
                  1 if passed else 0,
                  1 if reboot_passed else (0 if reboot_passed is not None else None),
                  task_count, mode))
            conn.commit()
        finally:
            conn.close()

    def save_task_result(self, exam_id, task_id, category, difficulty, domain,
                         description, score, max_score, passed,
                         persistence_passed=None, checks=None):
        """Save a per-task result."""
        checks_json = json.dumps(checks) if checks else None
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO task_results
                (exam_id, task_id, category, difficulty, domain, description,
                 score, max_score, passed, persistence_passed, checks_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (exam_id, task_id, category, difficulty, domain, description,
                  score, max_score, 1 if passed else 0,
                  1 if persistence_passed else (0 if persistence_passed is not None else None),
                  checks_json))
            conn.commit()
        finally:
            conn.close()

    def save_practice_attempt(self, task_id, category, difficulty, domain,
                               score, max_score, passed,
                               persistence_passed=None, mode='practice'):
        """Save a practice attempt."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO practice_history
                (task_id, category, difficulty, domain, score, max_score,
                 passed, persistence_passed, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, category, difficulty, domain, score, max_score,
                  1 if passed else 0,
                  1 if persistence_passed else (0 if persistence_passed is not None else None),
                  mode))
            conn.commit()
            self._update_weak_area(category, score, max_score, passed)
        finally:
            conn.close()

    def _update_weak_area(self, category, score, max_score, passed):
        """Update weak area stats using SM-2 algorithm."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM weak_areas WHERE category = ?", (category,)
            ).fetchone()

            now = datetime.now().isoformat()

            if row is None:
                ef = 2.5
                interval = 1
                reps = 0
            else:
                ef = row['easiness_factor']
                interval = row['interval_days']
                reps = row['repetitions']

            # SM-2 algorithm
            if passed:
                quality = 4 if score >= max_score * 0.9 else 3
                reps += 1
                if reps == 1:
                    interval = 1
                elif reps == 2:
                    interval = 6
                else:
                    interval = int(interval * ef)
            else:
                quality = 1
                reps = 0
                interval = 1

            ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            due = (datetime.now() + timedelta(days=interval)).isoformat()

            attempts = (row['attempts'] + 1) if row else 1
            passes = (row['passes'] + (1 if passed else 0)) if row else (1 if passed else 0)
            total_score_acc = (row['total_score'] + score) if row else score
            total_max_acc = (row['total_max_score'] + max_score) if row else max_score
            success_rate = passes / attempts if attempts > 0 else 0

            conn.execute("""
                INSERT OR REPLACE INTO weak_areas
                (category, attempts, passes, total_score, total_max_score,
                 success_rate, last_attempt, spaced_repetition_due,
                 easiness_factor, interval_days, repetitions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (category, attempts, passes, total_score_acc, total_max_acc,
                  success_rate, now, due, ef, interval, reps))
            conn.commit()
        finally:
            conn.close()

    def get_recent_exams(self, limit=10):
        """Get recent exam results."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM exam_results
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_weak_categories(self, threshold=0.7, limit=5):
        """Get categories with success rate below threshold."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM weak_areas
                WHERE success_rate < ? AND attempts >= 3
                ORDER BY success_rate ASC LIMIT ?
            """, (threshold, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_due_categories(self):
        """Get categories due for spaced repetition practice."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM weak_areas
                WHERE spaced_repetition_due <= ?
                ORDER BY success_rate ASC
            """, (now,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_category_stats(self, category):
        """Get stats for a specific category."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM weak_areas WHERE category = ?", (category,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_category_stats(self):
        """Get stats for all categories."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM weak_areas ORDER BY success_rate ASC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_persistence_failure_tasks(self):
        """Get task IDs that frequently fail persistence checks."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT task_id, category, COUNT(*) as failures
                FROM task_results
                WHERE persistence_passed = 0
                GROUP BY task_id
                ORDER BY failures DESC
                LIMIT 10
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_exam_count(self):
        """Get total number of exams taken."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM exam_results").fetchone()
            return row['cnt']
        finally:
            conn.close()

    def get_practice_count(self):
        """Get total number of practice attempts."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM practice_history").fetchone()
            return row['cnt']
        finally:
            conn.close()


_results_db = None


def get_results_db():
    global _results_db
    if _results_db is None:
        _results_db = ResultsDB()
    return _results_db
