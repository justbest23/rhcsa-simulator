"""Bad-task flagging: store behavior and registry filtering."""

import json

import pytest

from core import task_flags
from tasks.base import BaseTask
from tasks.registry import TaskRegistry


@pytest.fixture
def flags_file(tmp_path, monkeypatch):
    path = tmp_path / 'flagged_tasks.json'
    monkeypatch.setattr(task_flags, 'FLAGS_PATH', str(path))
    return path


class _FakeTask(BaseTask):
    _ID = 'fake_task_001'

    def __init__(self):
        super().__init__(id=self._ID, category='networking',
                         difficulty='exam', points=5)

    def generate(self, **params):
        self.description = 'fake'
        return self

    def validate(self):
        raise NotImplementedError


class _FakeTaskB(_FakeTask):
    _ID = 'fake_task_002'


class TestFlagStore:
    def test_seeds_chroot_task_on_first_use(self, flags_file):
        ids = task_flags.flagged_ids()
        assert 'boot_recovery_chroot_practice_001' in ids
        assert flags_file.exists()
        data = json.loads(flags_file.read_text())
        assert data['boot_recovery_chroot_practice_001']['reason']

    def test_flag_unflag_roundtrip(self, flags_file):
        assert task_flags.flag('some_task_001', 'too vague')
        assert task_flags.is_flagged('some_task_001')
        assert task_flags.all_flags()['some_task_001']['reason'] == 'too vague'
        assert not task_flags.flag('some_task_001')          # idempotent
        assert task_flags.unflag('some_task_001')
        assert not task_flags.is_flagged('some_task_001')
        assert not task_flags.unflag('some_task_001')

    def test_corrupt_file_degrades_to_no_flags(self, flags_file):
        flags_file.write_text('{ not json')
        assert task_flags.flagged_ids() == set()


class TestRegistryFiltering:
    def test_flagged_task_never_selected(self, flags_file, monkeypatch):
        monkeypatch.setitem(TaskRegistry._tasks, '_test_flags',
                            [_FakeTask, _FakeTaskB])
        task_flags.flag(_FakeTask._ID, 'bad')
        for _ in range(20):
            task = TaskRegistry.get_random_task(category='_test_flags')
            assert task is not None
            assert task.id == _FakeTaskB._ID

    def test_all_flagged_yields_none(self, flags_file, monkeypatch):
        monkeypatch.setitem(TaskRegistry._tasks, '_test_flags',
                            [_FakeTask, _FakeTaskB])
        task_flags.flag(_FakeTask._ID)
        task_flags.flag(_FakeTaskB._ID)
        assert TaskRegistry.get_random_task(category='_test_flags') is None

    def test_unflagged_returns_to_rotation(self, flags_file, monkeypatch):
        monkeypatch.setitem(TaskRegistry._tasks, '_test_flags', [_FakeTask])
        task_flags.flag(_FakeTask._ID)
        assert TaskRegistry.get_random_task(category='_test_flags') is None
        task_flags.unflag(_FakeTask._ID)
        task = TaskRegistry.get_random_task(category='_test_flags')
        assert task is not None and task.id == _FakeTask._ID
