"""
Tests for the exam device pool / allocator (utils.helpers) and the
generate_exam disk-budget cap (tasks.registry). These avoid creating real
loop devices by stubbing the pool builder.
"""
import pytest
from unittest.mock import patch

from utils import helpers
from tasks.registry import TaskRegistry

pytestmark = pytest.mark.unit


class TestDeviceAllocator:
    def test_allocates_distinct_then_none(self):
        pool = ['/dev/loop0', '/dev/loop1', '/dev/sda']
        with patch.object(helpers, 'build_device_pool', return_value=pool):
            helpers.begin_device_allocation()
            try:
                got = [helpers.allocate_practice_device() for _ in range(4)]
            finally:
                helpers.end_device_allocation()
        assert got[:3] == pool          # distinct, in order
        assert got[3] is None           # exhausted
        assert len(set(got[:3])) == 3   # no duplicates

    def test_inactive_by_default(self):
        assert helpers.device_allocation_active() is False
        assert helpers.allocate_practice_device() is None

    def test_get_practice_device_uses_allocator_when_active(self):
        pool = ['/dev/loopA', '/dev/loopB']
        with patch.object(helpers, 'build_device_pool', return_value=pool):
            helpers.begin_device_allocation()
            try:
                a = helpers.get_practice_device()
                b = helpers.get_practice_device()
            finally:
                helpers.end_device_allocation()
        assert a == '/dev/loopA' and b == '/dev/loopB'  # distinct per task


class TestExamDiskBudget:
    def test_generate_exam_respects_disk_budget(self):
        TaskRegistry.initialize()
        tasks = TaskRegistry.generate_exam(20, disk_budget=1)
        used = sum(getattr(t, 'disk_slots', 0) for t in tasks)
        assert used <= 1, f"disk_slots used ({used}) exceeded budget of 1"

    def test_zero_budget_yields_no_disk_tasks(self):
        TaskRegistry.initialize()
        tasks = TaskRegistry.generate_exam(20, disk_budget=0)
        assert all(getattr(t, 'disk_slots', 0) == 0 for t in tasks)
