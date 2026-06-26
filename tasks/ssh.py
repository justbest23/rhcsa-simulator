"""
SSH tasks for RHCSA exam.
"""

import random
import os
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("ssh")
class GenerateSSHKeyTask(BaseTask):
    """Generate an SSH key pair."""

    def __init__(self):
        super().__init__(
            id="ssh_keygen_001",
            category="ssh",
            difficulty="easy",
            points=8
        )
        self.key_type = None
        self.key_path = None
        self.user = None

    def generate(self, **params):
        """Generate SSH key task."""
        self.key_type = params.get('type', random.choice(['rsa', 'ed25519']))
        self.user = params.get('user', 'root')

        if self.user == 'root':
            self.key_path = f'/root/.ssh/id_{self.key_type}'
        else:
            self.key_path = f'/home/{self.user}/.ssh/id_{self.key_type}'

        self.description = (
            f"Generate an SSH key pair:\n"
            f"  - Key type: {self.key_type}\n"
            f"  - User: {self.user}\n"
            f"  - Key location: {self.key_path}\n"
            f"  - No passphrase (for automation)\n"
            f"  - Correct permissions on .ssh directory"
        )

        self.hints = [
            f"Generate key: ssh-keygen -t {self.key_type} -f {self.key_path} -N ''",
            "The -N '' sets empty passphrase",
            "Verify: ls -la ~/.ssh/",
            ".ssh directory should be 700",
            "Private key should be 600, public key 644"
        ]

        return self

    def validate(self):
        """Validate SSH key generation."""
        checks = []
        total_points = 0

        # Check 1: Private key exists (3 points)
        if validate_file_exists(self.key_path):
            checks.append(ValidationCheck(
                name="private_key",
                passed=True,
                points=3,
                message=f"Private key exists: {self.key_path}"
            ))
            total_points += 3

            # Check permissions (2 points)
            try:
                mode = os.stat(self.key_path).st_mode & 0o777
                if mode == 0o600:
                    checks.append(ValidationCheck(
                        name="private_perms",
                        passed=True,
                        points=2,
                        message="Private key has correct permissions (600)"
                    ))
                    total_points += 2
                else:
                    checks.append(ValidationCheck(
                        name="private_perms",
                        passed=False,
                        points=0,
                        max_points=2,
                        message=f"Private key permissions are {oct(mode)}, should be 600"
                    ))
            except Exception:
                pass
        else:
            checks.append(ValidationCheck(
                name="private_key",
                passed=False,
                points=0,
                max_points=3,
                message="Private key not found"
            ))

        # Check 2: Public key exists (3 points)
        pub_key = f"{self.key_path}.pub"
        if validate_file_exists(pub_key):
            checks.append(ValidationCheck(
                name="public_key",
                passed=True,
                points=3,
                message="Public key exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="public_key",
                passed=False,
                points=0,
                max_points=3,
                message="Public key not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SSHAuthorizedKeysTask(BaseTask):
    """Configure SSH authorized_keys for key-based auth."""

    def __init__(self):
        super().__init__(
            id="ssh_authkeys_001",
            category="ssh",
            difficulty="medium",
            points=10
        )
        self.user = None
        self.source_key = None

    def generate(self, **params):
        """Generate authorized_keys task."""
        self.user = params.get('user', 'student')
        self.source_key = params.get('source', '/root/.ssh/id_rsa.pub')

        self.description = (
            f"Configure SSH key-based authentication:\n"
            f"  - Target user: {self.user}\n"
            f"  - Add public key from: {self.source_key}\n"
            f"  - Add to user's authorized_keys file\n"
            f"  - Ensure correct permissions"
        )

        auth_keys = f'/home/{self.user}/.ssh/authorized_keys'

        self.hints = [
            f"Create .ssh dir: mkdir -p /home/{self.user}/.ssh",
            f"Copy key: cat {self.source_key} >> {auth_keys}",
            f"Or use: ssh-copy-id -i {self.source_key} {self.user}@localhost",
            f"Fix permissions: chmod 700 /home/{self.user}/.ssh",
            f"Fix file: chmod 600 {auth_keys}",
            f"Fix ownership: chown -R {self.user}:{self.user} /home/{self.user}/.ssh"
        ]

        return self

    def validate(self):
        """Validate authorized_keys configuration."""
        checks = []
        total_points = 0

        ssh_dir = f'/home/{self.user}/.ssh'
        auth_keys = f'{ssh_dir}/authorized_keys'

        # Check 1: .ssh directory exists (2 points)
        if os.path.isdir(ssh_dir):
            checks.append(ValidationCheck(
                name="ssh_dir",
                passed=True,
                points=2,
                message=f".ssh directory exists for {self.user}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="ssh_dir",
                passed=False,
                points=0,
                max_points=2,
                message=f".ssh directory not found for {self.user}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: authorized_keys exists (4 points)
        if validate_file_exists(auth_keys):
            checks.append(ValidationCheck(
                name="auth_keys_exists",
                passed=True,
                points=4,
                message="authorized_keys file exists"
            ))
            total_points += 4

            # Check if it has content
            try:
                with open(auth_keys, 'r') as f:
                    content = f.read()
                    if 'ssh-' in content:
                        checks.append(ValidationCheck(
                            name="has_key",
                            passed=True,
                            points=2,
                            message="File contains SSH key(s)"
                        ))
                        total_points += 2
            except Exception:
                pass
        else:
            checks.append(ValidationCheck(
                name="auth_keys_exists",
                passed=False,
                points=0,
                max_points=4,
                message="authorized_keys file not found"
            ))

        # Check 3: Permissions (2 points)
        try:
            dir_mode = os.stat(ssh_dir).st_mode & 0o777
            if dir_mode == 0o700:
                checks.append(ValidationCheck(
                    name="perms",
                    passed=True,
                    points=2,
                    message="Correct permissions on .ssh"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="perms",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f".ssh permissions are {oct(dir_mode)}, should be 700"
                ))
        except Exception:
            pass

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SSHClientConfigTask(BaseTask):
    """Create SSH client configuration file."""

    def __init__(self):
        super().__init__(
            id="ssh_config_001",
            category="ssh",
            difficulty="medium",
            points=8
        )
        self.host_alias = None
        self.hostname = None
        self.user = None

    def generate(self, **params):
        """Generate SSH config task."""
        self.host_alias = params.get('alias', 'webserver')
        self.hostname = params.get('hostname', 'server1.example.com')
        self.user = params.get('user', 'admin')

        self.description = (
            f"Create an SSH client configuration:\n"
            f"  - Config file: ~/.ssh/config\n"
            f"  - Host alias: {self.host_alias}\n"
            f"  - Hostname: {self.hostname}\n"
            f"  - User: {self.user}\n"
            f"  - After config, 'ssh {self.host_alias}' should work"
        )

        self.hints = [
            "Create/edit ~/.ssh/config",
            f"Add:\nHost {self.host_alias}\n    HostName {self.hostname}\n    User {self.user}",
            "Optional: add IdentityFile ~/.ssh/id_rsa",
            "Set permissions: chmod 600 ~/.ssh/config",
            f"Test: ssh {self.host_alias} (or ssh -v {self.host_alias} for debug)"
        ]

        return self

    def validate(self):
        """Validate SSH client config."""
        checks = []
        total_points = 0

        config_file = os.path.expanduser('~/.ssh/config')

        # Check 1: Config file exists (3 points)
        if validate_file_exists(config_file):
            checks.append(ValidationCheck(
                name="config_exists",
                passed=True,
                points=3,
                message="SSH config file exists"
            ))
            total_points += 3

            # Check 2: Has host entry (3 points)
            if validate_file_contains(config_file, f'Host {self.host_alias}', case_sensitive=False):
                checks.append(ValidationCheck(
                    name="host_entry",
                    passed=True,
                    points=3,
                    message=f"Host {self.host_alias} configured"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="host_entry",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Host {self.host_alias} not found in config"
                ))

            # Check 3: Has hostname and user (2 points)
            has_hostname = validate_file_contains(config_file, 'HostName', case_sensitive=False)
            has_user = validate_file_contains(config_file, 'User', case_sensitive=False)
            if has_hostname and has_user:
                checks.append(ValidationCheck(
                    name="config_complete",
                    passed=True,
                    points=2,
                    message="HostName and User configured"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="config_complete",
                    passed=False,
                    points=0,
                    max_points=2,
                    message="Missing HostName or User"
                ))
        else:
            checks.append(ValidationCheck(
                name="config_exists",
                passed=False,
                points=0,
                max_points=3,
                message="SSH config file not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SecureSSHDTask(BaseTask):
    """Secure SSH server configuration."""

    def __init__(self):
        super().__init__(
            id="ssh_sshd_001",
            category="ssh",
            difficulty="medium",
            points=12
        )
        self.disable_root = None
        self.disable_password = None

    def generate(self, **params):
        """Generate SSHD security task."""
        self.disable_root = params.get('disable_root', True)
        self.disable_password = params.get('disable_password', False)

        requirements = []
        if self.disable_root:
            requirements.append("- Disable root login via SSH")
        if self.disable_password:
            requirements.append("- Disable password authentication")
        requirements.append("- Restart sshd to apply changes")

        self.description = (
            f"Secure SSH server:\n"
            + "\n".join(requirements) +
            f"\n  - Edit /etc/ssh/sshd_config\n"
            f"  - Changes must be persistent"
        )

        self.hints = [
            "Edit /etc/ssh/sshd_config",
            "PermitRootLogin no (disable root login)",
            "PasswordAuthentication no (disable passwords)",
            "Restart: systemctl restart sshd",
            "Test BEFORE disconnecting: ssh -o PreferredAuthentications=password"
        ]

        return self

    def validate(self):
        """Validate SSH server security."""
        checks = []
        total_points = 0

        sshd_config = '/etc/ssh/sshd_config'

        # Check 1: Root login disabled (6 points if required)
        if self.disable_root:
            result = execute_safe(['grep', '-i', '^PermitRootLogin', sshd_config])
            if result.success and 'no' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name="root_disabled",
                    passed=True,
                    points=6,
                    message="Root login is disabled"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="root_disabled",
                    passed=False,
                    points=0,
                    max_points=6,
                    message="Root login is not disabled"
                ))
        else:
            total_points += 6  # Skip this check

        # Check 2: Password auth disabled (4 points if required)
        if self.disable_password:
            result = execute_safe(['grep', '-i', '^PasswordAuthentication', sshd_config])
            if result.success and 'no' in result.stdout.lower():
                checks.append(ValidationCheck(
                    name="password_disabled",
                    passed=True,
                    points=4,
                    message="Password authentication disabled"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="password_disabled",
                    passed=False,
                    points=0,
                    max_points=4,
                    message="Password authentication still enabled"
                ))
        else:
            total_points += 4  # Skip this check

        # Check 3: SSHD running (2 points)
        result = execute_safe(['systemctl', 'is-active', 'sshd'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck(
                name="sshd_running",
                passed=True,
                points=2,
                message="SSHD service is running"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="sshd_running",
                passed=False,
                points=0,
                max_points=2,
                message="SSHD service is not running"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SecureFileTransferTask(BaseTask):
    """Transfer a file securely using scp — push direction (EX200 v10 objective)."""

    def __init__(self):
        super().__init__(
            id="ssh_scp_001",
            category="ssh",
            difficulty="easy",
            points=8
        )
        self.src_file = None
        self.dest_path = None
        self.exam_tips = [
            "scp syntax: scp [src] [user@host:dest] for push, scp [user@host:src] [dest] for pull",
            "scp -r copies entire directories recursively",
            "sftp provides an interactive file-browser session over SSH",
            "rsync -avz is preferred for large or incremental transfers",
            "scp and sftp both use SSH for transport — same auth as ssh",
        ]

    def generate(self, **params):
        src_choices = ['/etc/hostname', '/etc/os-release', '/etc/redhat-release']
        self.src_file = params.get('src', random.choice(src_choices))
        self.dest_path = params.get('dest', f'/tmp/scp_transfer_{random.randint(100, 999)}')

        self.description = (
            f"Securely transfer a file using scp (push direction):\n\n"
            f"  1. Copy '{self.src_file}' to '{self.dest_path}' on localhost using scp\n"
            f"  2. Verify the destination file exists and is not empty\n\n"
            f"scp uses SSH for secure transport. Knowing scp is required for RHCSA."
        )

        self.hints = [
            "Ensure sshd is running before attempting the transfer",
            "scp syntax: scp <source> <user>@<host>:<destination>",
            f"Verify: ls -l {self.dest_path}",
        ]

        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        if os.path.exists(self.dest_path):
            checks.append(ValidationCheck("file_transferred", True, 5, f"File exists at {self.dest_path}"))
            total_points += 5
        else:
            checks.append(ValidationCheck("file_transferred", False, 0, f"No file found at {self.dest_path}", max_points=5))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        try:
            if os.path.getsize(self.dest_path) > 0:
                checks.append(ValidationCheck("file_not_empty", True, 3, "File has content"))
                total_points += 3
            else:
                checks.append(ValidationCheck("file_not_empty", False, 0, "File is empty", max_points=3))
        except Exception as e:
            checks.append(ValidationCheck("file_not_empty", False, 0, f"Could not stat: {e}", max_points=3))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SCPDirectoryTransferTask(BaseTask):
    """Transfer a directory recursively with scp -r (EX200 v10 objective)."""

    def __init__(self):
        super().__init__(
            id="ssh_scp_002",
            category="ssh",
            difficulty="medium",
            points=10
        )
        self.src_dir = None
        self.dest_dir = None
        self.exam_tips = [
            "scp -r copies an entire directory tree recursively",
            "rsync -avz is preferred for large directories — shows progress and handles errors",
            "Trailing slash on source changes what gets copied: /dir/ vs /dir",
        ]

    def generate(self, **params):
        tag = random.randint(100, 999)
        self.src_dir = params.get('src', f'/tmp/scp_src_{tag}')
        self.dest_dir = params.get('dest', f'/tmp/scp_dst_{tag}')

        self.description = (
            f"Transfer a directory securely using scp:\n\n"
            f"  1. Create a source directory '{self.src_dir}' with at least 2 files\n"
            f"     mkdir -p {self.src_dir} && echo data1 > {self.src_dir}/file1.txt && echo data2 > {self.src_dir}/file2.txt\n"
            f"  2. Copy the directory to '{self.dest_dir}' on localhost using scp -r\n"
            f"     scp -r {self.src_dir} root@localhost:{self.dest_dir}\n"
            f"  3. Verify the destination directory exists with the files inside"
        )

        self.hints = [
            f"Create: mkdir -p {self.src_dir} && touch {self.src_dir}/{{file1,file2}}.txt",
            f"Transfer: scp -r {self.src_dir} root@localhost:{self.dest_dir}",
            f"Verify: ls -l {self.dest_dir}",
            "Ensure sshd is running: systemctl is-active sshd",
        ]

        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        if os.path.isdir(self.dest_dir):
            checks.append(ValidationCheck("dir_exists", True, 5, f"Directory exists at {self.dest_dir}"))
            total_points += 5
        else:
            checks.append(ValidationCheck("dir_exists", False, 0, f"No directory at {self.dest_dir}", max_points=5))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        try:
            items = os.listdir(self.dest_dir)
            if items:
                checks.append(ValidationCheck("dir_content", True, 5, f"Directory contains {len(items)} item(s)"))
                total_points += 5
            else:
                checks.append(ValidationCheck("dir_content", False, 0, "Destination directory is empty", max_points=5))
        except Exception as e:
            checks.append(ValidationCheck("dir_content", False, 0, f"Could not list dir: {e}", max_points=5))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("ssh")
class SCPFromRemoteTask(BaseTask):
    """Pull a file from a remote host using scp (EX200 v10 objective)."""

    def __init__(self):
        super().__init__(
            id="ssh_scp_003",
            category="ssh",
            difficulty="medium",
            points=10
        )
        self.remote_src = None
        self.local_dest = None
        self.exam_tips = [
            "scp pulls from remote: scp user@host:/remote/path /local/path",
            "Know both push (local → remote) and pull (remote → local) directions",
            "sftp: connect then use 'get /remote/path [local_path]' to retrieve files",
        ]

    def generate(self, **params):
        tag = random.randint(100, 999)
        self.remote_src = params.get('remote_src', random.choice(['/etc/hostname', '/etc/os-release']))
        self.local_dest = params.get('local_dest', f'/tmp/remote_pull_{tag}')

        self.description = (
            f"Retrieve a file from a remote system using scp (pull direction):\n\n"
            f"  1. Pull '{self.remote_src}' FROM localhost TO '{self.local_dest}'\n"
            f"     scp root@localhost:{self.remote_src} {self.local_dest}\n"
            f"  2. Verify the file was retrieved and has content\n\n"
            f"On the exam you may need to retrieve files or logs from a remote host.\n"
            f"This tests the pull direction of scp."
        )

        self.hints = [
            "Ensure sshd is running: systemctl is-active sshd",
            f"Pull the file: scp root@localhost:{self.remote_src} {self.local_dest}",
            f"Verify: cat {self.local_dest}",
            f"sftp alternative: sftp root@localhost then: get {self.remote_src} {self.local_dest}",
        ]

        return self

    def validate(self):
        import os
        checks = []
        total_points = 0

        if os.path.exists(self.local_dest):
            checks.append(ValidationCheck("file_retrieved", True, 6, f"File retrieved to {self.local_dest}"))
            total_points += 6
        else:
            checks.append(ValidationCheck("file_retrieved", False, 0, f"No file at {self.local_dest}", max_points=6))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        try:
            if os.path.getsize(self.local_dest) > 0:
                checks.append(ValidationCheck("file_valid", True, 4, "Retrieved file has content"))
                total_points += 4
            else:
                checks.append(ValidationCheck("file_valid", False, 0, "Retrieved file is empty", max_points=4))
        except Exception as e:
            checks.append(ValidationCheck("file_valid", False, 0, f"Could not stat: {e}", max_points=4))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
