"""
Tests for portable progress codes: codec round-trip, corruption/typo rejection,
purely-alphanumeric output, and ResultsDB export/import (replace + merge).
"""

import pytest

from core import progress_code as pc
from core.results_db import ResultsDB


class TestCodec:
    def test_round_trip(self):
        payload = {'v': 1, 'weak': [{'category': 'lvm', 'attempts': 3}],
                   'practice': [], 'tasks': [], 'exams': []}
        code = pc.encode(payload)
        assert pc.decode(code) == payload

    def test_output_is_alphanumeric_or_dashes(self):
        code = pc.encode({'v': 1, 'x': list(range(50))})
        assert all(c.isalnum() or c == '-' for c in code)
        # Base32 body is uppercase A-Z/2-7 only.
        assert all(c in pc._ALPHABET for c in code.replace('-', ''))

    def test_dashes_spaces_newlines_are_ignored(self):
        code = pc.encode({'v': 1, 'hello': 'world'})
        messy = f"  {code[:5]}\n{code[5:10]} {code[10:]}  "
        assert pc.decode(messy) == {'v': 1, 'hello': 'world'}

    def test_rejects_foreign_string(self):
        with pytest.raises(pc.ProgressCodeError):
            pc.decode("just some random text")

    def test_rejects_empty(self):
        with pytest.raises(pc.ProgressCodeError):
            pc.decode("----")

    def test_rejects_mistyped_checksum(self):
        code = pc.encode({'v': 1, 'data': 'important'})
        body = code.replace('-', '')
        # Flip one character in the middle to a different valid-alphabet char.
        ch = 'A' if body[len(body) // 2] != 'A' else 'B'
        broken = body[:len(body) // 2] + ch + body[len(body) // 2 + 1:]
        with pytest.raises(pc.ProgressCodeError):
            pc.decode(broken)


@pytest.fixture
def db(tmp_path):
    return ResultsDB(db_path=str(tmp_path / "test.db"))


def _seed(db):
    db.save_exam_result("exam_a", "2026-01-01T10:00", "2026-01-01T11:00",
                        3600, 80, 100, passed=True, task_count=2)
    db.save_task_result("exam_a", "lvm_001", "lvm", "exam", 4, "desc",
                        40, 50, passed=True)
    db.save_practice_attempt("swap_001", "swap", "exam", 4, 10, 12, passed=True)
    db.save_practice_attempt("swap_001", "swap", "exam", 4, 5, 12, passed=False)


class TestDBRoundTrip:
    def test_export_then_import_replace_into_fresh_db(self, tmp_path):
        src = ResultsDB(db_path=str(tmp_path / "src.db"))
        _seed(src)
        code = pc.export_code(src)

        dst = ResultsDB(db_path=str(tmp_path / "dst.db"))
        counts, summary = pc.import_code(code, mode='replace', db=dst)

        assert dst.get_exam_count() == 1
        assert dst.get_practice_count() == 2
        # SM-2 state for 'swap' carried over.
        assert dst.get_category_stats('swap') is not None
        assert counts['exams'] == 1 and counts['practice'] == 2

    def test_replace_wipes_existing(self, tmp_path):
        dst = ResultsDB(db_path=str(tmp_path / "dst.db"))
        _seed(dst)  # local progress that should be wiped
        other = ResultsDB(db_path=str(tmp_path / "other.db"))
        other.save_practice_attempt("selinux_001", "selinux", "exam", 7,
                                    8, 8, passed=True)
        code = pc.export_code(other)

        pc.import_code(code, mode='replace', db=dst)
        assert dst.get_practice_count() == 1  # only the imported one

    def test_merge_keeps_local_and_skips_duplicates(self, tmp_path):
        dst = ResultsDB(db_path=str(tmp_path / "dst.db"))
        _seed(dst)
        code = pc.export_code(dst)  # export == current local state

        before = dst.get_practice_count()
        pc.import_code(code, mode='merge', db=dst)
        # Re-importing our own state must not double the rows.
        assert dst.get_practice_count() == before


class TestPrune:
    def test_delete_exam_removes_tasks(self, db):
        _seed(db)
        assert db.get_exam_count() == 1
        db.delete_exam("exam_a")
        assert db.get_exam_count() == 0
        assert db.get_exam_task_results("exam_a") == []

    def test_clear_practice_and_reset_category(self, db):
        _seed(db)
        assert db.clear_practice_history() == 2
        assert db.get_practice_count() == 0
        assert db.reset_category('swap') == 1
        assert db.get_category_stats('swap') is None
