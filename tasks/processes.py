"""
Process management tasks for RHCSA exam.
"""

import random
import re
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists


logger = logging.getLogger(__name__)


@TaskRegistry.register("processes")
class KillProcessTask(BaseTask):
    """Kill a process by name or PID."""

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="proc_kill_001",
            category="processes",
            difficulty="easy",
            points=8
        )
        self.process_name = None
        self.signal = None
        self._fake_dir = None

    def generate(self, **params):
        """Generate process kill task."""
        processes = ['httpd', 'nginx', 'sleep', 'dd']
        self.process_name = params.get('process', random.choice(processes))
        self.signal = params.get('signal', 'SIGTERM')

        self.description = (
            f"Terminate process:\n"
            f"  - Process name: {self.process_name}\n"
            f"  - Signal: {self.signal}\n"
            f"  - Kill ALL instances of this process\n"
            f"  - Verify the process is no longer running"
        )

        self.hints = [
            f"Kill by name: pkill {self.process_name}",
            f"Or: killall {self.process_name}",
            f"With specific signal: pkill -{self.signal} {self.process_name}",
            f"Find PID first: pgrep {self.process_name} or ps aux | grep {self.process_name}",
            "Then kill: kill <PID>",
            f"Verify: pgrep {self.process_name} (should return nothing)"
        ]

        return self

    def inject_fault(self):
        """Start real processes the candidate must kill.

        We copy `sleep` to a file named after the target process so that
        `pgrep -x <name>` (used by validate) matches its comm, then launch a
        couple of instances. Without this the task is trivially "passed" because
        nothing of that name is running.
        """
        import subprocess as _sp
        import os, shutil, tempfile
        src = shutil.which('sleep') or '/usr/bin/sleep'
        d = tempfile.mkdtemp(prefix='rhcsa_proc_')
        fake = os.path.join(d, self.process_name)
        try:
            shutil.copy(src, fake)
            os.chmod(fake, 0o755)
            for _ in range(2):
                _sp.Popen([fake, '600'])
        except Exception as e:
            shutil.rmtree(d, ignore_errors=True)
            return False, f"Could not start '{self.process_name}': {e}"
        self._fake_dir = d
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'process': self.process_name, 'dir': d})
        return True, f"Started 2 '{self.process_name}' process(es)"

    def restore_fault(self):
        import subprocess as _sp
        import shutil
        from tasks.troubleshooting import load_fault_state, clear_fault_state
        state = load_fault_state(self.id)
        info = state.get('restore_info', {}) if state else {}
        name = info.get('process', self.process_name)
        d = info.get('dir', self._fake_dir)
        _sp.run(['pkill', '-x', name], capture_output=True)
        if d:
            shutil.rmtree(d, ignore_errors=True)
        clear_fault_state(self.id)
        return True, f"Killed '{name}' processes and cleaned up"

    def validate(self):
        """Validate process is killed."""
        checks = []
        total_points = 0

        # Check: Process is not running
        result = execute_safe(['pgrep', '-x', self.process_name])

        if not result.success or not result.stdout.strip():
            checks.append(ValidationCheck(
                name="process_killed",
                passed=True,
                points=8,
                message=f"Process '{self.process_name}' successfully terminated"
            ))
            total_points += 8
        else:
            pids = result.stdout.strip().split('\n')
            checks.append(ValidationCheck(
                name="process_killed",
                passed=False,
                points=0,
                max_points=8,
                message=f"Process '{self.process_name}' still running (PIDs: {', '.join(pids)})"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class AdjustProcessPriorityTask(BaseTask):
    """Adjust process priority using nice/renice."""

    def __init__(self):
        super().__init__(
            id="proc_priority_001",
            category="processes",
            difficulty="medium",
            points=10
        )
        self.process_name = None
        self.nice_value = None

    def generate(self, **params):
        """Generate process priority task."""
        self.process_name = params.get('process', 'sleep')
        self.nice_value = params.get('nice', random.choice([-10, -5, 0, 5, 10, 19]))

        self.description = (
            f"Adjust process priority:\n"
            f"  - Process: {self.process_name}\n"
            f"  - Nice value: {self.nice_value}\n"
            f"  - Change priority of ALL running instances\n"
            f"  - Use renice command"
        )

        self.hints = [
            f"Find PIDs: pgrep {self.process_name}",
            f"Renice: renice {self.nice_value} -p <PID>",
            f"For all instances: renice {self.nice_value} $(pgrep {self.process_name})",
            f"Verify: ps -eo pid,ni,comm | grep {self.process_name}",
            "Negative nice values require root (higher priority)",
            "Positive nice values mean lower priority"
        ]

        return self

    def validate(self):
        """Validate process priority."""
        checks = []
        total_points = 0

        # Get PIDs of the process
        result = execute_safe(['pgrep', '-x', self.process_name])

        if result.success and result.stdout.strip():
            pids = result.stdout.strip().split('\n')

            # Check nice value of each PID
            all_correct = True
            for pid in pids:
                ps_result = execute_safe(['ps', '-o', 'ni=', '-p', pid])
                if ps_result.success:
                    try:
                        current_nice = int(ps_result.stdout.strip())
                        if current_nice != self.nice_value:
                            all_correct = False
                            break
                    except ValueError:
                        all_correct = False
                        break
                else:
                    all_correct = False
                    break

            if all_correct:
                checks.append(ValidationCheck(
                    name="priority_adjusted",
                    passed=True,
                    points=10,
                    message=f"All '{self.process_name}' processes have nice value {self.nice_value}"
                ))
                total_points += 10
            else:
                checks.append(ValidationCheck(
                    name="priority_adjusted",
                    passed=False,
                    points=0,
                    max_points=10,
                    message=f"Nice value not correctly set for all '{self.process_name}' processes"
                ))
        else:
            checks.append(ValidationCheck(
                name="process_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"Process '{self.process_name}' not found"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class StartProcessWithPriorityTask(BaseTask):
    """Start a process with specific nice value."""

    def __init__(self):
        super().__init__(
            id="proc_nice_start_001",
            category="processes",
            difficulty="medium",
            points=10
        )
        self.command = None
        self.nice_value = None
        self.process_name = None

    def generate(self, **params):
        """Generate start with priority task."""
        commands = [
            ('sleep 3600', 'sleep'),
            ('dd if=/dev/zero of=/dev/null', 'dd'),
        ]

        cmd_choice = params.get('command', random.choice(commands))
        if isinstance(cmd_choice, tuple):
            self.command, self.process_name = cmd_choice
        else:
            self.command = cmd_choice
            self.process_name = cmd_choice.split()[0]

        self.nice_value = params.get('nice', random.choice([5, 10, 15, 19]))

        self.description = (
            f"Start a process with specific priority:\n"
            f"  - Command: {self.command}\n"
            f"  - Nice value: {self.nice_value}\n"
            f"  - Process must run in background\n"
            f"  - Verify it's running with correct priority"
        )

        self.hints = [
            f"Start with nice: nice -n {self.nice_value} {self.command} &",
            f"Verify: ps -eo pid,ni,comm | grep {self.process_name}",
            f"Check: pgrep {self.process_name} should show the PID",
            "The & at the end runs it in background"
        ]

        return self

    def validate(self):
        """Validate process started with priority."""
        checks = []
        total_points = 0

        # Check if process is running (5 points)
        result = execute_safe(['pgrep', '-x', self.process_name])

        if result.success and result.stdout.strip():
            checks.append(ValidationCheck(
                name="process_running",
                passed=True,
                points=5,
                message=f"Process '{self.process_name}' is running"
            ))
            total_points += 5

            # Check nice value (5 points)
            pids = result.stdout.strip().split('\n')
            # Check the first PID's nice value
            ps_result = execute_safe(['ps', '-o', 'ni=', '-p', pids[0]])

            if ps_result.success:
                try:
                    current_nice = int(ps_result.stdout.strip())
                    if current_nice == self.nice_value:
                        checks.append(ValidationCheck(
                            name="correct_priority",
                            passed=True,
                            points=5,
                            message=f"Process has correct nice value: {self.nice_value}"
                        ))
                        total_points += 5
                    else:
                        checks.append(ValidationCheck(
                            name="correct_priority",
                            passed=False,
                            points=0,
                            max_points=5,
                            message=f"Nice value is {current_nice}, expected {self.nice_value}"
                        ))
                except ValueError:
                    checks.append(ValidationCheck(
                        name="correct_priority",
                        passed=False,
                        points=0,
                        max_points=5,
                        message=f"Could not determine nice value"
                    ))
        else:
            checks.append(ValidationCheck(
                name="process_running",
                passed=False,
                points=0,
                max_points=5,
                message=f"Process '{self.process_name}' is not running"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class FindProcessByUserTask(BaseTask):
    """Find and manage processes owned by a specific user."""

    has_fault_injection = True

    def __init__(self):
        super().__init__(
            id="proc_find_user_001",
            category="processes",
            difficulty="exam",
            points=12
        )
        self.username = None
        self.action = None
        self._created_user = False
        self.output_file = None

    def generate(self, **params):
        """Generate find process by user task."""
        # Use a dedicated practice account, never a real service user. 'apache'
        # is the httpd runtime user: if httpd is running (several fault tasks
        # start it), its workers are owned by apache and the master respawns any
        # the candidate kills, making the kill action impossible to complete.
        self.username = params.get('username', 'pracproc')
        actions = ['list', 'count', 'kill']
        self.action = params.get('action', random.choice(actions))

        # list/count are read-only: without a required artifact there is
        # nothing to validate, so both must be saved to a file the candidate
        # names.
        if self.action in ('list', 'count'):
            self.output_file = params.get(
                'output', f'/tmp/{self.username}-{self.action}-{random.randint(100, 999)}.txt'
            )

        if self.action == 'list':
            task_desc = (
                f"List all processes owned by user '{self.username}'\n"
                f"  - Save the output to: {self.output_file}"
            )
        elif self.action == 'count':
            task_desc = (
                f"Count processes owned by user '{self.username}'\n"
                f"  - Save the count to: {self.output_file}"
            )
        else:  # kill
            task_desc = f"Terminate all processes owned by user '{self.username}'"

        self.description = (
            f"Process management by user:\n"
            f"  - Task: {task_desc}\n"
            f"  - User: {self.username}\n"
            f"  - Use appropriate ps/pkill commands"
        )

        if self.action == 'list':
            self.hints = [
                f"List user processes: ps -u {self.username}",
                f"Save to file: ps -u {self.username} > {self.output_file}",
                f"Find PIDs: pgrep -u {self.username}",
            ]
        elif self.action == 'count':
            self.hints = [
                f"Count user processes: ps -u {self.username} --no-headers | wc -l",
                f"Save to file: ps -u {self.username} --no-headers | wc -l > {self.output_file}",
                f"Or: pgrep -u {self.username} | wc -l > {self.output_file}",
            ]
        else:  # kill
            self.hints = [
                f"Kill user processes: pkill -u {self.username}",
                f"Or: killall -u {self.username}",
                f"Find PIDs: pgrep -u {self.username}",
                f"Verify: ps -u {self.username} (should show nothing if killed)"
            ]

        return self

    def inject_fault(self):
        import subprocess as _sp
        # Provision for every action: list/count need processes to see, kill needs
        # processes to kill. Only delete the user later if we actually create it
        # here (apache may pre-exist as a real httpd account — never remove that).
        existed = _sp.run(['id', self.username], capture_output=True).returncode == 0
        self._created_user = not existed
        if not existed:
            _sp.run(['useradd', '-r', '-s', '/sbin/nologin', '-M', self.username],
                    capture_output=True)
        # Start several background sleep processes as that user
        for _ in range(3):
            _sp.Popen(['runuser', '-u', self.username, '--', 'sleep', '600'])
        from tasks.troubleshooting import save_fault_state
        save_fault_state(self.id, {'username': self.username,
                                   'created_user': self._created_user})
        return True, f"Started 3 background processes as '{self.username}'"

    def restore_fault(self):
        import subprocess as _sp
        import time
        from tasks.troubleshooting import load_fault_state, clear_fault_state
        state = load_fault_state(self.id)
        info = state.get('restore_info', {}) if state else {}
        created = info.get('created_user', getattr(self, '_created_user', False))
        _sp.run(['pkill', '-u', self.username], capture_output=True)
        msg = f"Killed remaining '{self.username}' processes"
        if created:
            time.sleep(0.5)  # let pkill reap processes so userdel won't fail on "in use"
            _sp.run(['userdel', '-rf', self.username], capture_output=True)
            msg += " and removed the user it created"
        clear_fault_state(self.id)
        return True, msg

    def validate(self):
        """Validate process management by user."""
        checks = []
        total_points = 0

        # For kill action, verify no processes remain
        if self.action == 'kill':
            result = execute_safe(['pgrep', '-u', self.username])

            if not result.success or not result.stdout.strip():
                checks.append(ValidationCheck(
                    name="user_processes_killed",
                    passed=True,
                    points=12,
                    message=f"All processes for user '{self.username}' terminated"
                ))
                total_points += 12
            else:
                pids = result.stdout.strip().split('\n')
                checks.append(ValidationCheck(
                    name="user_processes_killed",
                    passed=False,
                    points=0,
                    max_points=12,
                    message=f"User '{self.username}' still has {len(pids)} process(es) running"
                ))
        elif self.action == 'list':
            if validate_file_exists(self.output_file):
                checks.append(ValidationCheck(
                    name="output_file_exists",
                    passed=True,
                    points=5,
                    message=f"Output file exists at {self.output_file}"
                ))
                total_points += 5

                try:
                    with open(self.output_file, 'r') as f:
                        content = f.read().strip()
                    if content:
                        checks.append(ValidationCheck(
                            name="output_has_content",
                            passed=True,
                            points=7,
                            message="Output file contains the process listing"
                        ))
                        total_points += 7
                    else:
                        checks.append(ValidationCheck(
                            name="output_has_content",
                            passed=False,
                            points=0,
                            max_points=7,
                            message="Output file is empty"
                        ))
                except Exception as e:
                    checks.append(ValidationCheck(
                        name="output_has_content",
                        passed=False,
                        points=0,
                        max_points=7,
                        message=f"Could not read output file: {e}"
                    ))
            else:
                checks.append(ValidationCheck(
                    name="output_file_exists",
                    passed=False,
                    points=0,
                    max_points=12,
                    message=f"Output file not found: {self.output_file}"
                ))
        else:  # count
            if validate_file_exists(self.output_file):
                checks.append(ValidationCheck(
                    name="output_file_exists",
                    passed=True,
                    points=5,
                    message=f"Output file exists at {self.output_file}"
                ))
                total_points += 5

                pgrep_result = execute_safe(['pgrep', '-u', self.username])
                actual_count = (
                    len(pgrep_result.stdout.strip().split('\n'))
                    if pgrep_result.success and pgrep_result.stdout.strip() else 0
                )

                try:
                    with open(self.output_file, 'r') as f:
                        content = f.read().strip()
                    match = re.search(r'\d+', content)
                    if match and int(match.group()) == actual_count:
                        checks.append(ValidationCheck(
                            name="correct_count",
                            passed=True,
                            points=7,
                            message=f"Correct count ({actual_count}) recorded"
                        ))
                        total_points += 7
                    else:
                        found = match.group() if match else "no number"
                        checks.append(ValidationCheck(
                            name="correct_count",
                            passed=False,
                            points=0,
                            max_points=7,
                            message=f"Expected count {actual_count}, found '{found}' in file"
                        ))
                except Exception as e:
                    checks.append(ValidationCheck(
                        name="correct_count",
                        passed=False,
                        points=0,
                        max_points=7,
                        message=f"Could not read output file: {e}"
                    ))
            else:
                checks.append(ValidationCheck(
                    name="output_file_exists",
                    passed=False,
                    points=0,
                    max_points=12,
                    message=f"Output file not found: {self.output_file}"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class BackgroundProcessTask(BaseTask):
    """Run a process in the background."""

    def __init__(self):
        super().__init__(
            id="process_background_001",
            category="processes",
            difficulty="medium",
            points=8
        )
        self.command = None
        self.output_file = None

    def generate(self, **params):
        self.command = params.get('command', 'sleep 300')
        self.output_file = params.get('output', '/tmp/bg_process.pid')

        self.description = (
            f"Run a process in the background:\n"
            f"  - Command: {self.command}\n"
            f"  - Run in background (don't block terminal)\n"
            f"  - Save the process ID to: {self.output_file}\n"
            f"  - Process should continue running"
        )

        self.hints = [
            f"Run in background: {self.command} &",
            f"Get last background PID: echo $! > {self.output_file}",
            f"Or: nohup {self.command} & echo $! > {self.output_file}",
            "List background jobs: jobs",
            "Verify process: ps -p $(cat /tmp/bg_process.pid)"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: PID file exists (3 points)
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="pid_file_exists",
                passed=True,
                points=3,
                message=f"PID file exists"
            ))
            total_points += 3

            # Check 2: PID is valid and process running (5 points)
            try:
                with open(self.output_file, 'r') as f:
                    pid = f.read().strip()
                    if pid.isdigit():
                        result = execute_safe(['ps', '-p', pid])
                        if result.success and pid in result.stdout:
                            checks.append(ValidationCheck(
                                name="process_running",
                                passed=True,
                                points=5,
                                message=f"Process {pid} is running"
                            ))
                            total_points += 5
                        else:
                            checks.append(ValidationCheck(
                                name="process_running",
                                passed=False,
                                points=0,
                                max_points=5,
                                message=f"Process {pid} is not running"
                            ))
                    else:
                        checks.append(ValidationCheck(
                            name="process_running",
                            passed=False,
                            points=0,
                            max_points=5,
                            message=f"Invalid PID in file"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="process_running",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not read PID file"
                ))
        else:
            checks.append(ValidationCheck(
                name="pid_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"PID file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class FindResourceHogTask(BaseTask):
    """Find processes using the most resources."""

    def __init__(self):
        super().__init__(
            id="process_resource_001",
            category="processes",
            difficulty="medium",
            points=8
        )
        self.resource_type = None
        self.output_file = None

    def generate(self, **params):
        self.resource_type = params.get('resource', random.choice(['cpu', 'memory']))
        self.output_file = params.get('output', f'/tmp/top_{self.resource_type}.txt')

        if self.resource_type == 'cpu':
            sort_key = 'CPU usage'
            ps_sort = '-pcpu'
        else:
            sort_key = 'memory usage'
            ps_sort = '-pmem'

        self.description = (
            f"Find top processes by {self.resource_type}:\n"
            f"  - List top 10 processes by {sort_key}\n"
            f"  - Save the output to: {self.output_file}\n"
            f"  - Include PID, user, and command"
        )

        self.hints = [
            f"Using ps: ps aux --sort={ps_sort} | head -11 > {self.output_file}",
            "Or use top in batch mode: top -b -n 1 | head -20",
            f"ps columns: -o pid,user,%cpu,%mem,comm",
            "Sort by CPU: --sort=-%cpu, by memory: --sort=-%mem"
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
                    content = f.read()
                    lines = content.strip().split('\n')
                    if len(lines) >= 5:  # At least header + some processes
                        checks.append(ValidationCheck(
                            name="has_processes",
                            passed=True,
                            points=4,
                            message=f"File contains process list ({len(lines)} lines)"
                        ))
                        total_points += 4
                    else:
                        checks.append(ValidationCheck(
                            name="has_processes",
                            passed=False,
                            points=0,
                            max_points=4,
                            message=f"File has insufficient content"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="has_processes",
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


@TaskRegistry.register("processes")
class ManageTuningProfileTask(BaseTask):
    """Apply a named tuning profile with tuned-adm (EX200 v10 objective)."""

    def __init__(self):
        super().__init__(
            id="proc_tuned_001",
            category="processes",
            difficulty="easy",
            points=8
        )
        self.profile = None
        self.exam_tips = [
            "tuned-adm list — shows all available profiles",
            "tuned-adm active — shows the currently active profile",
            "tuned-adm profile <name> — applies a profile immediately (no reboot needed)",
            "'virtual-guest' and 'throughput-performance' are common exam profiles",
        ]

    def generate(self, **params):
        self.profile = params.get('profile', random.choice([
            'throughput-performance',
            'virtual-guest',
            'balanced',
            'powersave',
        ]))

        self.description = (
            f"Configure system tuning profile:\n\n"
            f"  1. Ensure the tuned service is running and enabled at boot\n"
            f"  2. Apply the '{self.profile}' tuning profile\n"
            f"  3. Verify the profile is active\n\n"
            f"The tuned daemon adjusts kernel parameters for the selected workload type."
        )

        self.hints = [
            "Start and enable tuned: systemctl enable --now tuned",
            "List available profiles: tuned-adm list",
            f"Apply profile: tuned-adm profile {self.profile}",
            "Verify: tuned-adm active",
            "Profile takes effect immediately — no reboot required",
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        result = execute_safe(['systemctl', 'is-active', 'tuned'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck("tuned_running", True, 3, "tuned service is running"))
            total_points += 3
        else:
            checks.append(ValidationCheck("tuned_running", False, 0, "tuned service is not running", max_points=3))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        result = execute_safe(['tuned-adm', 'active'])
        if result.success and self.profile in result.stdout:
            checks.append(ValidationCheck("profile_active", True, 5, f"Profile '{self.profile}' is active"))
            total_points += 5
        else:
            active = result.stdout.strip() if result.success else 'unknown'
            checks.append(ValidationCheck("profile_active", False, 0, f"Expected '{self.profile}', got: {active}", max_points=5))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class SetTuningProfileRecommendedTask(BaseTask):
    """Apply tuned-recommended profile and ensure persistence (EX200 v10 objective)."""

    def __init__(self):
        super().__init__(
            id="proc_tuned_002",
            category="processes",
            difficulty="medium",
            points=10
        )
        self.exam_tips = [
            "tuned-adm recommend — suggests the best profile for current hardware/environment",
            "Always verify the active profile after applying with tuned-adm active",
            "The tuned service must be enabled so the profile survives reboot",
        ]

    def generate(self, **params):
        self.description = (
            "Configure the system to use the tuned-recommended tuning profile:\n\n"
            "  1. Ensure the tuned service is running and enabled at boot\n"
            "  2. Determine the recommended profile for this system\n"
            "  3. Apply that recommended profile\n"
            "  4. Verify it is active\n\n"
            "The recommended profile is selected based on hardware and environment detection."
        )

        self.hints = [
            "Start and enable tuned: systemctl enable --now tuned",
            "Get recommendation: tuned-adm recommend",
            "Apply it in one step: tuned-adm profile $(tuned-adm recommend)",
            "Verify: tuned-adm active",
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        result_active = execute_safe(['systemctl', 'is-active', 'tuned'])
        result_enabled = execute_safe(['systemctl', 'is-enabled', 'tuned'])
        running = result_active.success and result_active.stdout.strip() == 'active'
        enabled = result_enabled.success and 'enabled' in result_enabled.stdout

        if running and enabled:
            checks.append(ValidationCheck("tuned_enabled", True, 4, "tuned is running and enabled at boot"))
            total_points += 4
        elif running:
            checks.append(ValidationCheck("tuned_enabled", False, 2, "tuned running but not enabled at boot", max_points=4))
            total_points += 2
        else:
            checks.append(ValidationCheck("tuned_enabled", False, 0, "tuned service is not running", max_points=4))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        result = execute_safe(['tuned-adm', 'active'])
        if result.success and 'Current active profile:' in result.stdout and 'none' not in result.stdout.lower():
            checks.append(ValidationCheck("profile_active", True, 6, f"Active: {result.stdout.strip()}"))
            total_points += 6
        else:
            checks.append(ValidationCheck("profile_active", False, 0, "No tuning profile is active", max_points=6))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class ListTuningProfilesTask(BaseTask):
    """List available tuning profiles and identify the active one."""

    def __init__(self):
        super().__init__(
            id="proc_tuned_003",
            category="processes",
            difficulty="easy",
            points=6
        )
        self.output_file = None
        self.exam_tips = [
            "tuned-adm list shows all installed profiles",
            "The active profile is highlighted in the output",
            "Use tuned-adm active to get just the current profile name",
        ]

    def generate(self, **params):
        self.output_file = params.get('output', '/tmp/tuned_profiles.txt')

        self.description = (
            f"Investigate the system tuning configuration:\n\n"
            f"  1. Ensure tuned is running\n"
            f"  2. List all available tuning profiles and save the output to {self.output_file}\n"
            f"  3. The file must include the currently active profile\n\n"
            f"This tests your ability to inspect system tuning state."
        )

        self.hints = [
            "Start tuned if not running: systemctl start tuned",
            f"List and save: tuned-adm list > {self.output_file}",
            "Check active profile: tuned-adm active",
            f"Or combine: {{ tuned-adm list; tuned-adm active; }} > {self.output_file}",
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        result = execute_safe(['systemctl', 'is-active', 'tuned'])
        if result.success and result.stdout.strip() == 'active':
            checks.append(ValidationCheck("tuned_running", True, 2, "tuned is running"))
            total_points += 2
        else:
            checks.append(ValidationCheck("tuned_running", False, 0, "tuned is not running", max_points=2))

        if validate_file_exists(self.output_file):
            try:
                with open(self.output_file) as f:
                    content = f.read()
                if 'balanced' in content or 'throughput' in content or 'virtual' in content:
                    checks.append(ValidationCheck("profiles_listed", True, 4, "Output file contains tuning profiles"))
                    total_points += 4
                else:
                    checks.append(ValidationCheck("profiles_listed", False, 0, "Output file does not appear to contain profile list", max_points=4))
            except Exception:
                checks.append(ValidationCheck("profiles_listed", False, 0, "Could not read output file", max_points=4))
        else:
            checks.append(ValidationCheck("profiles_listed", False, 0, f"Output file {self.output_file} not found", max_points=4))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
