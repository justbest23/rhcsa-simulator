"""
Tests for tasks.processes.FindProcessByUserTask - list/count/kill actions.

Regression coverage for GitHub issue #42: the 'count' (and 'list') actions
used to validate as passed just because the practice user existed, with no
way for the candidate to actually record their answer. They must now save
their result to a file that is checked for correctness.
"""

from unittest.mock import patch

import pytest

from tasks.processes import FindProcessByUserTask
from validators.safe_executor import ExecutionResult


pytestmark = pytest.mark.unit


def _pgrep_result(pids):
    stdout = "\n".join(pids)
    return ExecutionResult(returncode=0, stdout=stdout, stderr="", success=True)


class TestGenerate:
    def test_list_action_requires_output_file(self):
        task = FindProcessByUserTask().generate(username="pracproc", action="list")
        assert task.output_file
        assert task.output_file in task.description

    def test_count_action_requires_output_file(self):
        task = FindProcessByUserTask().generate(username="pracproc", action="count")
        assert task.output_file
        assert task.output_file in task.description

    def test_kill_action_has_no_output_file(self):
        task = FindProcessByUserTask().generate(username="pracproc", action="kill")
        assert task.output_file is None

    def test_output_file_honors_explicit_param(self):
        task = FindProcessByUserTask().generate(
            username="pracproc", action="count", output="/tmp/my-count.txt"
        )
        assert task.output_file == "/tmp/my-count.txt"


class TestValidateList:
    def test_fails_when_output_file_missing(self, tmp_path):
        task = FindProcessByUserTask().generate(
            username="pracproc", action="list", output=str(tmp_path / "missing.txt")
        )
        result = task.validate()
        assert result.passed is False
        assert result.score == 0

    def test_fails_when_output_file_empty(self, tmp_path):
        out = tmp_path / "list.txt"
        out.write_text("")
        task = FindProcessByUserTask().generate(
            username="pracproc", action="list", output=str(out)
        )
        result = task.validate()
        assert result.passed is False

    def test_passes_when_output_file_has_content(self, tmp_path):
        out = tmp_path / "list.txt"
        out.write_text("  PID TTY TIME CMD\n1234 ?  00:00:00 sleep\n")
        task = FindProcessByUserTask().generate(
            username="pracproc", action="list", output=str(out)
        )
        result = task.validate()
        assert result.passed is True
        assert result.score == task.points


class TestValidateCount:
    def test_fails_when_output_file_missing(self, tmp_path):
        task = FindProcessByUserTask().generate(
            username="pracproc", action="count", output=str(tmp_path / "missing.txt")
        )
        with patch("tasks.processes.execute_safe", return_value=_pgrep_result(["1", "2", "3"])):
            result = task.validate()
        assert result.passed is False
        assert result.score == 0

    def test_fails_when_count_is_wrong(self, tmp_path):
        out = tmp_path / "count.txt"
        out.write_text("5\n")
        task = FindProcessByUserTask().generate(
            username="pracproc", action="count", output=str(out)
        )
        with patch("tasks.processes.execute_safe", return_value=_pgrep_result(["1", "2", "3"])):
            result = task.validate()
        assert result.passed is False
        # Output file existing still earns partial credit.
        assert 0 < result.score < task.points

    def test_passes_when_count_matches(self, tmp_path):
        out = tmp_path / "count.txt"
        out.write_text("3\n")
        task = FindProcessByUserTask().generate(
            username="pracproc", action="count", output=str(out)
        )
        with patch("tasks.processes.execute_safe", return_value=_pgrep_result(["1", "2", "3"])):
            result = task.validate()
        assert result.passed is True
        assert result.score == task.points

    def test_passes_when_count_matches_zero(self, tmp_path):
        out = tmp_path / "count.txt"
        out.write_text("0\n")
        task = FindProcessByUserTask().generate(
            username="pracproc", action="count", output=str(out)
        )
        with patch("tasks.processes.execute_safe", return_value=_pgrep_result([])):
            result = task.validate()
        assert result.passed is True
        assert result.score == task.points


class TestValidateKill:
    def test_passes_when_no_processes_remain(self):
        task = FindProcessByUserTask().generate(username="pracproc", action="kill")
        empty = ExecutionResult(returncode=1, stdout="", stderr="", success=False)
        with patch("tasks.processes.execute_safe", return_value=empty):
            result = task.validate()
        assert result.passed is True
        assert result.score == task.points

    def test_fails_when_processes_remain(self):
        task = FindProcessByUserTask().generate(username="pracproc", action="kill")
        with patch("tasks.processes.execute_safe", return_value=_pgrep_result(["1", "2"])):
            result = task.validate()
        assert result.passed is False
        assert result.score == 0
