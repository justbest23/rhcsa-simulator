"""Extent-based LVM tasks: generation invariants and extent math."""

import pytest

import tasks.lvm as lvm
from tasks.lvm import LVMExtentWorkflowTask, CreateLVTask, ExtendLVTask


class _Result:
    def __init__(self, stdout, success=True):
        self.stdout = stdout
        self.success = success


class TestExtentWorkflowGeneration:
    def test_all_combos_fit_practice_disk_and_xfs_minimum(self):
        for pe, count in LVMExtentWorkflowTask._COMBOS:
            total = pe * count
            assert total == 320, f"combo ({pe},{count}) must total 320MiB"
            assert total > 300  # RHEL 10 mkfs.xfs minimum
            assert total < 480  # fits a 500MB loop disk incl. VG overhead

    def test_description_states_pe_size_and_extent_count(self):
        t = LVMExtentWorkflowTask().generate(device='/dev/loop9', combo=(16, 20))
        assert '16 MiB' in t.description
        assert '20 extents' in t.description
        assert t.pe_mib == 16 and t.extents == 20

    def test_hints_do_not_leak_beyond_commands(self):
        t = LVMExtentWorkflowTask().generate(device='/dev/loop9', combo=(8, 40))
        assert any('vgcreate -s 8M' in h for h in t.hints)
        assert any('lvcreate -l 40' in h for h in t.hints)


class TestExtentMath:
    def test_vg_extent_size_parses_vgs_output(self, monkeypatch):
        monkeypatch.setattr(lvm, 'execute_safe',
                            lambda cmd: _Result('  16.00\n'))
        assert lvm._vg_extent_size_mib('vg_x') == 16.0

    def test_lv_extent_count_divides_size_by_pe(self, monkeypatch):
        def fake(cmd):
            if 'lv_size' in cmd:
                return _Result('  320.00\n')
            return _Result('  16.00\n')
        monkeypatch.setattr(lvm, 'execute_safe', fake)
        assert lvm._lv_extent_count('vg_x', 'lv_x') == 20

    def test_missing_vg_returns_none(self, monkeypatch):
        monkeypatch.setattr(lvm, 'execute_safe',
                            lambda cmd: _Result('', success=False))
        assert lvm._vg_extent_size_mib('vg_gone') is None
        assert lvm._lv_extent_count('vg_gone', 'lv_gone') is None


class TestExtentVariantsOfExistingTasks:
    def test_create_lv_extent_phrasing_sets_consistent_size(self):
        t = CreateLVTask().generate(use_extents=True, device='/dev/loop9')
        assert t.pe_mib in (8, 16)
        assert t.lv_size_mb == t.pe_mib * t.extents
        assert f'{t.extents} extents' in t.description

    def test_create_lv_classic_phrasing_has_no_pe(self):
        t = CreateLVTask().generate(use_extents=False, device='/dev/loop9')
        assert t.pe_mib is None
        assert 'extent' not in t.description

    def test_extend_lv_extent_phrasing_math(self):
        t = ExtendLVTask().generate(use_extents=True, device='/dev/loop9')
        assert t.pe_mib == 16
        assert t.initial_mb == 96          # 6 extents x 16MiB
        assert t.target_mb == t.initial_mb + t.extend_by_mb
        assert 'extents' in t.description

    def test_extend_lv_classic_unchanged(self):
        t = ExtendLVTask().generate(use_extents=False, device='/dev/loop9')
        assert t.pe_mib is None
        assert t.initial_mb == 100
