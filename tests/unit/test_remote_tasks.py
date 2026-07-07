"""Remote (second-machine) tasks: registry gating, validation over the faked
SSH layer, and restore records."""

import pytest

from core import lab_machine
import tasks.troubleshooting as ts
from tasks.registry import TaskRegistry
from tasks.remote import RemoteHostnameTask, RemoteUserTask, RemoteTimezoneTask


@pytest.fixture
def fault_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, 'FAULT_STATE_FILE', str(tmp_path / 'fault.json'))
    return tmp_path / 'fault.json'


@pytest.fixture
def linked(monkeypatch):
    monkeypatch.setattr(lab_machine, 'load_config',
                        lambda: {'host': 'labbox', 'user': 'root'})


class FakeRemote:
    def __init__(self, monkeypatch, values=None, ok=True):
        self.values = values or {}
        self.ok = ok
        self.run_scripts = []
        monkeypatch.setattr(lab_machine, 'read_values',
                            lambda script, **kw: (self.ok, self.values, ''))
        monkeypatch.setattr(lab_machine, 'run',
                            lambda script, **kw: (self.run_scripts.append(script)
                                                  or (0, '')))


class TestRegistryGating:
    def test_remote_tasks_hidden_without_link(self, monkeypatch):
        monkeypatch.setattr(lab_machine, 'get_host', lambda: None)
        monkeypatch.setitem(TaskRegistry._tasks, '_test_remote_only',
                            [RemoteHostnameTask])
        assert TaskRegistry.get_random_task(category='_test_remote_only') is None

    def test_remote_tasks_offered_when_linked(self, monkeypatch, linked):
        monkeypatch.setattr(lab_machine, 'get_host', lambda: 'labbox')
        monkeypatch.setitem(TaskRegistry._tasks, '_test_remote_only',
                            [RemoteHostnameTask])
        task = TaskRegistry.get_random_task(category='_test_remote_only')
        assert task is not None and task.id == 'remote_hostname_001'

    def test_all_remote_tasks_declare_the_flag(self):
        for cls in (RemoteHostnameTask, RemoteUserTask, RemoteTimezoneTask):
            assert cls.requires_lab_machine is True
            assert cls.has_fault_injection is True


class TestDescriptions:
    def test_descriptions_name_the_lab_machine(self, monkeypatch, linked):
        monkeypatch.setattr(lab_machine, 'get_host', lambda: '192.168.1.50')
        for cls in (RemoteHostnameTask, RemoteUserTask, RemoteTimezoneTask):
            t = cls().generate()
            assert 'lab machine (192.168.1.50)' in t.description


class TestHostnameTask:
    def test_inject_records_original_and_restore_replays_it(
            self, fault_file, linked, monkeypatch):
        remote = FakeRemote(monkeypatch, {'STATIC': 'old.example.com'})
        t = RemoteHostnameTask().generate(hostname='node2.lab.example.com')
        ok, _ = t.inject_fault()
        assert ok
        state = ts.load_fault_state(t.id)
        script = state['restore_info']['remote_restore_script']
        assert "hostnamectl set-hostname 'old.example.com'" in script
        ok, _ = t.restore_fault()
        assert ok
        assert any('old.example.com' in s for s in remote.run_scripts)
        assert ts.load_fault_state(t.id) is None

    def test_validate_pass_and_fail(self, linked, monkeypatch):
        t = RemoteHostnameTask().generate(hostname='node2.lab.example.com')
        FakeRemote(monkeypatch, {'STATIC': 'node2.lab.example.com'})
        assert t.validate().passed
        FakeRemote(monkeypatch, {'STATIC': 'wrong.example.com'})
        assert not t.validate().passed

    def test_unreachable_machine_fails_with_clear_message(self, linked,
                                                          monkeypatch):
        t = RemoteHostnameTask().generate(hostname='node2.lab.example.com')
        FakeRemote(monkeypatch, ok=False)
        result = t.validate()
        assert not result.passed
        assert 'Cannot reach the lab machine' in result.checks[0].message

    def test_inject_skips_cleanly_when_unreachable(self, fault_file, linked,
                                                   monkeypatch):
        FakeRemote(monkeypatch, ok=False)
        t = RemoteHostnameTask().generate()
        ok, msg = t.inject_fault()
        assert not ok and 'unreachable' in msg


class TestUserTask:
    def test_full_credit(self, linked, monkeypatch):
        t = RemoteUserTask().generate(username='rmuser42', uid=3100, group='wheel')
        FakeRemote(monkeypatch, {'UID': '3100',
                                 'GROUPS': 'rmuser42 wheel',
                                 'HASH': '$6$salt$hash'})
        result = t.validate()
        assert result.passed and result.score == 10

    def test_wrong_uid_and_no_password(self, linked, monkeypatch):
        t = RemoteUserTask().generate(username='rmuser42', uid=3100, group='wheel')
        FakeRemote(monkeypatch, {'UID': '4000',
                                 'GROUPS': 'rmuser42',
                                 'HASH': '!!'})
        result = t.validate()
        assert not result.passed and result.score == 0

    def test_restore_record_deletes_user(self, fault_file, linked, monkeypatch):
        FakeRemote(monkeypatch, {'UP': 'yes'})
        t = RemoteUserTask().generate(username='rmuser42', uid=3100)
        assert t.inject_fault()[0]
        script = ts.load_fault_state(t.id)['restore_info']['remote_restore_script']
        assert "userdel -r 'rmuser42'" in script


class TestTimezoneTask:
    def test_validate(self, linked, monkeypatch):
        t = RemoteTimezoneTask().generate(timezone='Europe/Vienna')
        FakeRemote(monkeypatch, {'TZ': 'Europe/Vienna'})
        assert t.validate().passed
        FakeRemote(monkeypatch, {'TZ': 'UTC'})
        assert not t.validate().passed

    def test_inject_records_original_zone(self, fault_file, linked, monkeypatch):
        FakeRemote(monkeypatch, {'TZ': 'America/New_York'})
        t = RemoteTimezoneTask().generate(timezone='Asia/Kolkata')
        assert t.inject_fault()[0]
        script = ts.load_fault_state(t.id)['restore_info']['remote_restore_script']
        assert "timedatectl set-timezone 'America/New_York'" in script


class TestCrashRecoveryDispatch:
    def test_restore_any_active_fault_replays_remote_records(
            self, fault_file, linked, monkeypatch):
        remote = FakeRemote(monkeypatch, {'STATIC': 'orig.example.com'})
        t = RemoteHostnameTask().generate()
        assert t.inject_fault()[0]
        ok, msg = ts.restore_any_active_fault()
        assert ok
        assert any('orig.example.com' in s for s in remote.run_scripts)
        assert 'labbox' in msg
