"""
Tests for the httpd preflight added to the httpd-related troubleshooting fault
tasks (issue #37): on a minimal RHEL/Rocky install httpd isn't present, so
injecting the fault (wrong SELinux context, blocked firewall port, disabled
service, ...) silently did nothing observable — the candidate never saw the
symptom. tasks.troubleshooting._ensure_httpd_installed/_ensure_httpd_running
now install/start httpd on demand before the fault is applied, and
_restore_httpd_setup reverts exactly what was changed.
"""

import subprocess
from types import SimpleNamespace

import pytest

from tasks import troubleshooting as ts

pytestmark = pytest.mark.unit


class FakeSystem:
    """Minimal stand-in for rpm/dnf/systemctl state, driven by subprocess.run."""

    def __init__(self, httpd_installed=False, httpd_active=False,
                 httpd_enabled=False, install_should_fail=False):
        self.httpd_installed = httpd_installed
        self.httpd_active = httpd_active
        self.httpd_enabled = httpd_enabled
        self.install_should_fail = install_should_fail
        self.calls = []

    def run(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        prog = cmd[0]

        if prog == 'rpm' and cmd[1:3] == ['-q', 'httpd']:
            return SimpleNamespace(returncode=0 if self.httpd_installed else 1,
                                    stdout='', stderr='')

        if prog == 'dnf' and 'install' in cmd:
            if self.install_should_fail:
                return SimpleNamespace(returncode=1, stdout='', stderr='no repo access')
            self.httpd_installed = True
            return SimpleNamespace(returncode=0, stdout='', stderr='')

        if prog == 'dnf' and 'remove' in cmd:
            self.httpd_installed = False
            self.httpd_active = False
            self.httpd_enabled = False
            return SimpleNamespace(returncode=0, stdout='', stderr='')

        if prog == 'systemctl':
            sub = cmd[1]
            if sub == 'cat':
                return SimpleNamespace(returncode=0 if self.httpd_installed else 1,
                                        stdout='', stderr='')
            if sub == 'is-active':
                return SimpleNamespace(
                    returncode=0 if self.httpd_active else 3,
                    stdout='active' if self.httpd_active else 'inactive', stderr='')
            if sub == 'is-enabled':
                return SimpleNamespace(
                    returncode=0 if self.httpd_enabled else 1,
                    stdout='enabled' if self.httpd_enabled else 'disabled', stderr='')
            if sub == 'enable':
                self.httpd_enabled = True
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if sub == 'disable':
                self.httpd_enabled = False
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if sub == 'start':
                self.httpd_active = True
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if sub == 'stop':
                self.httpd_active = False
                return SimpleNamespace(returncode=0, stdout='', stderr='')

        return SimpleNamespace(returncode=0, stdout='', stderr='')


@pytest.fixture
def fake_state_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, 'FAULT_STATE_FILE', str(tmp_path / 'active_fault.json'))


@pytest.fixture
def fake_system(monkeypatch, fake_state_file):
    system = FakeSystem()
    monkeypatch.setattr(subprocess, 'run', system.run)
    return system


def dnf_calls(system, verb):
    return [c for c in system.calls if c[:2] == ['dnf', '-y'] and verb in c]


class TestEnsureHttpdInstalled:
    def test_installs_when_missing(self, fake_system):
        fake_system.httpd_installed = False
        assert ts._ensure_httpd_installed('task1') is True
        assert fake_system.httpd_installed is True
        assert dnf_calls(fake_system, 'install')

    def test_records_restore_state_when_installed(self, fake_system):
        ts._ensure_httpd_installed('task1')
        state = ts.load_fault_state(ts._httpd_pkg_key('task1'))
        assert state is not None
        assert state['restore_info']['restore_type'] == 'pkg_remove'
        assert state['restore_info']['pkg'] == 'httpd'

    def test_noop_when_already_installed(self, fake_system):
        fake_system.httpd_installed = True
        assert ts._ensure_httpd_installed('task1') is True
        assert not dnf_calls(fake_system, 'install')
        assert ts.load_fault_state(ts._httpd_pkg_key('task1')) is None

    def test_returns_false_when_install_fails(self, fake_system):
        fake_system.httpd_installed = False
        fake_system.install_should_fail = True
        assert ts._ensure_httpd_installed('task1') is False


class TestEnsureHttpdRunning:
    def test_starts_and_enables_when_stopped(self, fake_system):
        fake_system.httpd_installed = True
        fake_system.httpd_active = False
        fake_system.httpd_enabled = False
        ts._ensure_httpd_running('task1')
        assert fake_system.httpd_active is True
        assert fake_system.httpd_enabled is True

    def test_noop_when_already_running(self, fake_system):
        fake_system.httpd_installed = True
        fake_system.httpd_active = True
        fake_system.httpd_enabled = True
        ts._ensure_httpd_running('task1')
        assert ts.load_fault_state(ts._httpd_svc_key('task1')) is None


class TestRestoreHttpdSetup:
    def test_uninstalls_and_stops_what_it_started(self, fake_system):
        fake_system.httpd_installed = False
        ts._ensure_httpd_installed('task1')
        ts._ensure_httpd_running('task1')
        assert fake_system.httpd_installed is True
        assert fake_system.httpd_active is True

        msgs = []
        ts._restore_httpd_setup('task1', msgs)

        assert fake_system.httpd_installed is False
        assert msgs
        assert ts.load_fault_state(ts._httpd_pkg_key('task1')) is None
        assert ts.load_fault_state(ts._httpd_svc_key('task1')) is None

    def test_noop_when_nothing_was_changed(self, fake_system):
        fake_system.httpd_installed = True
        fake_system.httpd_active = True
        fake_system.httpd_enabled = True
        ts._ensure_httpd_installed('task1')
        ts._ensure_httpd_running('task1')

        msgs = []
        ts._restore_httpd_setup('task1', msgs)
        assert msgs == []
        assert fake_system.httpd_installed is True


class TestHttpdDisabledFaultTaskWithMissingPackage:
    """fault_service_httpd_001 previously assumed httpd was already installed;
    on a minimal install its systemctl stop/disable calls were silent no-ops."""

    def test_inject_installs_httpd_then_disables_it(self, fake_system):
        fake_system.httpd_installed = False
        task = ts.HttpdDisabledFaultTask()

        ok, msg = task.inject_fault()

        assert ok is True
        assert fake_system.httpd_installed is True
        assert fake_system.httpd_active is False
        assert fake_system.httpd_enabled is False

    def test_restore_leaves_host_as_it_found_it(self, fake_system):
        fake_system.httpd_installed = False
        task = ts.HttpdDisabledFaultTask()
        task.inject_fault()

        ok, msg = task.restore_fault()

        assert ok is True
        assert fake_system.httpd_installed is False

    def test_inject_fails_cleanly_when_httpd_cannot_be_installed(self, fake_system):
        fake_system.httpd_installed = False
        fake_system.install_should_fail = True
        task = ts.HttpdDisabledFaultTask()

        ok, msg = task.inject_fault()

        assert ok is False
        assert 'httpd' in msg.lower()
        # No fault state should be recorded for a failed injection.
        assert ts.load_fault_state(task.id) is None

    def test_inject_skips_install_when_httpd_already_present(self, fake_system):
        fake_system.httpd_installed = True
        fake_system.httpd_active = True
        fake_system.httpd_enabled = True
        task = ts.HttpdDisabledFaultTask()

        ok, msg = task.inject_fault()

        assert ok is True
        assert not dnf_calls(fake_system, 'install')
        # Original was active+enabled, so restore should bring it back.
        assert task._was_active is True
        assert task._was_enabled is True
