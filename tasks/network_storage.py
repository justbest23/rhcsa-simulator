"""
Network storage tasks for RHCSA exam (NFS, Autofs, SMB/CIFS).
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("network_storage")
class MountNFSShareTask(BaseTask):
    """Mount an NFS share manually."""

    def __init__(self):
        super().__init__(
            id="nfs_mount_001",
            category="network_storage",
            difficulty="medium",
            points=10
        )
        self.nfs_server = None
        self.nfs_export = None
        self.mount_point = None

    def generate(self, **params):
        """Generate NFS mount task."""
        self.nfs_server = params.get('server', 'server1.example.com')
        self.nfs_export = params.get('export', '/share/data')
        self.mount_point = params.get('mount_point', '/mnt/nfsdata')

        self.description = (
            f"Mount an NFS share:\n"
            f"  - NFS Server: {self.nfs_server}\n"
            f"  - Export path: {self.nfs_export}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Create mount point if needed\n"
            f"  - Mount read-write"
        )

        self.hints = [
            f"Discover exports: showmount -e {self.nfs_server}",
            f"Create mount point: mkdir -p {self.mount_point}",
            f"Mount: mount -t nfs {self.nfs_server}:{self.nfs_export} {self.mount_point}",
            "Common options: -o rw,sync,hard,intr",
            f"Verify: mount | grep {self.mount_point}"
        ]

        return self

    def validate(self):
        """Validate NFS mount."""
        checks = []
        total_points = 0

        import os

        # Check 1: Mount point exists (3 points)
        if os.path.isdir(self.mount_point):
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=True,
                points=3,
                message=f"Mount point {self.mount_point} exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Mount point {self.mount_point} does not exist"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: NFS is mounted (7 points)
        result = execute_safe(['mount'])
        if result.success and self.mount_point in result.stdout and 'nfs' in result.stdout:
            checks.append(ValidationCheck(
                name="nfs_mounted",
                passed=True,
                points=7,
                message=f"NFS share is mounted at {self.mount_point}"
            ))
            total_points += 7
        else:
            # Check /proc/mounts as backup
            result2 = execute_safe(['cat', '/proc/mounts'])
            if result2.success and self.mount_point in result2.stdout:
                checks.append(ValidationCheck(
                    name="nfs_mounted",
                    passed=True,
                    points=5,
                    message="Something is mounted (may not be NFS)"
                ))
                total_points += 5
            else:
                checks.append(ValidationCheck(
                    name="nfs_mounted",
                    passed=False,
                    points=0,
                    max_points=7,
                    message=f"NFS share is not mounted at {self.mount_point}"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("network_storage")
class PersistentNFSMountTask(BaseTask):
    """Configure persistent NFS mount in fstab."""

    def __init__(self):
        super().__init__(
            id="nfs_fstab_001",
            category="network_storage",
            difficulty="medium",
            points=12
        )
        self.nfs_server = None
        self.nfs_export = None
        self.mount_point = None

    def generate(self, **params):
        """Generate persistent NFS mount task."""
        self.nfs_server = params.get('server', 'nfsserver.example.com')
        self.nfs_export = params.get('export', '/exports/shared')
        self.mount_point = params.get('mount_point', '/mnt/shared')

        self.description = (
            f"Configure persistent NFS mount:\n"
            f"  - NFS Server: {self.nfs_server}\n"
            f"  - Export: {self.nfs_export}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Add to /etc/fstab for persistence\n"
            f"  - Use _netdev option (required for network mounts)\n"
            f"  - Mount should work after reboot"
        )

        self.hints = [
            f"Create mount point: mkdir -p {self.mount_point}",
            f"fstab entry format: {self.nfs_server}:{self.nfs_export} {self.mount_point} nfs defaults,_netdev 0 0",
            "Edit /etc/fstab with vim or nano",
            "_netdev waits for network before mounting",
            "Test without reboot: mount -a"
        ]

        return self

    def validate(self):
        """Validate persistent NFS mount."""
        checks = []
        total_points = 0

        import os

        # Check 1: Mount point exists (2 points)
        if os.path.isdir(self.mount_point):
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=True,
                points=2,
                message="Mount point exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Mount point does not exist"
            ))

        # Check 2: fstab entry exists (6 points)
        fstab_has_entry = False
        has_netdev = False

        if validate_file_contains('/etc/fstab', self.mount_point):
            try:
                with open('/etc/fstab', 'r') as f:
                    for line in f:
                        if self.mount_point in line and not line.strip().startswith('#'):
                            fstab_has_entry = True
                            if '_netdev' in line:
                                has_netdev = True
                            break
            except Exception:
                pass

        if fstab_has_entry:
            if has_netdev:
                checks.append(ValidationCheck(
                    name="fstab_entry",
                    passed=True,
                    points=6,
                    message="fstab entry with _netdev option exists"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="fstab_entry",
                    passed=True,
                    points=4,
                    message="fstab entry exists but missing _netdev option"
                ))
                total_points += 4
        else:
            checks.append(ValidationCheck(
                name="fstab_entry",
                passed=False,
                points=0,
                max_points=6,
                message="No fstab entry for this mount"
            ))

        # Check 3: Actually mounted (4 points)
        result = execute_safe(['mount'])
        if result.success and self.mount_point in result.stdout:
            checks.append(ValidationCheck(
                name="is_mounted",
                passed=True,
                points=4,
                message="Mount is active"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="is_mounted",
                passed=False,
                points=0,
                max_points=4,
                message="Not currently mounted (try: mount -a)"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("network_storage")
class ConfigureAutofsTask(BaseTask):
    """Configure autofs for automatic mounting."""

    def __init__(self):
        super().__init__(
            id="autofs_basic_001",
            category="network_storage",
            difficulty="exam",
            points=15
        )
        self.nfs_server = None
        self.nfs_export = None
        self.autofs_mount = None
        self.map_name = None

    def generate(self, **params):
        """Generate autofs configuration task."""
        self.nfs_server = params.get('server', 'nfs.example.com')
        self.nfs_export = params.get('export', '/export/data')
        self.autofs_mount = params.get('mount', '/data')
        self.map_name = params.get('map', 'auto.data')

        self.description = (
            f"Configure autofs for automatic NFS mounting:\n"
            f"  - NFS Server: {self.nfs_server}\n"
            f"  - NFS Export: {self.nfs_export}\n"
            f"  - Auto-mount point: {self.autofs_mount}\n"
            f"  - Mount should appear when accessed\n"
            f"  - Mount should unmount after timeout\n"
            f"  - autofs service must be running"
        )

        self.hints = [
            "Install autofs: dnf install autofs -y",
            f"Add to /etc/auto.master: {self.autofs_mount} /etc/{self.map_name}",
            f"Create /etc/{self.map_name} with: * -rw,sync {self.nfs_server}:{self.nfs_export}/&",
            "Or for direct map: /etc/auto.master: /- /etc/auto.direct",
            "Start service: systemctl enable --now autofs",
            f"Test: cd {self.autofs_mount} && ls"
        ]

        return self

    def validate(self):
        """Validate autofs configuration."""
        checks = []
        total_points = 0

        # Check 1: autofs service running (4 points)
        result = execute_safe(['systemctl', 'is-active', 'autofs'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="autofs_running",
                passed=True,
                points=4,
                message="autofs service is running"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="autofs_running",
                passed=False,
                points=0,
                max_points=4,
                message="autofs service is not running"
            ))

        # Check 2: autofs enabled (2 points)
        result = execute_safe(['systemctl', 'is-enabled', 'autofs'])
        if result.success and 'enabled' in result.stdout:
            checks.append(ValidationCheck(
                name="autofs_enabled",
                passed=True,
                points=2,
                message="autofs service is enabled"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="autofs_enabled",
                passed=False,
                points=0,
                max_points=2,
                message="autofs service is not enabled"
            ))

        # Check 3: auto.master has entry (5 points)
        if validate_file_contains('/etc/auto.master', self.autofs_mount):
            checks.append(ValidationCheck(
                name="master_entry",
                passed=True,
                points=5,
                message="auto.master has mount point entry"
            ))
            total_points += 5
        elif validate_file_contains('/etc/auto.master.d/', self.autofs_mount):
            checks.append(ValidationCheck(
                name="master_entry",
                passed=True,
                points=5,
                message="auto.master.d has mount point entry"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="master_entry",
                passed=False,
                points=0,
                max_points=5,
                message="No autofs master map entry found"
            ))

        # Check 4: Map file exists (4 points)
        map_file = f'/etc/{self.map_name}'
        if validate_file_exists(map_file):
            checks.append(ValidationCheck(
                name="map_file",
                passed=True,
                points=4,
                message=f"Map file {map_file} exists"
            ))
            total_points += 4
        else:
            # Check for any auto.* file
            result = execute_safe(['ls', '/etc/auto.*'])
            if result.success:
                checks.append(ValidationCheck(
                    name="map_file",
                    passed=True,
                    points=2,
                    message="Some autofs map files exist"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="map_file",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="No autofs map file found"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("network_storage")
class AutofsHomeDirectoriesTask(BaseTask):
    """Configure autofs for NFS home directories."""

    def __init__(self):
        super().__init__(
            id="autofs_home_001",
            category="network_storage",
            difficulty="exam",
            points=18
        )
        self.nfs_server = None
        self.home_export = None

    def generate(self, **params):
        """Generate autofs home directories task."""
        self.nfs_server = params.get('server', 'ldap.example.com')
        self.home_export = params.get('export', '/home/guests')

        self.description = (
            f"Configure autofs for user home directories:\n"
            f"  - NFS Server: {self.nfs_server}\n"
            f"  - Export base: {self.home_export}\n"
            f"  - Configure /home/guests to auto-mount user homes\n"
            f"  - Use wildcard mapping so /home/guests/<user> mounts automatically\n"
            f"  - Service must be running and enabled"
        )

        self.hints = [
            "Add to /etc/auto.master: /home/guests /etc/auto.home",
            f"Create /etc/auto.home: * -rw,sync {self.nfs_server}:{self.home_export}/&",
            "The * matches any subdirectory, & substitutes the matched name",
            "Restart autofs: systemctl restart autofs",
            "Test: ls /home/guests/testuser (should trigger mount)"
        ]

        return self

    def validate(self):
        """Validate autofs home directories."""
        checks = []
        total_points = 0

        # Check 1: autofs service running and enabled (4 points)
        result_active = execute_safe(['systemctl', 'is-active', 'autofs'])
        result_enabled = execute_safe(['systemctl', 'is-enabled', 'autofs'])

        if (result_active.success and result_active.stdout.strip() == 'active' and
            result_enabled.success and 'enabled' in result_enabled.stdout):
            checks.append(ValidationCheck(
                name="autofs_service",
                passed=True,
                points=4,
                message="autofs is running and enabled"
            ))
            total_points += 4
        elif result_active.success and result_active.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="autofs_service",
                passed=True,
                points=2,
                message="autofs running but not enabled"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="autofs_service",
                passed=False,
                points=0,
                max_points=4,
                message="autofs service not running"
            ))

        # Check 2: auto.master has /home entry (6 points)
        home_entry = False
        try:
            with open('/etc/auto.master', 'r') as f:
                content = f.read()
                if '/home' in content and 'auto.' in content:
                    home_entry = True
        except Exception:
            pass

        if home_entry:
            checks.append(ValidationCheck(
                name="master_home",
                passed=True,
                points=6,
                message="auto.master has /home configuration"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="master_home",
                passed=False,
                points=0,
                max_points=6,
                message="auto.master missing /home configuration"
            ))

        # Check 3: Map file with wildcard (8 points)
        wildcard_found = False
        for map_file in ['/etc/auto.home', '/etc/auto.guests', '/etc/auto.nfs']:
            if validate_file_exists(map_file):
                try:
                    with open(map_file, 'r') as f:
                        content = f.read()
                        if '*' in content and '&' in content:
                            wildcard_found = True
                            break
                except Exception:
                    pass

        if wildcard_found:
            checks.append(ValidationCheck(
                name="wildcard_map",
                passed=True,
                points=8,
                message="Map file with wildcard substitution found"
            ))
            total_points += 8
        else:
            checks.append(ValidationCheck(
                name="wildcard_map",
                passed=False,
                points=0,
                max_points=8,
                message="No wildcard (*) map for home directories"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("network_storage")
class MountCIFSShareTask(BaseTask):
    """Mount a CIFS/SMB share."""

    def __init__(self):
        super().__init__(
            id="cifs_mount_001",
            category="network_storage",
            difficulty="medium",
            points=10
        )
        self.server = None
        self.share = None
        self.mount_point = None
        self.username = None

    def generate(self, **params):
        """Generate CIFS mount task."""
        self.server = params.get('server', 'fileserver.example.com')
        self.share = params.get('share', 'shared')
        self.mount_point = params.get('mount_point', '/mnt/samba')
        self.username = params.get('username', 'smbuser')

        self.description = (
            f"Mount a CIFS/SMB (Windows) share:\n"
            f"  - Server: {self.server}\n"
            f"  - Share name: {self.share}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Username: {self.username}\n"
            f"  - Create a credentials file for security"
        )

        self.hints = [
            "Install cifs-utils: dnf install cifs-utils -y",
            f"Create mount point: mkdir -p {self.mount_point}",
            f"Create credentials file /root/smb.cred:\nusername={self.username}\npassword=<password>",
            "Secure credentials: chmod 600 /root/smb.cred",
            f"Mount: mount -t cifs //{self.server}/{self.share} {self.mount_point} -o credentials=/root/smb.cred"
        ]

        return self

    def validate(self):
        """Validate CIFS mount."""
        checks = []
        total_points = 0

        import os

        # Check 1: Mount point exists (2 points)
        if os.path.isdir(self.mount_point):
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=True,
                points=2,
                message="Mount point exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="mount_point_exists",
                passed=False,
                points=0,
                max_points=2,
                message="Mount point does not exist"
            ))

        # Check 2: Credentials file exists (3 points)
        cred_file = '/root/smb.cred'
        if validate_file_exists(cred_file):
            # Check permissions
            try:
                mode = os.stat(cred_file).st_mode
                if mode & 0o077 == 0:  # Only owner can read
                    checks.append(ValidationCheck(
                        name="credentials_file",
                        passed=True,
                        points=3,
                        message="Credentials file exists with secure permissions"
                    ))
                    total_points += 3
                else:
                    checks.append(ValidationCheck(
                        name="credentials_file",
                        passed=True,
                        points=2,
                        message="Credentials file exists but permissions too open"
                    ))
                    total_points += 2
            except Exception:
                checks.append(ValidationCheck(
                    name="credentials_file",
                    passed=True,
                    points=2,
                    message="Credentials file exists"
                ))
                total_points += 2
        else:
            checks.append(ValidationCheck(
                name="credentials_file",
                passed=False,
                points=0,
                max_points=3,
                message="Credentials file not found"
            ))

        # Check 3: CIFS is mounted (5 points)
        result = execute_safe(['mount', '-t', 'cifs'])
        if result.success and self.mount_point in result.stdout:
            checks.append(ValidationCheck(
                name="cifs_mounted",
                passed=True,
                points=5,
                message="CIFS share is mounted"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="cifs_mounted",
                passed=False,
                points=0,
                max_points=5,
                message="CIFS share is not mounted"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("network_storage")
class PersistentCIFSMountTask(BaseTask):
    """Configure persistent CIFS mount in fstab."""

    def __init__(self):
        super().__init__(
            id="cifs_fstab_001",
            category="network_storage",
            difficulty="medium",
            points=12
        )
        self.server = None
        self.share = None
        self.mount_point = None

    def generate(self, **params):
        """Generate persistent CIFS mount task."""
        self.server = params.get('server', 'samba.example.com')
        self.share = params.get('share', 'public')
        self.mount_point = params.get('mount_point', '/mnt/public')

        self.description = (
            f"Configure persistent CIFS mount:\n"
            f"  - Server: {self.server}\n"
            f"  - Share: {self.share}\n"
            f"  - Mount point: {self.mount_point}\n"
            f"  - Add to /etc/fstab\n"
            f"  - Use credentials file\n"
            f"  - Use _netdev option"
        )

        self.hints = [
            f"Create mount point: mkdir -p {self.mount_point}",
            "Create /root/cifs.cred with username= and password=",
            f"fstab entry: //{self.server}/{self.share} {self.mount_point} cifs credentials=/root/cifs.cred,_netdev 0 0",
            "Test: mount -a",
            "Verify: mount | grep cifs"
        ]

        return self

    def validate(self):
        """Validate persistent CIFS mount."""
        checks = []
        total_points = 0

        # Check 1: fstab has CIFS entry (6 points)
        if validate_file_contains('/etc/fstab', 'cifs') and validate_file_contains('/etc/fstab', self.mount_point):
            # Check for _netdev
            has_netdev = False
            try:
                with open('/etc/fstab', 'r') as f:
                    for line in f:
                        if self.mount_point in line and 'cifs' in line:
                            if '_netdev' in line:
                                has_netdev = True
                            break
            except Exception:
                pass

            if has_netdev:
                checks.append(ValidationCheck(
                    name="fstab_cifs",
                    passed=True,
                    points=6,
                    message="fstab has CIFS entry with _netdev"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="fstab_cifs",
                    passed=True,
                    points=4,
                    message="fstab has CIFS entry (missing _netdev)"
                ))
                total_points += 4
        else:
            checks.append(ValidationCheck(
                name="fstab_cifs",
                passed=False,
                points=0,
                max_points=6,
                message="No CIFS entry in fstab"
            ))

        # Check 2: Credentials file with right permissions (3 points)
        cred_files = ['/root/cifs.cred', '/root/smb.cred', '/etc/samba/credentials']
        cred_found = False
        for cf in cred_files:
            if validate_file_exists(cf):
                cred_found = True
                break

        if cred_found:
            checks.append(ValidationCheck(
                name="credentials",
                passed=True,
                points=3,
                message="Credentials file exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="credentials",
                passed=False,
                points=0,
                max_points=3,
                message="No credentials file found"
            ))

        # Check 3: Mount point exists (3 points)
        import os
        if os.path.isdir(self.mount_point):
            checks.append(ValidationCheck(
                name="mount_point",
                passed=True,
                points=3,
                message="Mount point exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="mount_point",
                passed=False,
                points=0,
                max_points=3,
                message="Mount point does not exist"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
