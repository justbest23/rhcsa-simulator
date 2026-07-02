"""
Tests for candidate-created systemd unit / helper-script cleanup in lab_cleanup.

These tasks build a .timer + .service pair under /etc/systemd/system with no
per-task teardown, so lab_cleanup must sweep them by name/prefix. We point the
unit dir and script list at a tmp dir so nothing on the host is touched, and use
dry_run so no `systemctl` call is needed.
"""

import pytest

from core import lab_cleanup


@pytest.fixture
def unit_dir(tmp_path, monkeypatch):
    d = tmp_path / "systemd"
    d.mkdir()
    monkeypatch.setattr(lab_cleanup, "_UNIT_DIR", str(d))
    return d


def _touch(path):
    path.write_text("# unit\n")


class TestFindUnits:
    def test_matches_fixed_names_and_prefixes(self, unit_dir):
        _touch(unit_dir / "backup-logs.timer")
        _touch(unit_dir / "backup-logs.service")
        _touch(unit_dir / "scheduled-rotate.timer")     # reported leftover
        _touch(unit_dir / "scheduled-rotate.service")
        _touch(unit_dir / "post-boot-init.timer")
        _touch(unit_dir / "repeat-poll.service")
        _touch(unit_dir / "converted-cron-42.timer")

        found = {p.rsplit("/", 1)[1] for p in lab_cleanup._find_units()}
        assert "scheduled-rotate.timer" in found
        assert "scheduled-rotate.service" in found
        assert "backup-logs.timer" in found
        assert "post-boot-init.timer" in found
        assert "repeat-poll.service" in found
        assert "converted-cron-42.timer" in found

    def test_ignores_unrelated_and_wellknown_units(self, unit_dir):
        _touch(unit_dir / "fstrim.timer")            # well-known system timer
        _touch(unit_dir / "logrotate.timer")
        _touch(unit_dir / "my-own-app.service")      # user's real unit
        found = lab_cleanup._find_units()
        assert found == []


class TestDryRunReporting:
    def test_reports_units_and_scripts(self, unit_dir, tmp_path, monkeypatch):
        _touch(unit_dir / "scheduled-rotate.timer")
        script = tmp_path / "rotate-logs.sh"
        script.write_text("#!/bin/sh\n")
        monkeypatch.setattr(lab_cleanup, "LOCAL_SCRIPTS", [str(script)])
        monkeypatch.setattr(lab_cleanup, "_LOCAL_SCRIPT_SET", {str(script)})

        actions = lab_cleanup.clean_units(dry_run=True)
        assert any("scheduled-rotate.timer" in a for a in actions)
        assert any(str(script) in a for a in actions)
        # Dry run must not delete anything.
        assert (unit_dir / "scheduled-rotate.timer").exists()
        assert script.exists()

    def test_find_leftovers_includes_units(self, unit_dir):
        _touch(unit_dir / "scheduled-rotate.service")
        leftovers = lab_cleanup.find_leftovers()
        assert any(p.endswith("scheduled-rotate.service") for p in leftovers)


class TestScriptGuard:
    def test_script_removal_is_exact_match_only(self, tmp_path, monkeypatch):
        keep = tmp_path / "important.sh"
        keep.write_text("keep me\n")
        target = tmp_path / "rotate-logs.sh"
        target.write_text("#!/bin/sh\n")
        # Only `target` is in the allowlist; `keep` must never be removed.
        monkeypatch.setattr(lab_cleanup, "LOCAL_SCRIPTS", [str(target)])
        monkeypatch.setattr(lab_cleanup, "_LOCAL_SCRIPT_SET", {str(target)})
        monkeypatch.setattr(lab_cleanup, "_UNIT_DIR", str(tmp_path / "none"))

        lab_cleanup.clean_units(dry_run=False)
        assert not target.exists()
        assert keep.exists()
