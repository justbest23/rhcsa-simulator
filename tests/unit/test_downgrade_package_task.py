"""
Tests for DowngradePackageTask.validate() — the checker behind pkg_downgrade_001.

Regression coverage for issue #44: a candidate who genuinely downgraded
vim-enhanced scored 0/12 with "vim-enhanced not installed" because the checker
treated ANY execute_safe failure (a 5s timeout on a busy rpmdb lock) as
"package absent", and the downgrade check substring-grepped ALL of dnf history
(false-passing on unrelated downgrades). Both are now transient-failure aware
and scoped to the task's package.
"""

import pytest
from unittest.mock import patch

from validators.safe_executor import ExecutionResult
from tasks.packages import (
    DowngradePackageTask,
    _package_installed,
    _downgrade_recorded,
)


pytestmark = pytest.mark.unit


def _res(returncode, stdout="", stderr=""):
    return ExecutionResult(
        returncode=returncode, stdout=stdout, stderr=stderr,
        success=(returncode == 0),
    )


@pytest.fixture
def task():
    return DowngradePackageTask().generate(package="vim-enhanced")


def _dispatch(rpm_res, history_res, showdup_res=None):
    """Return an execute_safe side effect keyed on the command."""
    def side_effect(cmd, *args, **kwargs):
        if cmd[0] == "rpm":
            return rpm_res
        if cmd[0] == "dnf" and "history" in cmd:
            return history_res
        if cmd[0] == "dnf" and "--showduplicates" in cmd:
            return showdup_res if showdup_res is not None else _res(0)
        return _res(0)
    return side_effect


class TestHappyPath:
    def test_installed_and_downgraded_scores_full(self, task):
        # rpm -q succeeds; dnf history list <pkg> shows a Downgrade row.
        history = "ID | Command line | Action(s)\n229 | dg vim-enhanced | Downgrade | 4 <"
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(0, "vim-enhanced-9.1.083-9.el10_2.3.x86_64"),
                                         _res(0, history))):
            result = task.validate()
        assert result.passed is True
        assert result.score == 12


class TestTransientFailureNotMisreported:
    def test_rpm_timeout_is_not_reported_as_not_installed(self, task):
        # execute_safe timeout => returncode -1, success False. Must NOT claim
        # "not installed"; must be an inconclusive "grade again" message.
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(-1, stderr="Command timed out"),
                                         _res(0, "Downgrade"))):
            result = task.validate()
        assert result.score == 0
        msg = result.checks[0].message.lower()
        assert "not installed" not in msg
        assert "grade again" in msg or "could not verify" in msg

    def test_history_timeout_does_not_null_the_downgrade_points(self, task):
        # Package present, but dnf history query fails transiently. The downgrade
        # check should say "could not read", not a definitive "no downgrade".
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(0, "vim-enhanced-9.1.083-9.el10_2.3.x86_64"),
                                         _res(-1, stderr="Command timed out"))):
            result = task.validate()
        assert result.score == 4  # pkg_installed only
        dg = [c for c in result.checks if c.name == "downgrade_done"][0]
        assert "could not read" in dg.message.lower()


class TestGenuineFailures:
    def test_genuinely_absent_package_says_not_installed(self, task):
        # rpm exits 1 with "is not installed" — the real absent case.
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(1, "package vim-enhanced is not installed"),
                                         _res(0, ""))):
            result = task.validate()
        assert result.score == 0
        assert "not installed" in result.checks[0].message.lower()

    def test_no_downgrade_in_scoped_history_fails_that_check(self, task):
        # Installed, but history for THIS package shows no downgrade.
        history = "No transaction which manipulates package 'vim-enhanced' was found."
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(0, "vim-enhanced-9.1.083-9.el10_2.3.x86_64"),
                                         _res(0, history))):
            result = task.validate()
        assert result.score == 4
        dg = [c for c in result.checks if c.name == "downgrade_done"][0]
        assert dg.passed is False


class TestNoOlderBuildAvailable:
    """Regression coverage for issue #68: a candidate scored 0/12 on
    pkg_downgrade_001 for wget even though the enabled repos genuinely carry
    only the currently-installed build (confirmed via `dnf --showduplicates
    list wget` showing one NEVRA under both Installed and Available). The
    checker must waive the downgrade step when this is the case, rather than
    failing a candidate for an objective the environment makes impossible.
    """

    def test_single_available_build_waives_the_check(self, task):
        history = "No transaction which manipulates package 'vim-enhanced' was found."
        showdup = (
            "Installed Packages\n"
            "vim-enhanced.x86_64    9.1.083-9.el10_2.3    @rhel-10-for-x86_64-appstream-rpms\n"
            "Available Packages\n"
            "vim-enhanced.x86_64    9.1.083-9.el10_2.3    rhel-10-for-x86_64-appstream-rpms\n"
        )
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(0, "vim-enhanced-9.1.083-9.el10_2.3.x86_64"),
                                         _res(0, history),
                                         _res(0, showdup))):
            result = task.validate()
        assert result.passed is True
        assert result.score == 12
        dg = [c for c in result.checks if c.name == "downgrade_done"][0]
        assert dg.passed is True
        assert "waived" in dg.message.lower()

    def test_multiple_available_builds_does_not_waive(self, task):
        history = "No transaction which manipulates package 'vim-enhanced' was found."
        showdup = (
            "Installed Packages\n"
            "vim-enhanced.x86_64    9.1.083-9.el10_2.3    @rhel-10-for-x86_64-appstream-rpms\n"
            "Available Packages\n"
            "vim-enhanced.x86_64    9.1.083-9.el10_2.3    rhel-10-for-x86_64-appstream-rpms\n"
            "vim-enhanced.x86_64    9.1.083-9.el10_2.2    rhel-10-for-x86_64-appstream-rpms\n"
        )
        with patch("tasks.packages.execute_safe",
                   side_effect=_dispatch(_res(0, "vim-enhanced-9.1.083-9.el10_2.3.x86_64"),
                                         _res(0, history),
                                         _res(0, showdup))):
            result = task.validate()
        assert result.score == 4
        dg = [c for c in result.checks if c.name == "downgrade_done"][0]
        assert dg.passed is False


class TestHelpers:
    def test_package_installed_tristate(self):
        with patch("tasks.packages.execute_safe", return_value=_res(0, "pkg-1.0")):
            assert _package_installed("pkg") is True
        with patch("tasks.packages.execute_safe",
                   return_value=_res(1, "package pkg is not installed")):
            assert _package_installed("pkg") is False
        with patch("tasks.packages.execute_safe", return_value=_res(-1, stderr="timeout")):
            assert _package_installed("pkg") is None

    def test_downgrade_recorded_is_scoped(self):
        # A Downgrade row for the queried package => True.
        with patch("tasks.packages.execute_safe",
                   return_value=_res(0, "229 | dg pkg | Downgrade | 4")):
            assert _downgrade_recorded("pkg") is True
        # dnf history list returns rc=0 with no matches => False, not a false pass.
        with patch("tasks.packages.execute_safe",
                   return_value=_res(0, "No transaction which manipulates package 'pkg' was found.")):
            assert _downgrade_recorded("pkg") is False
        # Query itself failed => inconclusive.
        with patch("tasks.packages.execute_safe", return_value=_res(-1, stderr="timeout")):
            assert _downgrade_recorded("pkg") is None
