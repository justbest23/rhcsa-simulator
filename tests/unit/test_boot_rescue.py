"""Boot-rescue lab: scenario lifecycle, validation and escape hatch, with the
SSH layer faked so no network is touched."""

import json

import pytest

from core import lab_machine, boot_rescue


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = tmp_path / 'boot_rescue.json'
    monkeypatch.setattr(boot_rescue, 'STATE_PATH', str(path))
    monkeypatch.setattr(lab_machine, 'STATE_DIR', str(tmp_path))
    return path


@pytest.fixture
def linked(monkeypatch):
    monkeypatch.setattr(lab_machine, 'load_config',
                        lambda: {'host': 'labbox', 'user': 'root'})
    monkeypatch.setattr(lab_machine, 'key_works', lambda **kw: True)


class FakeRemote:
    """Stands in for lab_machine.read_values; records scripts, plays a
    machine whose root hash/boot id can be mutated by the test."""

    def __init__(self, monkeypatch):
        self.hash = '$6$orig$hash'
        self.boot_id = 'boot-1'
        self.ctx = 'system_u:object_r:shadow_t:s0'
        self.sys_state = 'running'
        self.relabel = 'no'
        self.rdbreak = '0'
        self.scripts = []
        monkeypatch.setattr(lab_machine, 'read_values', self)

    def __call__(self, script, host=None, user=None, timeout=120):
        self.scripts.append(script)
        if 'chpasswd' in script:
            self.hash = '$6$planted$hash'
            return True, {'NEW_HASH': self.hash}, ''
        if 'usermod -p' in script:
            self.hash = script.split("'")[1]
            return True, {'RESTORED': 'yes'}, ''
        return True, {
            'BOOT_ID': self.boot_id,
            'ROOT_HASH': self.hash,
            'SHADOW_CTX': self.ctx,
            'SYS_STATE': self.sys_state,
            'RELABEL_PENDING': self.relabel,
            'RDBREAK_BOOTS': self.rdbreak,
        }, ''


class TestPasswordGeneration:
    def test_console_safe_alphabet(self):
        for _ in range(50):
            pw = boot_rescue.generate_password()
            assert len(pw) == 10
            assert not set(pw) & set("l1o0'\"\\$`| ;&<>")


class TestStart:
    def test_refuses_without_link(self, state_file, monkeypatch):
        monkeypatch.setattr(lab_machine, 'load_config', lambda: None)
        ok, msg = boot_rescue.start()
        assert not ok and 'No lab machine linked' in msg

    def test_refuses_without_working_key(self, state_file, monkeypatch):
        monkeypatch.setattr(lab_machine, 'load_config',
                            lambda: {'host': 'labbox', 'user': 'root'})
        monkeypatch.setattr(lab_machine, 'key_works', lambda **kw: False)
        ok, msg = boot_rescue.start()
        assert not ok and 'Key-based SSH' in msg

    def test_success_records_original_and_planted_hash(self, state_file, linked,
                                                       monkeypatch):
        remote = FakeRemote(monkeypatch)
        ok, msg = boot_rescue.start()
        assert ok and 'labbox' in msg
        state = json.loads(state_file.read_text())
        assert state['original_hash'] == '$6$orig$hash'
        assert state['planted_hash'] == '$6$planted$hash'
        assert state['planted_password']
        # The secret travels inside the script (stdin), and the scramble ran.
        assert any(state['planted_password'] in s for s in remote.scripts)

    def test_refuses_double_start(self, state_file, linked, monkeypatch):
        FakeRemote(monkeypatch)
        assert boot_rescue.start()[0]
        ok, msg = boot_rescue.start()
        assert not ok and 'already active' in msg

    def test_state_file_is_root_only(self, state_file, linked, monkeypatch):
        FakeRemote(monkeypatch)
        boot_rescue.start()
        assert (state_file.stat().st_mode & 0o777) == 0o600


class TestValidate:
    def _start(self, monkeypatch):
        remote = FakeRemote(monkeypatch)
        assert boot_rescue.start()[0]
        return remote

    def test_no_scenario(self, state_file):
        checks, method, err = boot_rescue.validate()
        assert checks is None and 'No rescue scenario' in err

    def test_unrecovered_machine_fails(self, state_file, linked, monkeypatch):
        self._start(monkeypatch)
        checks, method, err = boot_rescue.validate()
        results = dict((n, p) for n, p, _ in checks)
        assert results['password_changed'] is False
        assert results['rebooted'] is False

    def test_full_recovery_passes(self, state_file, linked, monkeypatch):
        remote = self._start(monkeypatch)
        remote.hash = '$6$candidate$new'
        remote.boot_id = 'boot-2'
        checks, method, err = boot_rescue.validate()
        assert err is None
        assert all(p is not False for _, p, _ in checks)
        assert 'init=/bin/bash' in method  # no rd.break boot seen

    def test_rdbreak_method_detected(self, state_file, linked, monkeypatch):
        remote = self._start(monkeypatch)
        remote.hash = '$6$candidate$new'
        remote.boot_id = 'boot-2'
        remote.rdbreak = '1'
        _, method, _ = boot_rescue.validate()
        assert method.startswith('rd.break')

    def test_mislabeled_shadow_fails_selinux_check(self, state_file, linked,
                                                   monkeypatch):
        remote = self._start(monkeypatch)
        remote.hash = '$6$candidate$new'
        remote.boot_id = 'boot-2'
        remote.ctx = 'system_u:object_r:etc_t:s0'
        checks, _, _ = boot_rescue.validate()
        results = dict((n, p) for n, p, _ in checks)
        assert results['selinux_context'] is False

    def test_pending_autorelabel_is_note_not_failure(self, state_file, linked,
                                                     monkeypatch):
        remote = self._start(monkeypatch)
        remote.hash = '$6$candidate$new'
        remote.boot_id = 'boot-2'
        remote.relabel = 'yes'
        checks, _, _ = boot_rescue.validate()
        results = dict((n, p) for n, p, _ in checks)
        assert results['relabel_pending'] is None


class TestGiveUp:
    def test_reveals_and_restores_original_hash(self, state_file, linked,
                                                monkeypatch):
        remote = FakeRemote(monkeypatch)
        assert boot_rescue.start()[0]
        planted = json.loads(state_file.read_text())['planted_password']
        ok, msg = boot_rescue.give_up(restore=True)
        assert ok and planted in msg
        assert remote.hash == '$6$orig$hash'      # restored exactly
        assert not boot_rescue.is_active()

    def test_reset_hook_noop_without_scenario(self, state_file):
        boot_rescue.reset_for_machine_reset()     # must not raise


class TestReadValues:
    def test_parses_only_key_value_lines(self, monkeypatch):
        monkeypatch.setattr(lab_machine, 'run', lambda *a, **kw:
                            (0, 'noise\nBOOT_ID=abc\nnot=this\nX Y=Z\nCTX=a b\n'))
        ok, values, _ = lab_machine.read_values('x', host='h')
        assert ok
        assert values == {'BOOT_ID': 'abc', 'CTX': 'a b'}

    def test_run_without_link_is_soft_error(self, monkeypatch):
        monkeypatch.setattr(lab_machine, 'load_config', lambda: None)
        rc, out = lab_machine.run('true')
        assert rc is None and 'no lab machine linked' in out


class TestWalkthrough:
    def test_covers_both_methods_and_sysrq(self):
        text = boot_rescue.WALKTHROUGH
        assert 'rd.break' in text
        assert 'init=/bin/bash' in text
        assert 'echo b > /proc/sysrq-trigger' in text
        assert 'autorelabel' in text
        assert 'Give root password for maintenance' in text
