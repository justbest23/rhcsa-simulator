"""
File permissions and ACL tasks for RHCSA exam.
"""

import os
import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.file_validators import (
    validate_file_exists, validate_file_permissions,
    validate_file_ownership, validate_acl_entry,
    get_file_permissions, get_file_owner, get_file_group
)


logger = logging.getLogger(__name__)


@TaskRegistry.register("permissions")
class SetFilePermissionsTask(BaseTask):
    """Set standard permissions on a file."""

    def __init__(self):
        super().__init__(
            id="perm_basic_001",
            category="permissions",
            difficulty="easy",
            points=4
        )
        self.tags = []
        self.exam_tips = [
            "Use chmod command with octal notation (e.g., chmod 644 file)",
            "Verify permissions with 'ls -l' - shows rwxrwxrwx format",
            "Remember: r=4, w=2, x=1, combine them for each user/group/other",
            "Common patterns: 644 (rw-r--r--), 755 (rwxr-xr-x), 600 (rw-------)"
        ]
        self.file_path = None
        self.permissions = None

    def generate(self, **params):
        """Generate permissions task."""
        file_suffix = random.randint(1, 99)
        self.file_path = params.get('file', f'/tmp/testfile{file_suffix}.txt')
        perm_choices = ['644', '640', '600', '755', '750', '700']
        self.permissions = params.get('perms', random.choice(perm_choices))

        self.description = (
            f"Set permissions on file '{self.file_path}':\n"
            f"  - Permissions: {self.permissions} (octal)"
        )

        self.hints = [
            "Use 'chmod' command",
            f"Format: chmod {self.permissions} {self.file_path}",
            "Verify with 'ls -l' or 'stat' command"
        ]

        return self

    def validate(self):
        """Validate file permissions."""
        checks = []
        total_points = 0

        # Check 1: File exists (1 point)
        if validate_file_exists(self.file_path):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=1,
                message=f"File exists: {self.file_path}"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=1,
                message=f"File not found: {self.file_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Correct permissions (3 points)
        if validate_file_permissions(self.file_path, self.permissions):
            checks.append(ValidationCheck(
                name="permissions",
                passed=True,
                points=3,
                message=f"Permissions correct: {self.permissions}"
            ))
            total_points += 3
        else:
            actual = get_file_permissions(self.file_path)
            checks.append(ValidationCheck(
                name="permissions",
                passed=False,
                points=0,
                max_points=3,
                message=f"Permissions incorrect: expected {self.permissions}, got {actual}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class SetFileOwnershipTask(BaseTask):
    """Set file ownership (owner and group)."""

    def __init__(self):
        super().__init__(
            id="perm_owner_001",
            category="permissions",
            difficulty="easy",
            points=5
        )
        self.tags = []
        self.exam_tips = [
            "Use chown for changing owner and group: chown user:group file",
            "Change only owner: chown user file",
            "Change only group: chown :group file or use chgrp group file",
            "Use -R flag for recursive changes on directories"
        ]
        self.file_path = None
        self.owner = None
        self.group = None

    def generate(self, **params):
        """Generate ownership task."""
        file_suffix = random.randint(1, 99)
        self.file_path = params.get('file', f'/tmp/ownertest{file_suffix}.txt')
        self.owner = params.get('owner', random.choice(['root', 'nobody', 'apache']))
        self.group = params.get('group', random.choice(['root', 'wheel', 'apache']))

        self.description = (
            f"Set ownership on file '{self.file_path}':\n"
            f"  - Owner: {self.owner}\n"
            f"  - Group: {self.group}"
        )

        self.hints = [
            "Use 'chown' command",
            f"Format: chown {self.owner}:{self.group} {self.file_path}",
            "Or use chown for owner and chgrp for group separately",
            "Verify with 'ls -l' command"
        ]

        return self

    def validate(self):
        """Validate file ownership."""
        checks = []
        total_points = 0

        # Check 1: File exists (1 point)
        if validate_file_exists(self.file_path):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=1,
                message=f"File exists"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=1,
                message=f"File not found: {self.file_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Correct owner (2 points)
        actual_owner = get_file_owner(self.file_path)
        if actual_owner == self.owner:
            checks.append(ValidationCheck(
                name="correct_owner",
                passed=True,
                points=2,
                message=f"Owner correct: {self.owner}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="correct_owner",
                passed=False,
                points=0,
                max_points=2,
                message=f"Owner incorrect: expected {self.owner}, got {actual_owner}"
            ))

        # Check 3: Correct group (2 points)
        actual_group = get_file_group(self.file_path)
        if actual_group == self.group:
            checks.append(ValidationCheck(
                name="correct_group",
                passed=True,
                points=2,
                message=f"Group correct: {self.group}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="correct_group",
                passed=False,
                points=0,
                max_points=2,
                message=f"Group incorrect: expected {self.group}, got {actual_group}"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class SetACLTask(BaseTask):
    """Set ACL on a file."""

    def __init__(self):
        super().__init__(
            id="acl_001",
            category="permissions",
            difficulty="exam",
            points=8
        )
        self.tags = ['acl']
        self.exam_tips = [
            "ACLs grant additional permissions beyond basic owner/group/other",
            "Set ACL with setfacl -m u:username:rwx file",
            "View ACLs with getfacl file",
            "ls -l shows '+' after permissions when ACLs are set",
            "Remove ACL with setfacl -x u:username file"
        ]
        self.file_path = None
        self.acl_user = None
        self.acl_perms = None

    def generate(self, **params):
        """Generate ACL task."""
        file_suffix = random.randint(1, 99)
        self.file_path = params.get('file', f'/tmp/acltest{file_suffix}.txt')
        self.acl_user = params.get('user', random.choice(['apache', 'nginx', 'nobody']))
        self.acl_perms = params.get('perms', random.choice(['r--', 'rw-', 'r-x']))

        self.description = (
            f"Configure ACL on file '{self.file_path}':\n"
            f"  - Grant user '{self.acl_user}' permissions: {self.acl_perms}\n"
            f"  - Use ACLs (Access Control Lists)"
        )

        self.hints = [
            "Use 'setfacl' command",
            f"Format: setfacl -m u:{self.acl_user}:{self.acl_perms} {self.file_path}",
            "Verify with 'getfacl <file>'",
            "Note: ACL permissions format is read(r), write(w), execute(x)"
        ]

        return self

    def validate(self):
        """Validate ACL configuration."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if validate_file_exists(self.file_path):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=2,
                message=f"File exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"File not found: {self.file_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: ACL entry exists (6 points)
        if validate_acl_entry(self.file_path, 'user', self.acl_user, self.acl_perms):
            checks.append(ValidationCheck(
                name="acl_entry",
                passed=True,
                points=6,
                message=f"ACL configured correctly: user:{self.acl_user}:{self.acl_perms}"
            ))
            total_points += 6
        else:
            checks.append(ValidationCheck(
                name="acl_entry",
                passed=False,
                points=0,
                max_points=6,
                message=f"ACL not configured correctly for user {self.acl_user}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class SetSpecialPermissionsTask(BaseTask):
    """Set special permissions (setuid, setgid, sticky bit)."""

    def __init__(self):
        super().__init__(
            id="perm_special_001",
            category="permissions",
            difficulty="exam",
            points=7
        )
        self.tags = ['special-permissions']
        self.exam_tips = [
            "SUID (4): Runs executable with owner's permissions (chmod 4755 or chmod u+s)",
            "SGID (2): On files runs with group permissions, on dirs new files inherit group (chmod 2755 or chmod g+s)",
            "Sticky bit (1): Only file owner can delete files in directory (chmod 1777 or chmod +t)",
            "ls -l shows 's' for SUID/SGID, 't' for sticky bit",
            "Common: /tmp has sticky bit (drwxrwxrwt)"
        ]
        self.file_path = None
        self.special_bit = None
        self.permissions = None

    def generate(self, **params):
        """Generate special permissions task."""
        file_suffix = random.randint(1, 99)
        self.file_path = params.get('file', f'/tmp/specialperm{file_suffix}')

        special_options = [
            ('setuid', '4755', 'setuid', 'file', 'run as the file owner regardless of who executes it'),
            ('setgid', '2755', 'setgid', 'file', 'run with the file group regardless of who executes it'),
            ('sticky', '1777', 'sticky bit', 'directory', 'only the file owner can delete files within it'),
        ]

        self.special_bit, self.permissions, perm_name, target_type, effect = random.choice(special_options)

        if target_type == 'directory' and not os.path.isdir(self.file_path):
            os.makedirs(self.file_path, exist_ok=True)

        self.description = (
            f"Apply the {perm_name} to the {target_type} at '{self.file_path}'.\n\n"
            f"Effect: {effect.capitalize()}.\n\n"
            f"The base permissions should be rwxr-xr-x for a file (755),\n"
            f"or rwxrwxrwx for a sticky directory (777). Apply the appropriate\n"
            f"special bit on top of those base permissions."
        )

        self.hints = [
            f"First create the {target_type} if it doesn't exist",
            "Special permission bits can be applied with chmod using symbolic notation (+s, +t) or octal",
            "Symbolic: chmod +t (sticky), chmod u+s (setuid), chmod g+s (setgid)",
            f"Verify with: ls -ld {self.file_path}  — look for 's' or 't' in the permission string",
        ]

        return self

    def validate(self):
        """Validate special permissions."""
        checks = []
        total_points = 0

        # Check 1: File exists (2 points)
        if validate_file_exists(self.file_path):
            checks.append(ValidationCheck(
                name="file_exists",
                passed=True,
                points=2,
                message=f"File exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="file_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"File not found: {self.file_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Correct permissions including special bit (5 points)
        if validate_file_permissions(self.file_path, self.permissions):
            checks.append(ValidationCheck(
                name="special_permissions",
                passed=True,
                points=5,
                message=f"Special permissions correct: {self.permissions}"
            ))
            total_points += 5
        else:
            actual = get_file_permissions(self.file_path)
            checks.append(ValidationCheck(
                name="special_permissions",
                passed=False,
                points=0,
                max_points=5,
                message=f"Permissions incorrect: expected {self.permissions}, got {actual}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class SharedDirectoryTask(BaseTask):
    """Configure a shared directory with SGID and sticky bit."""

    def __init__(self):
        super().__init__(
            id="perm_shared_dir_001",
            category="permissions",
            difficulty="exam",
            points=12
        )
        self.tags = ['special-permissions', 'collaborative']
        self.exam_tips = [
            "Collaborative directories typically combine two special bits for shared access",
            "One special bit ensures new files inherit the directory group instead of the creator's group",
            "Another special bit ensures users can only delete files they own within the directory",
            "Set group ownership with: chown :groupname directory",
            "Verify with: ls -ld — the permission string will show special bit characters",
        ]
        self.dir_path = None
        self.group = None

    def generate(self, **params):
        """Generate shared directory task."""
        dir_suffix = random.randint(1, 99)
        self.dir_path = params.get('dir', f'/shared/project{dir_suffix}')
        self.group = params.get('group', random.choice(['developers', 'team', 'shared']))

        self.description = (
            f"Configure a collaborative shared directory at '{self.dir_path}':\n"
            f"  - Create the directory (including parent directories)\n"
            f"  - Set group ownership to: {self.group}\n"
            f"  - All new files/directories should inherit the group '{self.group}'\n"
            f"  - Users should only be able to delete their own files\n"
            f"  - Group members should have full read/write/execute access\n"
            f"  - Others should have no access"
        )

        self.hints = [
            f"Create directory: mkdir -p {self.dir_path}",
            f"Set group ownership: chown :{self.group} {self.dir_path}",
            "You need two special bits: one for group inheritance, one for deletion protection",
            "chmod supports symbolic special-bit notation: u+s, g+s, +t",
            f"Verify: ls -ld {self.dir_path}  — look for 's' and 't' characters in the output",
        ]

        return self

    def validate(self):
        """Validate shared directory configuration."""
        checks = []
        total_points = 0

        # Check 1: Directory exists (2 points)
        if validate_file_exists(self.dir_path, file_type='directory'):
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=True,
                points=2,
                message=f"Directory exists: {self.dir_path}"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Directory not found: {self.dir_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Correct group ownership (3 points)
        actual_group = get_file_group(self.dir_path)
        if actual_group == self.group:
            checks.append(ValidationCheck(
                name="group_ownership",
                passed=True,
                points=3,
                message=f"Group ownership correct: {self.group}"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="group_ownership",
                passed=False,
                points=0,
                max_points=3,
                message=f"Group mismatch: expected {self.group}, got {actual_group}"
            ))

        # Check 3: SGID bit set (3 points)
        actual_perms = get_file_permissions(self.dir_path)
        sgid_set = actual_perms and len(actual_perms) == 4 and actual_perms[0] in ['2', '3', '6', '7']
        if sgid_set:
            checks.append(ValidationCheck(
                name="sgid_set",
                passed=True,
                points=3,
                message=f"SGID bit is set (new files inherit group)"
            ))
            total_points += 3
        else:
            checks.append(ValidationCheck(
                name="sgid_set",
                passed=False,
                points=0,
                max_points=3,
                message=f"SGID bit not set (permissions: {actual_perms})"
            ))

        # Check 4: Sticky bit set (2 points)
        sticky_set = actual_perms and len(actual_perms) == 4 and actual_perms[0] in ['1', '3', '5', '7']
        if sticky_set:
            checks.append(ValidationCheck(
                name="sticky_set",
                passed=True,
                points=2,
                message=f"Sticky bit is set (users can only delete own files)"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="sticky_set",
                passed=False,
                points=0,
                max_points=2,
                message=f"Sticky bit not set (permissions: {actual_perms})"
            ))

        # Check 5: Group has rwx, others have no access (2 points)
        if actual_perms and len(actual_perms) >= 3:
            base_perms = actual_perms[-3:]  # Get last 3 digits
            group_ok = base_perms[1] == '7'  # Group has rwx
            others_ok = base_perms[2] == '0'  # Others have nothing

            if group_ok and others_ok:
                checks.append(ValidationCheck(
                    name="base_perms",
                    passed=True,
                    points=2,
                    message=f"Base permissions correct (group rwx, others none)"
                ))
                total_points += 2
            elif group_ok:
                checks.append(ValidationCheck(
                    name="base_perms",
                    passed=True,
                    points=1,
                    message=f"Group has full access (partial: others should have none)"
                ))
                total_points += 1
            else:
                checks.append(ValidationCheck(
                    name="base_perms",
                    passed=False,
                    points=0,
                    max_points=2,
                    message=f"Permissions incorrect: {actual_perms}"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class DefaultACLTask(BaseTask):
    """Set default ACL on a directory for inheritance."""

    def __init__(self):
        super().__init__(
            id="acl_default_001",
            category="permissions",
            difficulty="exam",
            points=10
        )
        self.tags = ['acl', 'inheritance']
        self.exam_tips = [
            "Default ACLs only work on directories, not files",
            "Use -d flag with setfacl to set default ACL: setfacl -d -m u:user:rwx dir",
            "Default ACLs are inherited by newly created files/subdirectories",
            "Without -d flag, ACL only applies to the directory itself",
            "Verify with getfacl dir - look for 'default:user:' entries",
            "Regular ACL affects existing directory, default ACL affects future contents"
        ]
        self.dir_path = None
        self.acl_user = None
        self.acl_perms = None

    def generate(self, **params):
        """Generate default ACL task."""
        dir_suffix = random.randint(1, 99)
        # Use /srv (never a mount point in this sim) rather than /data — the
        # autofs and boot-recovery tasks claim /data as an auto/rescue mount,
        # which would shadow an ACL directory nested under it.
        self.dir_path = params.get('dir', f'/srv/acltest{dir_suffix}')
        self.acl_user = params.get('user', random.choice(['webadmin', 'developer', 'operator']))
        self.acl_perms = params.get('perms', random.choice(['rwx', 'rw-', 'r-x']))

        self.description = (
            f"Configure default ACL on directory '{self.dir_path}':\n"
            f"  - Create the directory if it doesn't exist\n"
            f"  - Set a DEFAULT ACL for user '{self.acl_user}' with permissions: {self.acl_perms}\n"
            f"  - All NEW files and directories created inside should automatically\n"
            f"    grant these permissions to '{self.acl_user}'\n"
            f"  - This is for inheritance, not just the directory itself"
        )

        self.hints = [
            f"Create directory: mkdir -p {self.dir_path}",
            f"Set DEFAULT ACL: setfacl -d -m u:{self.acl_user}:{self.acl_perms} {self.dir_path}",
            "The -d flag sets DEFAULT ACL (affects new files)",
            "Without -d, ACL only affects the directory itself",
            f"Verify with: getfacl {self.dir_path} | grep default"
        ]

        return self

    def validate(self):
        """Validate default ACL configuration."""
        checks = []
        total_points = 0

        # Check 1: Directory exists (2 points)
        if validate_file_exists(self.dir_path, file_type='directory'):
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=True,
                points=2,
                message=f"Directory exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Directory not found: {self.dir_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Default ACL is set (8 points)
        try:
            import subprocess
            result = subprocess.run(
                ['getfacl', self.dir_path],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout

            # Look for default ACL entry
            expected_patterns = [
                f"default:user:{self.acl_user}:{self.acl_perms}",
                f"default:user:{self.acl_user}:{self.acl_perms.replace('-', '')}"
            ]

            default_acl_found = any(pattern in output for pattern in expected_patterns)

            if default_acl_found:
                checks.append(ValidationCheck(
                    name="default_acl",
                    passed=True,
                    points=8,
                    message=f"Default ACL set correctly for user:{self.acl_user}:{self.acl_perms}"
                ))
                total_points += 8
            elif f"default:user:{self.acl_user}" in output:
                # User has default ACL but different permissions
                checks.append(ValidationCheck(
                    name="default_acl",
                    passed=True,
                    points=5,
                    message=f"Default ACL exists for {self.acl_user} but permissions differ"
                ))
                total_points += 5
            elif "default:" in output:
                # Some default ACL exists
                checks.append(ValidationCheck(
                    name="default_acl",
                    passed=True,
                    points=3,
                    message=f"Default ACL exists but not for user {self.acl_user}"
                ))
                total_points += 3
            else:
                checks.append(ValidationCheck(
                    name="default_acl",
                    passed=False,
                    points=0,
                    max_points=8,
                    message=f"No default ACL found (use setfacl -d -m ...)"
                ))

        except Exception as e:
            checks.append(ValidationCheck(
                name="default_acl",
                passed=False,
                points=0,
                max_points=8,
                message=f"Could not verify ACL: {e}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class RecursivePermissionsTask(BaseTask):
    """Set permissions recursively on a directory tree."""

    def __init__(self):
        super().__init__(
            id="perm_recursive_001",
            category="permissions",
            difficulty="medium",
            points=8
        )
        self.tags = ['recursive']
        self.exam_tips = [
            "Use chown -R user:group dir for recursive ownership changes",
            "chmod -R applies same permissions to all files and directories",
            "Better: use find to distinguish files vs directories",
            "Find directories: find /path -type d -exec chmod 755 {} \\;",
            "Find files: find /path -type f -exec chmod 644 {} \\;",
            "This prevents giving execute permission to regular files"
        ]
        self.dir_path = None
        self.dir_perms = None
        self.file_perms = None
        self.owner = None
        self.group = None

    def generate(self, **params):
        """Generate recursive permissions task."""
        dir_suffix = random.randint(1, 99)
        self.dir_path = params.get('dir', f'/var/data/project{dir_suffix}')
        self.owner = params.get('owner', random.choice(['root', 'admin']))
        self.group = params.get('group', random.choice(['webteam', 'developers']))
        self.dir_perms = params.get('dir_perms', '755')
        self.file_perms = params.get('file_perms', '644')

        self.description = (
            f"Set permissions recursively on '{self.dir_path}':\n"
            f"  - Owner: {self.owner}\n"
            f"  - Group: {self.group}\n"
            f"  - Directory permissions: {self.dir_perms}\n"
            f"  - File permissions: {self.file_perms}\n"
            f"  - Apply to ALL files and subdirectories"
        )

        self.hints = [
            f"Change ownership recursively: chown -R {self.owner}:{self.group} {self.dir_path}",
            f"Set directory permissions: find {self.dir_path} -type d -exec chmod {self.dir_perms} {{}} \\;",
            f"Set file permissions: find {self.dir_path} -type f -exec chmod {self.file_perms} {{}} \\;",
            "Alternative: chmod -R sets same perms for all (less precise)",
            "Use find to distinguish files vs directories"
        ]

        return self

    def validate(self):
        """Validate recursive permissions."""
        checks = []
        total_points = 0

        # Check 1: Directory exists (2 points)
        if validate_file_exists(self.dir_path, file_type='directory'):
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=True,
                points=2,
                message=f"Directory exists"
            ))
            total_points += 2
        else:
            checks.append(ValidationCheck(
                name="dir_exists",
                passed=False,
                points=0,
                max_points=2,
                message=f"Directory not found: {self.dir_path}"
            ))
            return ValidationResult(self.id, False, total_points, self.points, checks)

        # Check 2: Ownership is correct (3 points)
        actual_owner = get_file_owner(self.dir_path)
        actual_group = get_file_group(self.dir_path)

        if actual_owner == self.owner and actual_group == self.group:
            checks.append(ValidationCheck(
                name="ownership",
                passed=True,
                points=3,
                message=f"Ownership correct: {self.owner}:{self.group}"
            ))
            total_points += 3
        elif actual_owner == self.owner or actual_group == self.group:
            checks.append(ValidationCheck(
                name="ownership",
                passed=True,
                points=1,
                message=f"Partial ownership match: {actual_owner}:{actual_group}"
            ))
            total_points += 1
        else:
            checks.append(ValidationCheck(
                name="ownership",
                passed=False,
                points=0,
                max_points=3,
                message=f"Ownership incorrect: {actual_owner}:{actual_group}"
            ))

        # Check 3: Directory has correct permissions (3 points)
        if validate_file_permissions(self.dir_path, self.dir_perms):
            checks.append(ValidationCheck(
                name="dir_permissions",
                passed=True,
                points=3,
                message=f"Directory permissions correct: {self.dir_perms}"
            ))
            total_points += 3
        else:
            actual_perms = get_file_permissions(self.dir_path)
            checks.append(ValidationCheck(
                name="dir_permissions",
                passed=False,
                points=0,
                max_points=3,
                message=f"Directory permissions: expected {self.dir_perms}, got {actual_perms}"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("permissions")
class UmaskConfigTask(BaseTask):
    """Configure umask for default permissions."""

    def __init__(self):
        super().__init__(
            id="perm_umask_001",
            category="permissions",
            difficulty="medium",
            points=10
        )
        self.requires_persistence = True
        self.tags = ['umask', 'persistent']
        self.exam_tips = [
            "Umask sets default permissions for newly created files",
            "Umask subtracts from 666 (files) and 777 (directories)",
            "Common umasks: 0022 (755/644), 0027 (750/640), 0077 (700/600)",
            "Set permanently in ~/.bashrc, ~/.bash_profile, or /etc/profile.d/",
            "System-wide: create script in /etc/profile.d/ with umask command",
            "Test by logging in as user and running 'umask' command"
        ]
        self.umask_value = None
        self.target_user = None

    def generate(self, **params):
        umasks = ['0027', '0077', '0022', '0002']
        self.umask_value = params.get('umask', random.choice(umasks))
        self.target_user = params.get('user', random.choice(['root', 'testuser']))
        self.description = (
            f"Configure default umask:\n"
            f"  - Set umask to {self.umask_value} for user {self.target_user}\n"
            f"  - Make the change persistent (survives login/logout)\n"
            f"  - New files should be created with the correct default permissions"
        )
        self.hints = [
            f"Set in ~/.bashrc or ~/.bash_profile: umask {self.umask_value}",
            f"System-wide: /etc/profile.d/custom-umask.sh",
            f"Verify: umask (should show {self.umask_value})",
        ]
        return self

    def validate(self):
        from validators.safe_executor import execute_safe
        checks = []
        total_points = 0
        profile_files = []
        if self.target_user == 'root':
            profile_files = ['/root/.bashrc', '/root/.bash_profile']
        else:
            profile_files = [f'/home/{self.target_user}/.bashrc', f'/home/{self.target_user}/.bash_profile']
        found = False
        for pf in profile_files:
            result = execute_safe(['grep', f'umask {self.umask_value}', pf])
            if result.success and result.stdout.strip():
                found = True
                break
        if not found:
            result = execute_safe(['grep', '-r', f'umask {self.umask_value}', '/etc/profile.d/'])
            if result.success and result.stdout.strip():
                found = True
        if found:
            checks.append(ValidationCheck("umask_persistent", True, 10, f"Umask {self.umask_value} configured"))
            total_points = 10
        else:
            checks.append(ValidationCheck("umask_persistent", False, 0, "Umask not found in profile", max_points=10))
        return ValidationResult(self.id, total_points >= 7, total_points, self.points, checks)
