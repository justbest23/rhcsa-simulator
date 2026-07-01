"""
Safety tests for core.full_reset — this reset is destructive, so the
classification logic that decides what gets removed must never match real
system repos, real accounts, or system swap.
"""

from core import full_reset as fr


class TestPracticeUserMatching:
    def test_matches_generated_practice_users(self):
        for name in ('user5', 'user12', 'alice7', 'bob10', 'nginxsvc3',
                     'sudopractice', 'operator4'):
            assert fr._is_practice_user(name), name

    def test_never_matches_real_accounts(self):
        for name in ('root', 'justbest23', 'admin', 'alice', 'bob',
                     'nginx', 'postgres', 'user', 'user123'):
            assert not fr._is_practice_user(name), name


class TestPracticeGroupMatching:
    def test_matches_generated_groups(self):
        for name in ('devteam03', 'qagroup12', 'opsgroup99'):
            assert fr._GROUP_PAT.match(name), name

    def test_never_matches_system_groups(self):
        for name in ('wheel', 'root', 'users', 'devteam', 'devteam3'):
            assert not fr._GROUP_PAT.match(name), name


class TestRepoKeepList:
    def test_system_repos_are_kept(self, tmp_path, monkeypatch):
        repo_dir = tmp_path
        for f in ('redhat.repo', 'rhel-baseos.repo', 'redhat-extra.repo',
                  'docker-ce.repo', 'epel.repo', 'notes.txt'):
            (repo_dir / f).write_text('[x]\n')

        real_listdir = fr.os.listdir
        monkeypatch.setattr(fr.os, 'listdir',
                            lambda d: real_listdir(repo_dir) if d == '/etc/yum.repos.d' else real_listdir(d))
        found = {fr.os.path.basename(p) for p in fr.list_nondefault_repos()}
        assert found == {'docker-ce.repo', 'epel.repo'}


class TestSystemSwapGuard:
    def test_system_swap_devices_are_protected(self):
        for dev in ('/dev/nvme0n1p3', '/dev/mapper/rhel-swap', '/dev/dm-1'):
            assert fr._system_swap(dev), dev

    def test_practice_swap_is_not_protected(self):
        for dev in ('/swapfile', '/var/swap', '/dev/loop2p1'):
            assert not fr._system_swap(dev), dev


class TestPreviewShape:
    def test_preview_returns_expected_categories(self):
        data = fr.preview()
        for key in ('Third-party repos', 'Flatpak apps', 'Practice users',
                    'Lab files/dirs'):
            assert key in data
            assert isinstance(data[key], list)
