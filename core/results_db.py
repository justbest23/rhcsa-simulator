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

            # Migration: add hints/exam_tips columns if not present
            for col in ('hints_json', 'exam_tips_json'):
                try:
                    conn.execute(f"ALTER TABLE task_results ADD COLUMN {col} TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # column already exists
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
        self._autosave()

    def save_task_result(self, exam_id, task_id, category, difficulty, domain,
                         description, score, max_score, passed,
                         persistence_passed=None, checks=None,
                         hints=None, exam_tips=None):
        """Save a per-task result."""
        checks_json = json.dumps(checks) if checks else None
        hints_json = json.dumps(hints) if hints else None
        exam_tips_json = json.dumps(exam_tips) if exam_tips else None
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO task_results
                (exam_id, task_id, category, difficulty, domain, description,
                 score, max_score, passed, persistence_passed, checks_json,
                 hints_json, exam_tips_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (exam_id, task_id, category, difficulty, domain, description,
                  score, max_score, 1 if passed else 0,
                  1 if persistence_passed else (0 if persistence_passed is not None else None),
                  checks_json, hints_json, exam_tips_json))
            conn.commit()
        finally:
            conn.close()
        self._autosave()

    def get_exam_task_results(self, exam_id):
        """Get all per-task results for a specific exam, in order."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM task_results WHERE exam_id = ? ORDER BY id ASC
            """, (exam_id,)).fetchall()
            return [dict(r) for r in rows]
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
        self._autosave()

    def _autosave(self):
        """Mirror the DB to the on-disk autosave code (progress_code.autosave)
        after each recorded result, so history survives a reinstall — the DB
        itself lives inside INSTALL_DIR, which install.sh wipes. Best-effort:
        recording a result must never fail because the autosave couldn't be
        written."""
        try:
            from core import progress_code
            progress_code.autosave(self)
        except Exception:
            pass

    def _update_weak_area(self, category, score, max_score, passed, when=None):
        """Update weak area stats using SM-2 algorithm.

        `when` (ISO string) backdates the attempt — used when replaying
        history in rebuild_weak_areas(); defaults to now for live updates."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM weak_areas WHERE category = ?", (category,)
            ).fetchone()

            now = when or datetime.now().isoformat()

            if row is None:
                ef = 2.5
                interval = 1
                reps = 0
            else:
                ef = row['easiness_factor']
                interval = row['interval_days']
                reps = row['repetitions']

            # SM-2 algorithm.
            # Map the pass/fail + score onto SM-2's 0-5 quality grade. A perfect
            # score must reach 5 — at q=4 the EF delta is exactly 0, so without a
            # 5 the easiness factor could only ever stay flat or shrink toward the
            # 1.3 floor (intervals would never grow).
            if passed:
                if score >= max_score:
                    quality = 5
                elif score >= max_score * 0.9:
                    quality = 4
                else:
                    quality = 3
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
            base = datetime.fromisoformat(now) if when else datetime.now()
            due = (base + timedelta(days=interval)).isoformat()

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

    def list_recent_practice(self, limit=30):
        """Most recent practice/adaptive attempts, newest first (for pruning)."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT id, task_id, category, score, max_score, passed, mode,
                       created_at
                FROM practice_history ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_practice_attempts(self, ids):
        """Delete specific practice attempts by row id. Returns rows deleted.
        Callers should rebuild_weak_areas() afterwards."""
        if not ids:
            return 0
        conn = self._get_conn()
        try:
            marks = ','.join('?' for _ in ids)
            cur = conn.execute(
                f"DELETE FROM practice_history WHERE id IN ({marks})",
                list(ids))
            conn.commit()
        finally:
            conn.close()
        self._autosave()
        return cur.rowcount

    def rebuild_weak_areas(self):
        """Recompute ALL weak-area/SM-2 state from the surviving practice
        history. Without this, pruned attempts kept polluting the adaptive
        stats: deleting rows never touched weak_areas. Replays every attempt
        in order, backdated to its original timestamp."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM weak_areas")
            conn.commit()
            rows = conn.execute(
                "SELECT category, score, max_score, passed, created_at "
                "FROM practice_history ORDER BY created_at ASC, id ASC"
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            when = None
            try:
                # SQLite CURRENT_TIMESTAMP is 'YYYY-MM-DD HH:MM:SS'
                when = datetime.strptime(
                    r['created_at'], '%Y-%m-%d %H:%M:%S').isoformat()
            except (TypeError, ValueError):
                pass
            self._update_weak_area(r['category'], r['score'],
                                   r['max_score'], bool(r['passed']),
                                   when=when)
        self._autosave()
        return len(rows)

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

    # ── Portable progress (snapshot code) ────────────────────────────────────

    def dump_progress(self):
        """Return all progress needed to reconstruct history + SM-2 state as a
        plain dict. Large regenerable text (descriptions, checks, hints) is
        omitted to keep the exported code small."""
        conn = self._get_conn()
        try:
            exams = [dict(r) for r in conn.execute(
                "SELECT exam_id, start_time, end_time, duration_seconds, "
                "total_score, max_score, percentage, passed, reboot_passed, "
                "task_count, mode FROM exam_results").fetchall()]
            tasks = [dict(r) for r in conn.execute(
                "SELECT exam_id, task_id, category, difficulty, domain, score, "
                "max_score, passed, persistence_passed, created_at "
                "FROM task_results").fetchall()]
            practice = [dict(r) for r in conn.execute(
                "SELECT task_id, category, difficulty, domain, score, max_score, "
                "passed, persistence_passed, mode, created_at "
                "FROM practice_history").fetchall()]
            weak = [dict(r) for r in conn.execute(
                "SELECT category, attempts, passes, total_score, total_max_score, "
                "success_rate, last_attempt, spaced_repetition_due, "
                "easiness_factor, interval_days, repetitions "
                "FROM weak_areas").fetchall()]
            return {'exams': exams, 'tasks': tasks,
                    'practice': practice, 'weak': weak}
        finally:
            conn.close()

    def load_progress(self, data, mode='replace'):
        """Insert progress from a dump_progress() dict. mode='replace' wipes
        existing history first; mode='merge' keeps it and skips duplicates.
        Returns a dict of how many rows were added per table."""
        counts = {'exams': 0, 'tasks': 0, 'practice': 0, 'weak': 0}
        conn = self._get_conn()
        try:
            if mode == 'replace':
                for t in ('task_results', 'exam_results',
                          'practice_history', 'weak_areas'):
                    conn.execute(f"DELETE FROM {t}")

            for e in data.get('exams', []):
                conn.execute("""
                    INSERT OR REPLACE INTO exam_results
                    (exam_id, start_time, end_time, duration_seconds, total_score,
                     max_score, percentage, passed, reboot_passed, task_count, mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (e.get('exam_id'), e.get('start_time'), e.get('end_time'),
                      e.get('duration_seconds'), e.get('total_score'),
                      e.get('max_score'), e.get('percentage'), e.get('passed'),
                      e.get('reboot_passed'), e.get('task_count'),
                      e.get('mode', 'exam')))
                counts['exams'] += 1

            for t in data.get('tasks', []):
                if mode == 'merge' and conn.execute(
                        "SELECT 1 FROM task_results WHERE exam_id=? AND task_id=? "
                        "LIMIT 1", (t.get('exam_id'), t.get('task_id'))).fetchone():
                    continue
                conn.execute("""
                    INSERT INTO task_results
                    (exam_id, task_id, category, difficulty, domain, score,
                     max_score, passed, persistence_passed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (t.get('exam_id'), t.get('task_id'), t.get('category'),
                      t.get('difficulty'), t.get('domain'), t.get('score'),
                      t.get('max_score'), t.get('passed'),
                      t.get('persistence_passed'), t.get('created_at')))
                counts['tasks'] += 1

            for p in data.get('practice', []):
                if mode == 'merge' and conn.execute(
                        "SELECT 1 FROM practice_history WHERE task_id=? AND "
                        "created_at=? AND score=? LIMIT 1",
                        (p.get('task_id'), p.get('created_at'),
                         p.get('score'))).fetchone():
                    continue
                conn.execute("""
                    INSERT INTO practice_history
                    (task_id, category, difficulty, domain, score, max_score,
                     passed, persistence_passed, mode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (p.get('task_id'), p.get('category'), p.get('difficulty'),
                      p.get('domain'), p.get('score'), p.get('max_score'),
                      p.get('passed'), p.get('persistence_passed'),
                      p.get('mode', 'practice'), p.get('created_at')))
                counts['practice'] += 1

            # SM-2 state is authoritative in the snapshot — take the imported row.
            for w in data.get('weak', []):
                conn.execute("""
                    INSERT OR REPLACE INTO weak_areas
                    (category, attempts, passes, total_score, total_max_score,
                     success_rate, last_attempt, spaced_repetition_due,
                     easiness_factor, interval_days, repetitions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (w.get('category'), w.get('attempts'), w.get('passes'),
                      w.get('total_score'), w.get('total_max_score'),
                      w.get('success_rate'), w.get('last_attempt'),
                      w.get('spaced_repetition_due'), w.get('easiness_factor'),
                      w.get('interval_days'), w.get('repetitions')))
                counts['weak'] += 1

            conn.commit()
        finally:
            conn.close()
        self._autosave()
        return counts

    def list_exams(self):
        """All exams (id, date, score) for a prune/selection UI."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT exam_id, start_time, percentage, passed, mode "
                "FROM exam_results ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_exam(self, exam_id):
        """Remove one exam and its per-task rows. Returns rows deleted."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM task_results WHERE exam_id=?", (exam_id,))
            cur = conn.execute("DELETE FROM exam_results WHERE exam_id=?", (exam_id,))
            conn.commit()
        finally:
            conn.close()
        self._autosave()
        return cur.rowcount

    def clear_practice_history(self):
        """Delete all practice/adaptive attempts. Returns rows deleted."""
        conn = self._get_conn()
        try:
            cur = conn.execute("DELETE FROM practice_history")
            conn.commit()
        finally:
            conn.close()
        self._autosave()
        return cur.rowcount

    def reset_category(self, category):
        """Clear the SM-2 / weak-area state for one category."""
        conn = self._get_conn()
        try:
            cur = conn.execute("DELETE FROM weak_areas WHERE category=?", (category,))
            conn.commit()
        finally:
            conn.close()
        self._autosave()
        return cur.rowcount

    def clear_all_progress(self):
        """Wipe every progress table (used before a full restore)."""
        conn = self._get_conn()
        try:
            for t in ('task_results', 'exam_results',
                      'practice_history', 'weak_areas'):
                conn.execute(f"DELETE FROM {t}")
            conn.commit()
        finally:
            conn.close()
        self._autosave()


_results_db = None


def get_results_db():
    global _results_db
    if _results_db is None:
        _results_db = ResultsDB()
    return _results_db
