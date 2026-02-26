"""
Container management tasks for RHCSA EX200 v10 exam (Podman).
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.system_validators import (
    validate_container_running, validate_container_exists,
    validate_image_exists
)
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains


logger = logging.getLogger(__name__)


@TaskRegistry.register("containers")
class PullContainerImageTask(BaseTask):
    """Pull a container image using podman."""

    def __init__(self):
        super().__init__(
            id="container_pull_001",
            category="containers",
            difficulty="easy",
            points=6
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "Use 'podman pull' to download images",
            "Fully qualified names: registry/namespace/image:tag",
            "List local images: podman images",
        ]
        self.image_name = None

    def generate(self, **params):
        """Generate image pull task."""
        images = [
            'docker.io/library/fedora:latest',
            'docker.io/library/httpd:latest',
            'docker.io/library/nginx:latest',
            'docker.io/library/alpine:latest',
        ]

        self.image_name = params.get('image', random.choice(images))

        self.description = (
            f"Pull a container image:\n"
            f"  - Image: {self.image_name}\n"
            f"  - Use podman to pull the image\n"
            f"  - Verify the image is available locally"
        )

        self.hints = [
            f"Pull image: podman pull {self.image_name}",
            "List images: podman images",
            "Search for images: podman search <name>",
            f"Inspect image: podman inspect {self.image_name}"
        ]

        return self

    def validate(self):
        """Validate image is pulled."""
        checks = []
        total_points = 0

        # Check if image exists locally
        if validate_image_exists(self.image_name):
            checks.append(ValidationCheck(
                name="image_pulled",
                passed=True,
                points=6,
                message=f"Image '{self.image_name}' is available locally"
            ))
            total_points += 6
        else:
            # Try with short name
            short_name = self.image_name.split('/')[-1]
            if validate_image_exists(short_name):
                checks.append(ValidationCheck(
                    name="image_pulled",
                    passed=True,
                    points=6,
                    message=f"Image is available locally"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="image_pulled",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Image '{self.image_name}' not found locally"
                ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class RunContainerTask(BaseTask):
    """Run a container with specific options."""

    def __init__(self):
        super().__init__(
            id="container_run_001",
            category="containers",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "podman run -d runs detached (background)",
            "--name assigns a name to the container",
            "-p maps host:container ports",
            "podman ps shows running containers",
        ]
        self.container_name = None
        self.image_name = None
        self.port_mapping = None

    def generate(self, **params):
        """Generate container run task."""
        self.container_name = params.get('name', f'webapp{random.randint(1,99)}')
        self.image_name = params.get('image', 'httpd:latest')
        self.port_mapping = params.get('port', f'{random.randint(8080,8090)}:80')

        host_port, container_port = self.port_mapping.split(':')

        self.description = (
            f"Run a container:\n"
            f"  - Container name: {self.container_name}\n"
            f"  - Image: {self.image_name}\n"
            f"  - Port mapping: Host {host_port} -> Container {container_port}\n"
            f"  - Run in detached mode (background)\n"
            f"  - Container must be running"
        )

        self.hints = [
            f"Run container: podman run -d --name {self.container_name} -p {self.port_mapping} {self.image_name}",
            "-d runs in detached (background) mode",
            "-p maps ports: host_port:container_port",
            "Check status: podman ps",
            f"View logs: podman logs {self.container_name}"
        ]

        return self

    def validate(self):
        """Validate container is running."""
        checks = []
        total_points = 0

        # Check 1: Container exists (4 points)
        if validate_container_exists(self.container_name):
            checks.append(ValidationCheck(
                name="container_exists",
                passed=True,
                points=4,
                message=f"Container '{self.container_name}' exists"
            ))
            total_points += 4

            # Check 2: Container is running (6 points)
            if validate_container_running(self.container_name):
                checks.append(ValidationCheck(
                    name="container_running",
                    passed=True,
                    points=6,
                    message=f"Container is running"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="container_running",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Container exists but is not running"
                ))
        else:
            checks.append(ValidationCheck(
                name="container_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Container '{self.container_name}' not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class PersistentContainerTask(BaseTask):
    """Configure a container to start automatically via systemd."""

    def __init__(self):
        super().__init__(
            id="container_systemd_001",
            category="containers",
            difficulty="exam",
            points=15
        )
        self.requires_persistence = True
        self.tags = ['v10-new', 'exam-seen']
        self.exam_tips = [
            "podman generate systemd --new --name <container> creates unit file",
            "Place unit file in ~/.config/systemd/user/ for rootless",
            "Or /etc/systemd/system/ for root containers",
            "Enable with systemctl [--user] enable <service>",
            "loginctl enable-linger <user> for rootless containers at boot",
        ]
        self.container_name = None
        self.image_name = None
        self.service_name = None

    def generate(self, **params):
        """Generate persistent container task."""
        self.container_name = params.get('name', f'persistent-app{random.randint(1,99)}')
        self.image_name = params.get('image', 'httpd:latest')
        self.service_name = f'container-{self.container_name}.service'

        self.description = (
            f"Configure a persistent container:\n"
            f"  - Container name: {self.container_name}\n"
            f"  - Image: {self.image_name}\n"
            f"  - Container must start automatically at boot\n"
            f"  - Use systemd to manage the container\n"
            f"  - Generate systemd unit file\n"
            f"  - Enable and start the service"
        )

        self.hints = [
            f"Create and run container first: podman run -d --name {self.container_name} {self.image_name}",
            f"Generate systemd unit: podman generate systemd --new --name {self.container_name} > ~/.config/systemd/user/{self.service_name}",
            f"Or for system: podman generate systemd --new --name {self.container_name} | sudo tee /etc/systemd/system/{self.service_name}",
            "Reload systemd: systemctl --user daemon-reload (or sudo systemctl daemon-reload for system)",
            f"Enable: systemctl --user enable {self.service_name}",
            f"Start: systemctl --user start {self.service_name}",
            "For system service, use sudo and omit --user"
        ]

        return self

    def validate(self):
        """Validate container systemd integration."""
        checks = []
        total_points = 0

        # Check 1: Container exists (5 points)
        if validate_container_exists(self.container_name):
            checks.append(ValidationCheck(
                name="container_exists",
                passed=True,
                points=5,
                message=f"Container exists"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="container_exists",
                passed=False,
                points=0,
                max_points=5,
                message=f"Container '{self.container_name}' not found"
            ))

        # Check 2: Container is running (5 points)
        if validate_container_running(self.container_name):
            checks.append(ValidationCheck(
                name="container_running",
                passed=True,
                points=5,
                message=f"Container is running"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="container_running",
                passed=False,
                points=0,
                max_points=5,
                message=f"Container is not running"
            ))

        # Check 3: Systemd service exists and is enabled (5 points)
        import os
        user_service_path = os.path.expanduser(f'~/.config/systemd/user/{self.service_name}')
        system_service_path = f'/etc/systemd/system/{self.service_name}'

        service_exists = os.path.exists(user_service_path) or os.path.exists(system_service_path)

        if service_exists:
            checks.append(ValidationCheck(
                name="systemd_service",
                passed=True,
                points=5,
                message=f"Systemd service file exists"
            ))
            total_points += 5
        else:
            # Also check for alternative naming patterns
            result = execute_safe(['systemctl', 'list-unit-files', '--no-pager'])
            if result.success and self.container_name in result.stdout:
                checks.append(ValidationCheck(
                    name="systemd_service",
                    passed=True,
                    points=3,
                    message=f"Systemd service exists (partial credit)"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="systemd_service",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Systemd service file not found"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class ContainerVolumeTask(BaseTask):
    """Run a container with a volume mount."""

    def __init__(self):
        super().__init__(
            id="container_volume_001",
            category="containers",
            difficulty="medium",
            points=12
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "-v host_path:container_path mounts a volume",
            "Create host directory first with mkdir -p",
            ":Z or :z for SELinux relabeling",
            ":ro for read-only mount",
        ]
        self.container_name = None
        self.image_name = None
        self.host_path = None
        self.container_path = None

    def generate(self, **params):
        """Generate container volume task."""
        self.container_name = params.get('name', f'data-container{random.randint(1,99)}')
        self.image_name = params.get('image', 'docker.io/library/fedora:latest')
        self.host_path = params.get('host_path', '/opt/containerdata')
        self.container_path = params.get('container_path', '/data')

        self.description = (
            f"Run a container with volume mount:\n"
            f"  - Container name: {self.container_name}\n"
            f"  - Image: {self.image_name}\n"
            f"  - Mount host path: {self.host_path}\n"
            f"  - To container path: {self.container_path}\n"
            f"  - Create host directory if it doesn't exist\n"
            f"  - Run container in background"
        )

        self.hints = [
            f"Create host directory: mkdir -p {self.host_path}",
            f"Run with volume: podman run -d --name {self.container_name} -v {self.host_path}:{self.container_path} {self.image_name} sleep infinity",
            "-v or --volume mounts a host path into the container",
            "Format: -v host_path:container_path",
            "For read-only: -v host_path:container_path:ro",
            f"Verify: podman inspect {self.container_name} | grep -A5 Mounts"
        ]

        return self

    def validate(self):
        """Validate container with volume mount."""
        checks = []
        total_points = 0

        import os

        # Check 1: Host directory exists (3 points)
        if os.path.exists(self.host_path) and os.path.isdir(self.host_path):
            checks.append(ValidationCheck(
                name="host_dir_exists",
                passed=True,
                points=3,
                message=f"Host directory exists"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="host_dir_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Host directory {self.host_path} not found"
            ))

        # Check 2: Container exists (4 points)
        if validate_container_exists(self.container_name):
            checks.append(ValidationCheck(
                name="container_exists",
                passed=True,
                points=4,
                message=f"Container exists"
            ))
            total_points += 4
        else:
            checks.append(ValidationCheck(
                name="container_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Container not found"
            ))

        # Check 3: Container is running (5 points)
        if validate_container_running(self.container_name):
            checks.append(ValidationCheck(
                name="container_running",
                passed=True,
                points=5,
                message=f"Container is running"
            ))
            total_points += 5
        else:
            checks.append(ValidationCheck(
                name="container_running",
                passed=False,
                points=0,
                max_points=5,
                message=f"Container is not running"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class StopRemoveContainerTask(BaseTask):
    """Stop and remove a container."""

    def __init__(self):
        super().__init__(
            id="container_stop_remove_001",
            category="containers",
            difficulty="easy",
            points=6
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "podman stop <name> stops a running container",
            "podman rm <name> removes a stopped container",
            "podman rm -f <name> force removes (stop + remove)",
        ]
        self.container_name = None

    def generate(self, **params):
        self.container_name = params.get('name', f'old-container{random.randint(1,99)}')

        self.description = (
            f"Stop and remove a container:\n"
            f"  - Container name: {self.container_name}\n"
            f"  - Stop the container if running\n"
            f"  - Remove the container completely"
        )

        self.hints = [
            f"Stop container: podman stop {self.container_name}",
            f"Remove container: podman rm {self.container_name}",
            f"Or force remove: podman rm -f {self.container_name}",
            "List containers: podman ps -a",
            f"Verify: podman ps -a | grep {self.container_name} (should be empty)"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: Container should NOT exist
        if not validate_container_exists(self.container_name):
            checks.append(ValidationCheck(
                name="container_removed",
                passed=True,
                points=6,
                message=f"Container successfully removed"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="container_removed",
                passed=False,
                points=0,
                max_points=6,
                message=f"Container '{self.container_name}' still exists"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class ContainerEnvVarsTask(BaseTask):
    """Run a container with environment variables."""

    def __init__(self):
        super().__init__(
            id="container_env_001",
            category="containers",
            difficulty="medium",
            points=10
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "Use -e KEY=VALUE to set environment variables",
            "Multiple -e flags for multiple variables",
            "Verify with: podman exec <name> env",
        ]
        self.container_name = None
        self.image_name = None
        self.env_vars = None

    def generate(self, **params):
        self.container_name = params.get('name', f'app{random.randint(1,99)}')
        self.image_name = params.get('image', 'docker.io/library/httpd:latest')
        self.env_vars = params.get('env', {'APP_ENV': 'production', 'DEBUG': 'false'})

        env_str = ', '.join([f'{k}={v}' for k, v in self.env_vars.items()])

        self.description = (
            f"Run a container with environment variables:\n"
            f"  - Container name: {self.container_name}\n"
            f"  - Image: {self.image_name}\n"
            f"  - Environment variables: {env_str}\n"
            f"  - Run in detached mode"
        )

        env_flags = ' '.join([f'-e {k}={v}' for k, v in self.env_vars.items()])
        self.hints = [
            f"Run with env: podman run -d --name {self.container_name} {env_flags} {self.image_name}",
            "Use -e KEY=VALUE for each environment variable",
            f"Verify: podman inspect {self.container_name} | grep -A5 Env",
            f"Or: podman exec {self.container_name} env"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: Container exists and running (5 points)
        if validate_container_running(self.container_name):
            checks.append(ValidationCheck(
                name="container_running",
                passed=True,
                points=5,
                message=f"Container is running"
            ))
            total_points += 5

            # Check 2: Environment variables set (5 points)
            result = execute_safe(['podman', 'inspect', self.container_name, '--format', '{{.Config.Env}}'])
            if result.success:
                env_found = True
                for key, value in self.env_vars.items():
                    if f'{key}={value}' not in result.stdout:
                        env_found = False
                        break

                if env_found:
                    checks.append(ValidationCheck(
                        name="env_vars_set",
                        passed=True,
                        points=5,
                        message=f"Environment variables are set correctly"
                    ))
                    total_points += 5
                else:
                    checks.append(ValidationCheck(
                        name="env_vars_set",
                        passed=False,
                        points=0,
                        max_points=5,
                        message=f"Environment variables not set correctly"
                    ))
            else:
                checks.append(ValidationCheck(
                    name="env_vars_set",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not inspect container"
                ))
        else:
            checks.append(ValidationCheck(
                name="container_running",
                passed=False,
                points=0,
                max_points=5,
                message=f"Container not running"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("containers")
class InspectContainerTask(BaseTask):
    """Inspect container configuration and extract information."""

    def __init__(self):
        super().__init__(
            id="container_inspect_001",
            category="containers",
            difficulty="medium",
            points=8
        )
        self.tags = ['v10-new']
        self.exam_tips = [
            "podman inspect --format uses Go templates",
            "Common: {{.NetworkSettings.IPAddress}}",
            "Use jq for JSON parsing: podman inspect <name> | jq .",
        ]
        self.container_name = None
        self.output_file = None

    def generate(self, **params):
        self.container_name = params.get('name', 'httpd')
        self.output_file = params.get('output', '/tmp/container_info.txt')

        self.description = (
            f"Inspect a container and save information:\n"
            f"  - Container: {self.container_name}\n"
            f"  - Save the container's IP address to: {self.output_file}\n"
            f"  - Extract the IP using podman inspect"
        )

        self.hints = [
            f"Get IP: podman inspect {self.container_name} --format '{{{{.NetworkSettings.IPAddress}}}}'",
            f"Save to file: podman inspect {self.container_name} --format '{{{{.NetworkSettings.IPAddress}}}}' > {self.output_file}",
            "Use --format with Go templates to extract specific values",
            f"View all info: podman inspect {self.container_name}"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: Output file exists and has content
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=4,
                message=f"Output file exists"
            ))
            total_points += 4

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read().strip()
                    # Check if it looks like an IP address
                    import re
                    if content and re.match(r'\d+\.\d+\.\d+\.\d+', content):
                        checks.append(ValidationCheck(
                            name="has_ip",
                            passed=True,
                            points=4,
                            message=f"File contains IP address: {content}"
                        ))
                        total_points += 4
                    elif content:
                        checks.append(ValidationCheck(
                            name="has_ip",
                            passed=True,
                            points=2,
                            message=f"File has content (partial credit)"
                        ))
                        total_points += 2
                    else:
                        checks.append(ValidationCheck(
                            name="has_ip",
                            passed=False,
                            points=0,
                            max_points=4,
                            message=f"File is empty"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="has_ip",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not read file"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
