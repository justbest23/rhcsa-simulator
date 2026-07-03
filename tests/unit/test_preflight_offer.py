"""
preflight.offer_task_packages: the ONLY path that may install packages, and it
is strictly consent-gated (Y/n prompt). Declining installs nothing.
"""

import pytest

from core import preflight


pytestmark = pytest.mark.unit


class _T:
    def __init__(self, pkgs):
        self.required_packages = pkgs


@pytest.fixture
def gather(monkeypatch):
    state = {"installed": [], "missing": {"httpd"}, "asked": [], "answer": False}

    monkeypatch.setattr(preflight, "filter_missing",
                        lambda pkgs: sorted(set(pkgs) & state["missing"]))

    def fake_install(pkgs):
        state["installed"].extend(pkgs)
        state["missing"] -= set(pkgs)
        return True, ""
    monkeypatch.setattr(preflight, "install_packages", fake_install)

    from utils import helpers
    def fake_confirm(prompt, default=False):
        state["asked"].append(prompt)
        return state["answer"]
    monkeypatch.setattr(helpers, "confirm_action", fake_confirm)
    return state


def test_no_required_packages_no_prompt(gather):
    still = preflight.offer_task_packages([_T([]), _T([])])
    assert still == []
    assert gather["asked"] == [], "must not prompt when nothing is needed"


def test_all_present_no_prompt(gather):
    gather["missing"] = set()
    still = preflight.offer_task_packages([_T(["httpd"])])
    assert still == []
    assert gather["asked"] == []


def test_decline_installs_nothing(gather):
    gather["answer"] = False
    still = preflight.offer_task_packages([_T(["httpd"])])
    assert gather["asked"], "must ask before installing"
    assert gather["installed"] == [], "declining must install NOTHING"
    assert still == ["httpd"], "caller learns what is still missing"


def test_consent_installs(gather):
    gather["answer"] = True
    still = preflight.offer_task_packages([_T(["httpd"]), _T(["httpd"])])
    assert gather["installed"] == ["httpd"]
    assert still == []
