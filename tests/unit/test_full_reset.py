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
        # rhel-baseos.repo is REMOVABLE despite the protected rhel- prefix:
        # it's a name the dual-repo task generates (real RHEL repos only live
        # in redhat.repo), and treating it as a system repo made it survive
        # every reset.
        repo_dir = tmp_path
        for f in ('redhat.repo', 'rhel-baseos.repo', 'redhat-extra.repo',
                  'docker-ce.repo', 'epel.repo', 'notes.txt'):
            (repo_dir / f).write_text('[x]\n')

        real_listdir = fr.os.listdir
        monkeypatch.setattr(fr.os, 'listdir',
                            lambda d: real_listdir(repo_dir) if d == '/etc/yum.repos.d' else real_listdir(d))
        found = {fr.os.path.basename(p) for p in fr.list_nondefault_repos()}
        assert found == {'docker-ce.repo', 'epel.repo', 'rhel-baseos.repo'}


class TestSystemSwapGuard:
    def test_system_swap_devices_are_protected(self):
        for dev in ('/dev/nvme0n1p3', '/dev/mapper/rhel-swap', '/dev/dm-1'):
            assert fr._system_swap(dev), dev

    def test_practice_swap_is_not_protected(self):
        for dev in ('/swapfile', '/var/swap', '/dev/loop2p1'):
            assert not fr._system_swap(dev), dev


class TestMountClassification:
    def test_nfs_and_practice_filesystems_are_unmounted(self):
        assert fr._is_practice_mount('/mnt/nfsdata', 'nfsserver:/exports/x', 'nfs4')
        assert fr._is_practice_mount('/mnt/shared', 'nfsserver:/exports/y', 'nfs')
        assert fr._is_practice_mount('/mnt/data', '/dev/loop2p1', 'xfs')
        assert fr._is_practice_mount('/srv/acltest5', '/dev/loop3', 'ext4')
        # non-system VG-backed LVM mount
        assert fr._is_practice_mount('/mnt/lvm', '/dev/mapper/vg_test-lv_data', 'xfs')

    def test_system_mounts_are_never_unmounted(self):
        assert not fr._is_practice_mount('/', '/dev/mapper/rhel-root', 'xfs')
        assert not fr._is_practice_mount('/boot', '/dev/nvme0n1p2', 'xfs')
        assert not fr._is_practice_mount('/home', '/dev/mapper/rhel-home', 'xfs')
        assert not fr._is_practice_mount('/boot/efi', '/dev/nvme0n1p1', 'vfat')
        # a system-VG LV mounted somewhere odd must still be protected
        assert not fr._is_practice_mount('/mnt/whatever', '/dev/mapper/rhel-var', 'xfs')

    def test_dm_vg_parsing_handles_escaped_dashes(self):
        assert fr._dm_vg('/dev/mapper/rhel-root') == 'rhel'
        assert fr._dm_vg('/dev/mapper/vg_test-lv_data') == 'vg_test'
        assert fr._dm_vg('/dev/mapper/vg--x-lv') == 'vg-x'


class TestPreviewShape:
    def test_preview_returns_expected_categories(self):
        data = fr.preview()
        for key in ('Third-party repos', 'Flatpak apps', 'Practice users',
                    'Lab files/dirs'):
            assert key in data
            assert isinstance(data[key], list)
