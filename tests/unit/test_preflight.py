"""
Tests for core.preflight — the startup dependency check that warns when
exam-relevant packages (httpd, vsftpd, ...) aren't installed.
"""

from core import preflight


def test_check_dependencies_uses_rpm_status(monkeypatch):
    def fake_rpm_installed(pkg):
        return pkg == 'httpd'

    monkeypatch.setattr(preflight, '_rpm_installed', fake_rpm_installed)
    statuses = preflight.check_dependencies(['httpd', 'vsftpd'])
    assert statuses == {'httpd': True, 'vsftpd': False}


def test_missing_packages_excludes_installed_and_unknown():
    statuses = {'httpd': True, 'vsftpd': False, 'samba': None}
    assert preflight.missing_packages(statuses) == ['vsftpd']


def test_missing_packages_sorted():
    statuses = {'vsftpd': False, 'httpd': False, 'nfs-utils': False}
    assert preflight.missing_packages(statuses) == ['httpd', 'nfs-utils', 'vsftpd']


def test_warn_missing_noop_when_nothing_missing(capsys):
    preflight.warn_missing([])
    assert capsys.readouterr().out == ''


def test_warn_missing_lists_packages_and_install_command(capsys):
    preflight.warn_missing(['httpd', 'vsftpd'])
    out = capsys.readouterr().out
    assert 'httpd' in out
    assert 'vsftpd' in out
    assert 'dnf install -y httpd vsftpd' in out


def test_rpm_installed_returns_none_when_rpm_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(preflight.subprocess, 'run', fake_run)
    assert preflight._rpm_installed('httpd') is None
