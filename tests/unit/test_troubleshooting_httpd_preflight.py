"""
httpd-dependent troubleshooting faults must NEVER install packages themselves.

Packages are offered (Y/n) at session prep via preflight.offer_task_packages;
tasks only declare required_packages. When httpd is absent at inject time:

  * SELinux faults still inject (the misconfiguration is real) and plant the
    audit-log evidence a real denial would have produced (_seed_avc_denial),
    so `ausearch -m AVC | audit2why` still leads to the root cause.
  * Service/firewall faults (which need a real httpd to run) skip cleanly.
"""

from types import SimpleNamespace

import pytest

from tasks import troubleshooting as ts

pytestmark = pytest.mark.unit


class FakeSystem:
    """Stand-in for rpm/systemctl/chcon/setsebool state, driven by ts._run."""

    def __init__(self, httpd_installed=False):
        self.httpd_installed = httpd_installed
        self.calls = []

    def run(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        prog = cmd[0]
        if prog == 'rpm' and cmd[1:3] == ['-q', 'httpd']:
            return SimpleNamespace(returncode=0 if self.httpd_installed else 1,
                                   stdout='', stderr='')
        if prog == 'getsebool':
            return SimpleNamespace(returncode=0,
                                   stdout='httpd_can_network_connect --> on',
                                   stderr='')
        # chcon, setsebool, systemctl, curl, logger, firewall-cmd ... succeed
        return SimpleNamespace(returncode=0, stdout='', stderr='')


@pytest.fixture
def no_httpd(monkeypatch, tmp_path):
    fake = FakeSystem(httpd_installed=False)
    monkeypatch.setattr(ts, '_run', lambda cmd, **kw: fake.run(cmd, **kw))
    # State + audit files sandboxed
    monkeypatch.setattr(ts, 'FAULT_STATE_FILE', str(tmp_path / 'fault.json'))
    monkeypatch.setattr(ts, '_AUDIT_LOG', str(tmp_path / 'audit.log'))
    return fake, tmp_path


def _no_dnf(fake):
    return not any(c and c[0] == 'dnf' for c in fake.calls)


class TestNoSilentInstalls:
    def test_httpd_present_is_read_only(self, no_httpd):
        fake, _ = no_httpd
        assert ts._httpd_present() is False
        fake.httpd_installed = True
        assert ts._httpd_present() is True
        assert _no_dnf(fake), "presence check must never run dnf"

    def test_tasks_declare_required_packages(self):
        for cls in (ts.SELinuxHttpdContextFaultTask, ts.SELinuxHttpdBooleanFaultTask,
                    ts.FirewallHttpBlockedFaultTask, ts.HttpdDisabledFaultTask):
            assert 'httpd' in cls.required_packages


class TestSELinuxFaultsWithoutHttpd:
    def test_context_fault_injects_and_seeds_avc(self, no_httpd):
        fake, sandbox = no_httpd
        task = ts.SELinuxHttpdContextFaultTask()
        task.web_root = str(sandbox / 'www')
        ok, msg = task.inject_fault()
        assert ok, msg
        assert _no_dnf(fake), "inject_fault must never dnf install"
        # Synthetic AVC evidence written for the candidate to find
        log = sandbox / 'audit.log'
        assert log.exists()
        content = log.read_text()
        assert 'type=AVC' in content and 'etc_t' in content and 'httpd' in content

    def test_boolean_fault_injects_and_seeds_avc(self, no_httpd):
        fake, sandbox = no_httpd
        task = ts.SELinuxHttpdBooleanFaultTask()
        ok, msg = task.inject_fault()
        assert ok, msg
        assert _no_dnf(fake)
        content = (sandbox / 'audit.log').read_text()
        assert 'name_connect' in content and 'httpd_t' in content

    def test_real_httpd_means_no_synthetic_avc(self, no_httpd):
        fake, sandbox = no_httpd
        fake.httpd_installed = True
        task = ts.SELinuxHttpdContextFaultTask()
        task.web_root = str(sandbox / 'www')
        ok, _ = task.inject_fault()
        assert ok
        # With a real httpd triggering a real denial, nothing is fabricated.
        assert not (sandbox / 'audit.log').exists()
        assert _no_dnf(fake)


class TestServiceFaultsWithoutHttpd:
    def test_firewall_fault_skips_cleanly(self, no_httpd):
        fake, _ = no_httpd
        ok, msg = ts.FirewallHttpBlockedFaultTask().inject_fault()
        assert ok is False
        assert 'not installed' in msg
        assert _no_dnf(fake)

    def test_service_fault_skips_cleanly(self, no_httpd):
        fake, _ = no_httpd
        task = ts.HttpdDisabledFaultTask()
        task.generate()
        ok, msg = task.inject_fault()
        assert ok is False
        assert 'not installed' in msg
        assert _no_dnf(fake)


class TestSeedAvcHelper:
    def test_seed_appends_parseable_record(self, no_httpd):
        fake, sandbox = no_httpd
        ts._seed_avc_denial('{ read } for pid=1 comm="httpd" tclass=file',
                            'SELinux is preventing httpd ...')
        line = (sandbox / 'audit.log').read_text().strip()
        assert line.startswith('type=AVC msg=audit(')
        # timestamp:serial framing intact
        assert '): avc:  denied  ' in line
        # journal mirror attempted via logger
        assert any(c and c[0] == 'logger' for c in fake.calls)
