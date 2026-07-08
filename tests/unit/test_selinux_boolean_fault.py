"""
Regression tests for issues #69 and #76: SELinux troubleshooting tasks must
leave real, findable evidence behind — a candidate running
`ausearch -m avc -ts recent | audit2why` should never come up empty.

Three distinct bugs were fixed:

  * TroubleshootSELinuxDenialTask (tasks/selinux.py) did nothing at all for
    its "boolean" scenario — the boolean was never turned off and no AVC
    evidence was ever written, so there was no fault to find in the first
    place. (#69)
  * SELinuxHttpdBooleanFaultTask (tasks/troubleshooting.py) tried to trigger
    a real denial by curling http://localhost:8080 as a *client* — but that
    never makes httpd itself originate an outbound connection, so no genuine
    name_connect denial was ever produced even with httpd installed. (#69)
  * TroubleshootSELinuxDenialTask's "fcontext" scenarios (httpd/nginx/samba
    directories) never wire the mislabelled directory into the service's
    real config, so the service never touches it and no genuine denial can
    occur no matter what the candidate does — ausearch came up empty and,
    since the fault never affected anything the service actually serves,
    curl kept working whether or not SELinux was fixed. (#76)
"""

import subprocess
from types import SimpleNamespace

import pytest

from tasks import selinux as sel
from tasks import troubleshooting as ts

pytestmark = pytest.mark.unit


class FakeSubprocess:
    """Stand-in for subprocess.run, tracking calls and current boolean state."""

    def __init__(self):
        self.calls = []
        self.boolean_state = 'on'

    def run(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        prog = cmd[0]
        if prog == 'getsebool':
            return SimpleNamespace(returncode=0,
                                    stdout=f'{cmd[1]} --> {self.boolean_state}',
                                    stderr='')
        if prog == 'setsebool':
            self.boolean_state = cmd[-1]
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        return SimpleNamespace(returncode=0, stdout='', stderr='')


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    fake = FakeSubprocess()
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: fake.run(cmd, **kw))
    monkeypatch.setattr(ts, '_run', lambda cmd, **kw: fake.run(cmd, **kw))
    monkeypatch.setattr(ts, 'FAULT_STATE_FILE', str(tmp_path / 'fault.json'))
    monkeypatch.setattr(ts, '_AUDIT_LOG', str(tmp_path / 'audit.log'))
    return fake, tmp_path


class TestTroubleshootSELinuxDenialBooleanScenario:
    def _boolean_task(self):
        task = sel.TroubleshootSELinuxDenialTask()
        task.service = 'httpd'
        task.directory = None
        task.expected_context = 'httpd_can_network_connect'
        task.fix_type = 'boolean'
        return task

    def test_inject_turns_boolean_off_and_seeds_avc(self, sandbox):
        fake, tmp_path = sandbox
        task = self._boolean_task()

        ok, msg = task.inject_fault()

        assert ok, msg
        assert fake.boolean_state == 'off'
        assert any(c[0] == 'setsebool' and c[-1] == 'off' for c in fake.calls)

        log = tmp_path / 'audit.log'
        assert log.exists(), "ausearch would find nothing without this"
        content = log.read_text()
        assert 'type=AVC' in content
        assert 'name_connect' in content and 'httpd_t' in content

    def test_restore_sets_boolean_back_to_original(self, sandbox):
        fake, _ = sandbox
        fake.boolean_state = 'on'
        task = self._boolean_task()

        task.inject_fault()
        assert fake.boolean_state == 'off'

        ok, msg = task.restore_fault()

        assert ok, msg
        assert fake.boolean_state == 'on'

    def test_fcontext_scenario_untouched(self, sandbox):
        """The pre-existing fcontext path (directory-based) must keep working."""
        fake, tmp_path = sandbox
        task = sel.TroubleshootSELinuxDenialTask()
        task.service = 'httpd'
        task.directory = str(tmp_path / 'custom')
        task.expected_context = 'httpd_sys_content_t'
        task.fix_type = 'fcontext'

        ok, msg = task.inject_fault()

        assert ok, msg
        assert (tmp_path / 'custom' / 'index.html').exists()
        assert any(c[0] == 'chcon' for c in fake.calls)
        # No boolean flip for the fcontext scenario
        assert not any(c[0] == 'setsebool' for c in fake.calls)

    @pytest.mark.parametrize("service,expected_context,comm", [
        ("httpd", "httpd_sys_content_t", "httpd"),
        ("httpd", "httpd_sys_rw_content_t", "httpd"),
        ("samba", "samba_share_t", "smbd"),
        ("nginx", "httpd_sys_content_t", "nginx"),
    ])
    def test_fcontext_scenario_seeds_avc(self, sandbox, service, expected_context, comm):
        """Issue #76: the directory these scenarios mislabel is never wired
        into the service's real config, so nothing ever makes the service
        touch it and a genuine denial can't be relied on to occur. Seed the
        evidence a real one would have left."""
        _, tmp_path = sandbox
        task = sel.TroubleshootSELinuxDenialTask()
        task.service = service
        task.directory = str(tmp_path / 'custom')
        task.expected_context = expected_context
        task.fix_type = 'fcontext'

        ok, msg = task.inject_fault()

        assert ok, msg
        log = tmp_path / 'audit.log'
        assert log.exists(), "ausearch would find nothing without this"
        content = log.read_text()
        assert 'type=AVC' in content
        assert f'comm="{comm}"' in content


class TestSELinuxHttpdBooleanFaultTaskAlwaysSeedsAvc:
    def test_seeds_avc_even_when_httpd_is_installed(self, sandbox, monkeypatch):
        """Previously, when httpd was installed, inject_fault() only curled
        localhost:8080 (a no-op for triggering httpd's own name_connect
        denial) and left the audit log untouched."""
        fake, tmp_path = sandbox

        def fake_run(cmd, **kw):
            if cmd[:2] == ['rpm', '-q']:
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            return fake.run(cmd, **kw)

        monkeypatch.setattr(ts, '_run', fake_run)

        task = ts.SELinuxHttpdBooleanFaultTask()
        ok, msg = task.inject_fault()

        assert ok, msg
        log = tmp_path / 'audit.log'
        assert log.exists(), "ausearch would find nothing without this"
        content = log.read_text()
        assert 'name_connect' in content and 'httpd_t' in content
