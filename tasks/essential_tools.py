"""
Essential tools tasks for RHCSA exam (find, grep, tar, I/O redirection).
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe
from validators.file_validators import validate_file_exists, validate_file_contains
from validators.system_validators import validate_archive_contains, get_archive_compression


logger = logging.getLogger(__name__)


@TaskRegistry.register("essential_tools")
class FindFilesTask(BaseTask):
    """Find files using the find command."""

    def __init__(self):
        super().__init__(
            id="tools_find_001",
            category="essential_tools",
            difficulty="medium",
            points=10
        )
        self.criteria = None
        self.search_path = None
        self.output_file = None

    def generate(self, **params):
        """Generate find task."""
        criteria_options = [
            ('-name "*.log"', 'all files ending with .log'),
            ('-type d', 'all directories'),
            ('-user root', 'all files owned by root'),
            ('-size +10M', 'files larger than 10MB'),
            ('-mtime -7', 'files modified in last 7 days'),
            ('-perm 777', 'files with 777 permissions'),
        ]

        self.search_path = params.get('path', '/etc')
        criteria_choice = params.get('criteria', random.choice(criteria_options))

        if isinstance(criteria_choice, tuple):
            self.criteria, criteria_desc = criteria_choice
        else:
            self.criteria = criteria_choice
            criteria_desc = criteria_choice

        self.output_file = params.get('output', '/tmp/findresults.txt')

        self.description = (
            f"Use find command to locate files:\n"
            f"  - Search path: {self.search_path}\n"
            f"  - Criteria: {criteria_desc}\n"
            f"  - Save results to: {self.output_file}\n"
            f"  - Redirect output to the file"
        )

        self.hints = [
            f"Use find: find {self.search_path} {self.criteria}",
            f"Save to file: find {self.search_path} {self.criteria} > {self.output_file}",
            "Common find options: -name, -type, -user, -size, -mtime, -perm",
            "-type f = files, -type d = directories",
            "Sizes: -size +10M (larger than), -size -10M (smaller than)"
        ]

        return self

    def validate(self):
        """Validate find results."""
        checks = []
        total_points = 0

        # Check: Output file exists and has content
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=5,
                message=f"Output file {self.output_file} exists"
            ))
            total_points += 5

            # Check if file has content
            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=True,
                            points=5,
                            message=f"File contains search results"
                        ))
                        total_points += 5
                    else:
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=False,
                            points=0,
                            max_points=5,
                            message=f"File is empty"
                        ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="has_results",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=5,
                message=f"Output file {self.output_file} not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class GrepSearchTask(BaseTask):
    """Search for patterns in files using grep."""

    def __init__(self):
        super().__init__(
            id="tools_grep_001",
            category="essential_tools",
            difficulty="easy",
            points=8
        )
        self.pattern = None
        self.search_file = None
        self.output_file = None

    def generate(self, **params):
        """Generate grep task."""
        patterns = ['error', 'warning', 'failed', 'root', 'deny']
        self.pattern = params.get('pattern', random.choice(patterns))
        self.search_file = params.get('search_file', '/var/log/messages')
        self.output_file = params.get('output', '/tmp/grepresults.txt')

        self.description = (
            f"Search for pattern in a file:\n"
            f"  - Pattern: '{self.pattern}'\n"
            f"  - Search in: {self.search_file}\n"
            f"  - Save matching lines to: {self.output_file}\n"
            f"  - Use case-insensitive search"
        )

        self.hints = [
            f"Use grep: grep -i '{self.pattern}' {self.search_file}",
            f"Save to file: grep -i '{self.pattern}' {self.search_file} > {self.output_file}",
            "-i makes search case-insensitive",
            "-v inverts match (lines NOT containing pattern)",
            "-r searches recursively in directories",
            "-n shows line numbers"
        ]

        return self

    def validate(self):
        """Validate grep results."""
        checks = []
        total_points = 0

        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=4,
                message=f"Output file exists"
            ))
            total_points += 4

            # Check if pattern appears in output
            if validate_file_contains(self.output_file, self.pattern, case_sensitive=False):
                checks.append(ValidationCheck(
                    name="pattern_found",
                    passed=True,
                    points=4,
                    message=f"Output contains the pattern '{self.pattern}'"
                ))
                total_points += 4
            else:
                checks.append(ValidationCheck(
                    name="pattern_found",
                    passed=True,
                    points=2,
                    message=f"Output file exists (pattern may not be present in source, partial credit)"
                ))
                total_points += 2
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class CreateArchiveTask(BaseTask):
    """Create a tar archive with compression."""

    def __init__(self):
        super().__init__(
            id="tools_tar_001",
            category="essential_tools",
            difficulty="medium",
            points=12
        )
        self.archive_path = None
        self.source_path = None
        self.compression = None

    def generate(self, **params):
        """Generate tar archive task."""
        compressions = [
            ('gzip', 'gz', 'z', 'gzip'),
            ('bzip2', 'bz2', 'j', 'bzip2'),
            ('xz', 'xz', 'J', 'xz'),
        ]

        comp_choice = params.get('compression', random.choice(compressions))
        if isinstance(comp_choice, tuple):
            comp_name, comp_ext, comp_flag, self.compression = comp_choice
        else:
            comp_name = comp_choice
            comp_ext = comp_choice
            comp_flag = 'z' if comp_choice == 'gzip' else 'j'
            self.compression = comp_choice

        self.source_path = params.get('source', '/etc/sysconfig')
        self.archive_path = params.get('archive', f'/tmp/backup.tar.{comp_ext}')

        self.description = (
            f"Create a compressed archive:\n"
            f"  - Source directory: {self.source_path}\n"
            f"  - Archive file: {self.archive_path}\n"
            f"  - Compression: {comp_name}\n"
            f"  - Use tar command"
        )

        self.hints = [
            f"Create archive: tar -c{comp_flag}f {self.archive_path} {self.source_path}",
            "c = create, z = gzip, j = bzip2, J = xz, f = file",
            f"Example: tar -czf {self.archive_path} {self.source_path}",
            f"List contents: tar -tf {self.archive_path}",
            f"Extract: tar -xf {self.archive_path}"
        ]

        return self

    def validate(self):
        """Validate tar archive creation."""
        checks = []
        total_points = 0

        # Check 1: Archive file exists (5 points)
        if validate_file_exists(self.archive_path):
            checks.append(ValidationCheck(
                name="archive_exists",
                passed=True,
                points=5,
                message=f"Archive file exists"
            ))
            total_points += 5

            # Check 2: Archive has correct compression (4 points)
            actual_compression = get_archive_compression(self.archive_path)
            if actual_compression == self.compression:
                checks.append(ValidationCheck(
                    name="correct_compression",
                    passed=True,
                    points=4,
                    message=f"Archive has correct compression: {self.compression}"
                ))
                total_points += 4
            elif actual_compression:
                checks.append(ValidationCheck(
                    name="correct_compression",
                    passed=True,
                    points=2,
                    message=f"Archive is compressed but with {actual_compression} (partial credit)"
                ))
                total_points += 2
            else:
                checks.append(ValidationCheck(
                    name="correct_compression",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not determine compression type"
                ))

            # Check 3: Archive is valid tar file (3 points)
            result = execute_safe(['tar', '-tf', self.archive_path])
            if result.success:
                checks.append(ValidationCheck(
                    name="valid_archive",
                    passed=True,
                    points=3,
                    message=f"Archive is a valid tar file"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="valid_archive",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Archive is not a valid tar file"
                ))
        else:
            checks.append(ValidationCheck(
                name="archive_exists",
                passed=False,
                points=0,
                max_points=5,
                message=f"Archive file not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class ExtractArchiveTask(BaseTask):
    """Extract a tar archive to a specific location."""

    def __init__(self):
        super().__init__(
            id="tools_extract_001",
            category="essential_tools",
            difficulty="easy",
            points=8
        )
        self.archive_path = None
        self.extract_path = None
        self.expected_file = None

    def generate(self, **params):
        """Generate archive extraction task."""
        self.archive_path = params.get('archive', '/tmp/backup.tar.gz')
        self.extract_path = params.get('extract_to', '/tmp/extracted')
        self.expected_file = params.get('expected_file', 'README')

        self.description = (
            f"Extract an archive:\n"
            f"  - Archive: {self.archive_path}\n"
            f"  - Extract to: {self.extract_path}\n"
            f"  - Create extraction directory if needed\n"
            f"  - Verify extraction was successful"
        )

        self.hints = [
            f"Create directory: mkdir -p {self.extract_path}",
            f"Extract: tar -xf {self.archive_path} -C {self.extract_path}",
            "-x = extract, -C specifies destination directory",
            "Auto-detects compression type",
            f"List before extracting: tar -tf {self.archive_path}"
        ]

        return self

    def validate(self):
        """Validate archive extraction."""
        checks = []
        total_points = 0

        import os

        # Check 1: Extract directory exists (3 points)
        if os.path.exists(self.extract_path) and os.path.isdir(self.extract_path):
            checks.append(ValidationCheck(
                name="extract_dir_exists",
                passed=True,
                points=3,
                message=f"Extraction directory exists"
            ))
            total_points += 3

            # Check 2: Directory has content (5 points)
            try:
                contents = os.listdir(self.extract_path)
                if contents:
                    checks.append(ValidationCheck(
                        name="files_extracted",
                        passed=True,
                        points=5,
                        message=f"Files extracted ({len(contents)} items found)"
                    ))
                    total_points += 5
                else:
                    checks.append(ValidationCheck(
                        name="files_extracted",
                        passed=False,
                        points=0,
                        max_points=5,
                        message=f"Extract directory is empty"
                    ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="files_extracted",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not list directory: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="extract_dir_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Extract directory not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class IORedirectionTask(BaseTask):
    """Use I/O redirection and pipes."""

    def __init__(self):
        super().__init__(
            id="tools_io_001",
            category="essential_tools",
            difficulty="exam",
            points=12
        )
        self.source_file = None
        self.output_file = None
        self.operation = None

    def generate(self, **params):
        """Generate I/O redirection task."""
        operations = [
            ('sort_unique', 'Sort lines and remove duplicates'),
            ('count_lines', 'Count number of lines'),
            ('find_pattern', 'Find and count pattern occurrences'),
        ]

        self.source_file = params.get('source', '/etc/passwd')
        self.output_file = params.get('output', '/tmp/processed.txt')

        if params.get('operation'):
            self.operation = params['operation']
            op_desc = params.get('operation_desc', self.operation)
        else:
            self.operation, op_desc = random.choice(operations)

        if self.operation == 'sort_unique':
            task_details = f"  - Sort all lines alphabetically\n  - Remove duplicate lines\n  - Save to {self.output_file}"
            example = f"sort {self.source_file} | uniq > {self.output_file}"
        elif self.operation == 'count_lines':
            task_details = f"  - Count total number of lines\n  - Save count to {self.output_file}"
            example = f"wc -l {self.source_file} > {self.output_file}"
        else:  # find_pattern
            task_details = f"  - Count lines containing 'root'\n  - Save count to {self.output_file}"
            example = f"grep -c 'root' {self.source_file} > {self.output_file}"

        self.description = (
            f"Process a file using pipes and redirection:\n"
            f"  - Source file: {self.source_file}\n"
            f"{task_details}"
        )

        self.hints = [
            f"Example: {example}",
            "> redirects output to file (overwrites)",
            ">> appends to file",
            "| pipes output from one command to another",
            "2> redirects errors",
            "wc -l counts lines, sort sorts, uniq removes duplicates"
        ]

        return self

    def validate(self):
        """Validate I/O redirection."""
        checks = []
        total_points = 0

        # Check: Output file exists and has content
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=6,
                message=f"Output file created"
            ))
            total_points += 6

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=True,
                            points=6,
                            message=f"Output file contains processed data"
                        ))
                        total_points += 6
                    else:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=False,
                            points=0,
                            max_points=6,
                            message=f"Output file is empty"
                        ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="has_content",
                    passed=False,
                    points=0,
                    max_points=6,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=6,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class CreateHardLinkTask(BaseTask):
    """Create a hard link to a file."""

    def __init__(self):
        super().__init__(
            id="tools_hardlink_001",
            category="essential_tools",
            difficulty="medium",
            points=8
        )
        self.target_file = None
        self.link_path = None

    def generate(self, **params):
        """Generate hard link task."""
        file_suffix = random.randint(1, 99)
        self.target_file = params.get('target', f'/tmp/original{file_suffix}.txt')
        self.link_path = params.get('link', f'/tmp/hardlink{file_suffix}.txt')

        self.description = (
            f"Create a hard link:\n"
            f"  - Target file: {self.target_file} (create this file first if needed)\n"
            f"  - Hard link name: {self.link_path}\n"
            f"  - Both files should share the same inode"
        )

        self.hints = [
            f"Create target file: touch {self.target_file}",
            f"Create hard link: ln {self.target_file} {self.link_path}",
            "Hard links share the same inode number",
            "Verify with: ls -i (shows inode numbers)",
            "Hard links cannot cross filesystems"
        ]

        return self

    def validate(self):
        """Validate hard link creation."""
        checks = []
        total_points = 0

        import os

        # Check 1: Target file exists (2 points)
        if validate_file_exists(self.target_file):
            checks.append(ValidationCheck(
                name="target_exists",
                passed=True,
                points=2,
                message=f"Target file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="target_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Target file not found: {self.target_file}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Link exists (2 points)
        if validate_file_exists(self.link_path):
            checks.append(ValidationCheck(
                name="link_exists",
                passed=True,
                points=2,
                message=f"Link file exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="link_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Link not found: {self.link_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 3: Same inode (hard link verification) (4 points)
        try:
            target_inode = os.stat(self.target_file).st_ino
            link_inode = os.stat(self.link_path).st_ino

            if target_inode == link_inode:
                checks.append(ValidationCheck(
                    name="same_inode",
                    passed=True,
                    points=4,
                    message=f"Hard link confirmed (same inode: {target_inode})"
                ))
                total_points += 4
            else:
                # Check if it's a symbolic link instead
                if os.path.islink(self.link_path):
                    checks.append(ValidationCheck(
                        name="same_inode",
                        passed=False,
                        points=0,
                        max_points=4,
                        message=f"This is a symbolic link, not a hard link (different inodes)"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="same_inode",
                        passed=False,
                        points=0,
                        max_points=4,
                        message=f"Inodes don't match (target: {target_inode}, link: {link_inode})"
                    ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="same_inode",
                passed=False,
                points=0,
                max_points=4,
                message=f"Could not verify inode: {e}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class CreateSymbolicLinkTask(BaseTask):
    """Create a symbolic (soft) link to a file or directory."""

    def __init__(self):
        super().__init__(
            id="tools_symlink_001",
            category="essential_tools",
            difficulty="easy",
            points=6
        )
        self.target = None
        self.link_path = None
        self.is_directory = False

    def generate(self, **params):
        """Generate symbolic link task."""
        link_suffix = random.randint(1, 99)
        self.is_directory = params.get('is_directory', random.choice([True, False]))

        if self.is_directory:
            self.target = params.get('target', '/var/log')
            self.link_path = params.get('link', f'/home/loglink{link_suffix}')
        else:
            self.target = params.get('target', '/etc/passwd')
            self.link_path = params.get('link', f'/tmp/passwdlink{link_suffix}')

        target_type = "directory" if self.is_directory else "file"

        self.description = (
            f"Create a symbolic link:\n"
            f"  - Target {target_type}: {self.target}\n"
            f"  - Symbolic link: {self.link_path}\n"
            f"  - The link should point to the target"
        )

        self.hints = [
            f"Create symbolic link: ln -s {self.target} {self.link_path}",
            "The -s flag creates a symbolic (soft) link",
            "Symbolic links can point to files or directories",
            "Symbolic links can cross filesystems",
            "Verify with: ls -l (shows link -> target)"
        ]

        return self

    def validate(self):
        """Validate symbolic link creation."""
        checks = []
        total_points = 0

        import os

        # Check 1: Target exists (1 point)
        if os.path.exists(self.target):
            checks.append(ValidationCheck(
                name="target_exists",
                passed=True,
                points=1,
                message=f"Target exists: {self.target}"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="target_exists",
                passed=False,
                points=0,
                max_points=1,
                message=f"Target not found: {self.target}"
            ))

        # Check 2: Link exists and is a symlink (2 points)
        if os.path.islink(self.link_path):
            checks.append(ValidationCheck(
                name="is_symlink",
                passed=True,
                points=2,
                message=f"Symbolic link exists"
            ))
            total_points += 2

            # Check 3: Link points to correct target (3 points)
            actual_target = os.readlink(self.link_path)
            if actual_target == self.target or os.path.realpath(self.link_path) == os.path.realpath(self.target):
                checks.append(ValidationCheck(
                    name="correct_target",
                    passed=True,
                    points=3,
                    message=f"Link correctly points to: {self.target}"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="correct_target",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Link points to wrong target: {actual_target}"
                ))
        elif os.path.exists(self.link_path):
            # File exists but is not a symlink
            checks.append(ValidationCheck(
                name="is_symlink",
                passed=False,
                points=0,
                max_points=2,
                message=f"File exists but is not a symbolic link (might be hard link or copy)"
            ))
        else:
            checks.append(ValidationCheck(
                name="is_symlink",
                passed=False,
                points=0,
                max_points=2,
                message=f"Link not found: {self.link_path}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class FindByPermissionsTask(BaseTask):
    """Find files by special permissions (SUID, SGID)."""

    def __init__(self):
        super().__init__(
            id="tools_find_perm_001",
            category="essential_tools",
            difficulty="exam",
            points=10
        )
        self.search_path = None
        self.permission_type = None
        self.output_file = None

    def generate(self, **params):
        """Generate find by permissions task."""
        perm_options = [
            ('suid', '-perm -4000', 'SUID (setuid) files'),
            ('sgid', '-perm -2000', 'SGID (setgid) files'),
            ('world_writable', '-perm -0002', 'world-writable files'),
        ]

        self.search_path = params.get('path', '/')
        self.output_file = params.get('output', '/tmp/special_perms.txt')

        if params.get('permission_type'):
            self.permission_type = params['permission_type']
            self.perm_flag = next((p[1] for p in perm_options if p[0] == self.permission_type), '-perm -4000')
            self.perm_desc = next((p[2] for p in perm_options if p[0] == self.permission_type), 'special permission files')
        else:
            self.permission_type, self.perm_flag, self.perm_desc = random.choice(perm_options)

        self.description = (
            f"Find files with special permissions:\n"
            f"  - Search path: {self.search_path}\n"
            f"  - Find all {self.perm_desc}\n"
            f"  - Save results to: {self.output_file}\n"
            f"  - Suppress permission denied errors"
        )

        self.hints = [
            "Use 'find' with the -perm flag to match special permission bits",
            "SUID bit: -perm -4000  |  SGID bit: -perm -2000  |  world-writable: -perm -0002",
            "The leading '-' means 'at least these bits set'",
            f"Redirect output to {self.output_file} and suppress errors with 2>/dev/null",
        ]

        return self

    def validate(self):
        """Validate find by permissions."""
        checks = []
        total_points = 0

        # Check: Output file exists
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=True,
                points=5,
                message=f"Output file created"
            ))
            total_points += 5

            # Check if file has content (may be empty if no matching files, which is OK)
            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=True,
                            points=5,
                            message=f"Found files with {self.perm_desc}"
                        ))
                        total_points += 5
                    else:
                        # Empty file could be valid if no such files exist
                        checks.append(ValidationCheck(
                            name="has_results",
                            passed=True,
                            points=3,
                            message=f"Output file exists but is empty (may be correct if no matches)"
                        ))
                        total_points += 3
            except Exception as e:
                checks.append(ValidationCheck(
                    name="has_results",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not read file: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_file_exists",
                passed=False,
                points=0,
                max_points=5,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class CopyPreserveTask(BaseTask):
    """Copy files while preserving attributes."""

    def __init__(self):
        super().__init__(
            id="tools_copy_001",
            category="essential_tools",
            difficulty="medium",
            points=8
        )
        self.source = None
        self.destination = None

    def generate(self, **params):
        """Generate copy with preserve task."""
        suffix = random.randint(1, 99)
        self.source = params.get('source', '/etc/sysconfig')
        self.destination = params.get('destination', f'/backup/sysconfig{suffix}')

        self.description = (
            f"Copy a directory while preserving all attributes:\n"
            f"  - Source: {self.source}\n"
            f"  - Destination: {self.destination}\n"
            f"  - Preserve: permissions, ownership, timestamps\n"
            f"  - Copy all contents recursively"
        )

        self.hints = [
            f"Use cp with archive mode: cp -a {self.source} {self.destination}",
            "Alternative: cp -rp (recursive, preserve)",
            "-a is equivalent to -dR --preserve=all",
            "This preserves: mode, ownership, timestamps, links",
            "Verify with: ls -la on both directories"
        ]

        return self

    def validate(self):
        """Validate copy preserve."""
        checks = []
        total_points = 0

        import os

        # Check 1: Destination exists (4 points)
        if os.path.exists(self.destination):
            checks.append(ValidationCheck(
                name="destination_exists",
                passed=True,
                points=4,
                message=f"Destination exists"
            ))
            total_points += 4

            # Check 2: Has contents (4 points)
            try:
                if os.path.isdir(self.destination):
                    contents = os.listdir(self.destination)
                    if contents:
                        checks.append(ValidationCheck(
                            name="has_contents",
                            passed=True,
                            points=4,
                            message=f"Directory has contents ({len(contents)} items)"
                        ))
                        total_points += 4
                    else:
                        checks.append(ValidationCheck(
                            name="has_contents",
                            passed=False,
                            points=0,
                            max_points=4,
                            message=f"Directory is empty"
                        ))
                else:
                    # It's a file
                    checks.append(ValidationCheck(
                        name="has_contents",
                        passed=True,
                        points=4,
                        message=f"File copied"
                    ))
                    total_points += 4
            except Exception as e:
                checks.append(ValidationCheck(
                    name="has_contents",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not check contents: {e}"
                ))
        else:
            checks.append(ValidationCheck(
                name="destination_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Destination not found: {self.destination}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class SortFileTask(BaseTask):
    """Sort file contents and save to output."""

    def __init__(self):
        super().__init__(
            id="tools_sort_001",
            category="essential_tools",
            difficulty="easy",
            points=6
        )
        self.source_file = None
        self.output_file = None
        self.reverse = False

    def generate(self, **params):
        self.source_file = params.get('source', '/etc/passwd')
        self.output_file = params.get('output', '/tmp/sorted_output.txt')
        self.reverse = params.get('reverse', random.choice([True, False]))

        sort_order = "reverse alphabetically" if self.reverse else "alphabetically"

        self.description = (
            f"Sort file contents:\n"
            f"  - Source file: {self.source_file}\n"
            f"  - Sort order: {sort_order}\n"
            f"  - Save to: {self.output_file}"
        )

        if self.reverse:
            self.hints = [
                f"Sort in reverse: sort -r {self.source_file} > {self.output_file}",
                "-r reverses the sort order",
                "Verify: head {self.output_file}"
            ]
        else:
            self.hints = [
                f"Sort: sort {self.source_file} > {self.output_file}",
                "Default sort is alphabetical, ascending",
                f"Verify: head {self.output_file}"
            ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=3,
                message=f"Output file exists"
            ))
            total_points += 3

            try:
                with open(self.output_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        # Check if sorted
                        sorted_lines = sorted(lines, reverse=self.reverse)
                        if lines == sorted_lines:
                            checks.append(ValidationCheck(
                                name="correctly_sorted",
                                passed=True,
                                points=3,
                                message=f"File is correctly sorted"
                            ))
                            total_points += 3
                        else:
                            checks.append(ValidationCheck(
                                name="correctly_sorted",
                                passed=False,
                                points=0,
                                max_points=3,
                                message=f"File is not sorted correctly"
                            ))
                    else:
                        checks.append(ValidationCheck(
                            name="correctly_sorted",
                            passed=True,
                            points=2,
                            message=f"File has content (partial credit)"
                        ))
                        total_points += 2
            except Exception:
                checks.append(ValidationCheck(
                    name="correctly_sorted",
                    passed=False,
                    points=0,
                    max_points=3,
                    message=f"Could not verify sorting"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("essential_tools")
class CutFieldsTask(BaseTask):
    """Extract specific fields from a file using cut."""

    def __init__(self):
        super().__init__(
            id="tools_cut_001",
            category="essential_tools",
            difficulty="medium",
            points=8
        )
        self.source_file = None
        self.output_file = None
        self.field = None
        self.delimiter = None

    def generate(self, **params):
        self.source_file = params.get('source', '/etc/passwd')
        self.output_file = params.get('output', '/tmp/extracted_field.txt')
        self.field = params.get('field', random.choice([1, 3, 7]))
        self.delimiter = params.get('delimiter', ':')

        field_names = {1: 'username', 3: 'UID', 7: 'shell'}
        field_name = field_names.get(self.field, f'field {self.field}')

        self.description = (
            f"Extract a field from a file:\n"
            f"  - Source file: {self.source_file}\n"
            f"  - Extract: {field_name} (field {self.field})\n"
            f"  - Delimiter: '{self.delimiter}'\n"
            f"  - Save to: {self.output_file}"
        )

        self.hints = [
            f"Use cut: cut -d'{self.delimiter}' -f{self.field} {self.source_file} > {self.output_file}",
            "-d specifies delimiter, -f specifies field number",
            f"Field numbering starts at 1",
            f"Verify: head {self.output_file}"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

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
                    if content:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=True,
                            points=4,
                            message=f"File contains extracted fields"
                        ))
                        total_points += 4
                    else:
                        checks.append(ValidationCheck(
                            name="has_content",
                            passed=False,
                            points=0,
                            max_points=4,
                            message=f"File is empty"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="has_content",
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


@TaskRegistry.register("essential_tools")
class DiffFilesTask(BaseTask):
    """Compare two files using diff."""

    def __init__(self):
        super().__init__(
            id="tools_diff_001",
            category="essential_tools",
            difficulty="medium",
            points=8
        )
        self.file1 = None
        self.file2 = None
        self.output_file = None

    def generate(self, **params):
        self.file1 = params.get('file1', '/etc/passwd')
        self.file2 = params.get('file2', '/etc/passwd-')
        self.output_file = params.get('output', '/tmp/diff_output.txt')

        self.description = (
            f"Compare two files:\n"
            f"  - File 1: {self.file1}\n"
            f"  - File 2: {self.file2}\n"
            f"  - Save differences to: {self.output_file}\n"
            f"  - Show what changed between files"
        )

        self.hints = [
            f"Compare files: diff {self.file1} {self.file2} > {self.output_file}",
            "diff shows lines that differ between files",
            "< indicates lines only in first file",
            "> indicates lines only in second file",
            f"Unified format: diff -u {self.file1} {self.file2}"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: Output file exists
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=8,
                message=f"Diff output file created"
            ))
            total_points += 8
        else:
            # Could be empty if files are identical
            import os
            if os.path.exists(self.output_file):
                checks.append(ValidationCheck(
                    name="output_exists",
                    passed=True,
                    points=6,
                    message=f"Diff file created (may be empty if files identical)"
                ))
                total_points += 6
            else:
                checks.append(ValidationCheck(
                    name="output_exists",
                    passed=False,
                    points=0,
                    max_points=8,
                    message=f"Output file not found"
                ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
