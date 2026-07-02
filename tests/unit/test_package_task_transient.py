"""
Transient-failure hardening across the package validators (follow-up to #44).

execute_safe returns success=False on a 5s timeout, not just on a clean
"absent". Every package validator that keyed a verdict off that must now treat
a failed/timed-out query as inconclusive — never a pass, never a definitive
fail. The nastiest case was RemovePackageTask, where a timeout used to award
full points ("removed") for work not done.
"""

import pytest
from unittest.mock import patch

from validators.safe_executor import ExecutionResult
from tasks.packages import (
    InstallPackageTask,
    RemovePackageTask,
    InstallPackageGroupTask,
    VerifyPackageIntegrityTask,
    _group_installed,
)


pytestmark = pytest.mark.unit


def _res(returncode, stdout="", stderr=""):
    return ExecutionResult(returncode=returncode, stdout=stdout, stderr=stderr,
                           success=(returncode == 0))


def _rpm(res):
    def side_effect(cmd, *a, **k):
        return res if cmd[0] == "rpm" else _res(0)
    return side_effect


TIMEOUT = _res(-1, stderr="Command timed out after 5 seconds")


class TestInstall:
    def test_timeout_is_inconclusive_not_absent(self):
        task = InstallPackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(TIMEOUT)):
            r = task.validate()
        assert r.score == 0 and r.passed is False
        assert "not installed" not in r.checks[0].message.lower()
        assert "grade again" in r.checks[0].message.lower()

    def test_installed_passes(self):
        task = InstallPackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(_res(0, "tree-2.1.1-1.el10.x86_64"))):
            r = task.validate()
        assert r.passed is True and r.score == 6

    def test_absent_fails_cleanly(self):
        task = InstallPackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(_res(1, "package tree is not installed"))):
            r = task.validate()
        assert r.passed is False and r.score == 0
        assert "not installed" in r.checks[0].message.lower()


class TestRemove:
    def test_timeout_does_not_award_removed(self):
        # The regression: a timeout used to score 6/6 "removed" for free.
        task = RemovePackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(TIMEOUT)):
            r = task.validate()
        assert r.passed is False and r.score == 0
        assert r.checks[0].passed is False

    def test_absent_is_removed(self):
        task = RemovePackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(_res(1, "package tree is not installed"))):
            r = task.validate()
        assert r.passed is True and r.score == 6

    def test_still_installed_fails(self):
        task = RemovePackageTask().generate(package="tree")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(_res(0, "tree-2.1.1-1.el10.x86_64"))):
            r = task.validate()
        assert r.passed is False and r.score == 0
        assert "still installed" in r.checks[0].message.lower()


class TestGroup:
    def test_timeout_is_inconclusive(self):
        task = InstallPackageGroupTask().generate(group=("Development Tools", "development"))
        with patch("tasks.packages.execute_safe", return_value=TIMEOUT):
            r = task.validate()
        assert r.passed is False and r.score == 0
        assert "grade again" in r.checks[0].message.lower()

    def test_group_present_passes(self):
        assert _group_installed("Development Tools", "development") in (True, False, None)
        with patch("tasks.packages.execute_safe",
                   return_value=_res(0, "Installed Groups:\n   Development Tools\n")):
            assert _group_installed("Development Tools", "development") is True
        with patch("tasks.packages.execute_safe", return_value=_res(0, "Installed Groups:\n   System Tools\n")):
            assert _group_installed("Development Tools", "development") is False


class TestVerifyIntegrity:
    def test_rpm_timeout_is_inconclusive(self):
        task = VerifyPackageIntegrityTask().generate(package="bash")
        with patch("tasks.packages.execute_safe", side_effect=_rpm(TIMEOUT)):
            r = task.validate()
        assert r.passed is False and r.score == 0
        assert "grade again" in r.checks[0].message.lower()
