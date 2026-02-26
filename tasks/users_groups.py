"""
User and group management tasks for RHCSA EX200 v10 exam.
12 tasks covering user creation, group management, sudo, password aging,
account locking, shell configuration, service accounts, bulk operations,
and troubleshooting.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. CreateUserWithUIDTask (easy / 6pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class CreateUserWithUIDTask(BaseTask):
    """Create a user with a specific UID and home directory."""

    def __init__(self):
        super().__init__(
            id="user_create_uid_001",
            category="users_groups",
            difficulty="easy",
            points=6,
        )
        self.requires_persistence = True
        self.tags = ["useradd", "uid", "user-management"]
        self.exam_tips = [
            "Always verify with 'id <username>' after creating a user.",
            "The -u flag sets the UID, -m ensures a home directory is created.",
        ]
        self.username = None
        self.uid = None

    def generate(self, **params):
        names = ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "hank"]
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"{random.choice(names)}{suffix}")
        self.uid = params.get("uid", random.randint(2000, 5999))

        self.description = (
            f"Create a new user account with the following specifications:\n"
            f"  - Username: {self.username}\n"
            f"  - UID: {self.uid}\n"
            f"  - Home directory: /home/{self.username} (must be created)\n"
            f"  - Default shell: /bin/bash"
        )

        self.hints = [
            "Use the 'useradd' command with appropriate flags.",
            f"Example: useradd -u {self.uid} -m -s /bin/bash {self.username}",
            "Verify with: id {0}".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: correct UID (2 pts)
        id_result = execute_safe(["id", "-u", self.username])
        actual_uid = id_result.stdout.strip() if id_result.success else ""
        if actual_uid == str(self.uid):
            checks.append(ValidationCheck("correct_uid", True, 2,
                          f"UID is correct: {self.uid}"))
            total += 2
        else:
            checks.append(ValidationCheck("correct_uid", False, 0,
                          f"UID mismatch: expected {self.uid}, got {actual_uid}",
                          max_points=2))

        # Check 3: home directory exists (1 pt)
        home_check = execute_safe(["stat", f"/home/{self.username}"])
        if home_check.success:
            checks.append(ValidationCheck("home_dir", True, 1,
                          f"Home directory /home/{self.username} exists"))
            total += 1
        else:
            checks.append(ValidationCheck("home_dir", False, 0,
                          f"Home directory /home/{self.username} missing",
                          max_points=1))

        # Check 4: shell is /bin/bash (1 pt)
        passwd_result = execute_safe(["getent", "passwd", self.username])
        shell = ""
        if passwd_result.success and passwd_result.stdout:
            fields = passwd_result.stdout.strip().split(":")
            if len(fields) >= 7:
                shell = fields[6]
        if shell == "/bin/bash":
            checks.append(ValidationCheck("shell", True, 1,
                          "Shell is /bin/bash"))
            total += 1
        else:
            checks.append(ValidationCheck("shell", False, 0,
                          f"Shell is '{shell}', expected /bin/bash",
                          max_points=1))

        passed = total >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 2. CreateUserNoLoginTask (easy / 6pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class CreateUserNoLoginTask(BaseTask):
    """Create a user that cannot log in interactively."""

    def __init__(self):
        super().__init__(
            id="user_nologin_002",
            category="users_groups",
            difficulty="easy",
            points=6,
        )
        self.requires_persistence = True
        self.tags = ["useradd", "nologin", "service-account"]
        self.exam_tips = [
            "Use /sbin/nologin as the shell to prevent interactive login.",
            "This is commonly used for application or daemon accounts.",
        ]
        self.username = None
        self.uid = None

    def generate(self, **params):
        prefixes = ["appsvc", "mailsvc", "websvc", "dbsvc", "ftpsvc", "logsvc"]
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"{random.choice(prefixes)}{suffix}")
        self.uid = params.get("uid", random.randint(3000, 4999))

        self.description = (
            f"Create a user account that cannot log in interactively:\n"
            f"  - Username: {self.username}\n"
            f"  - UID: {self.uid}\n"
            f"  - Shell: /sbin/nologin\n"
            f"  - Home directory: /home/{self.username}"
        )

        self.hints = [
            "Use the -s flag to specify the login shell.",
            f"useradd -u {self.uid} -s /sbin/nologin -m {self.username}",
            "Verify: getent passwd {0} | grep nologin".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: correct UID (2 pts)
        uid_result = execute_safe(["id", "-u", self.username])
        actual_uid = uid_result.stdout.strip() if uid_result.success else ""
        if actual_uid == str(self.uid):
            checks.append(ValidationCheck("correct_uid", True, 2,
                          f"UID is correct: {self.uid}"))
            total += 2
        else:
            checks.append(ValidationCheck("correct_uid", False, 0,
                          f"UID mismatch: expected {self.uid}, got {actual_uid}",
                          max_points=2))

        # Check 3: shell is nologin (2 pts)
        passwd = execute_safe(["getent", "passwd", self.username])
        shell = ""
        if passwd.success and passwd.stdout:
            fields = passwd.stdout.strip().split(":")
            if len(fields) >= 7:
                shell = fields[6]
        nologin_shells = ["/sbin/nologin", "/usr/sbin/nologin", "/bin/false"]
        if shell in nologin_shells:
            checks.append(ValidationCheck("nologin_shell", True, 2,
                          f"Shell correctly set to {shell}"))
            total += 2
        else:
            checks.append(ValidationCheck("nologin_shell", False, 0,
                          f"Shell is '{shell}', expected /sbin/nologin",
                          max_points=2))

        passed = total >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 3. ModifyUserGroupsTask (exam / 10pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class ModifyUserGroupsTask(BaseTask):
    """Add a user to one or more supplementary groups."""

    def __init__(self):
        super().__init__(
            id="user_groups_002",
            category="users_groups",
            difficulty="exam",
            points=10,
        )
        self.requires_persistence = True
        self.tags = ["usermod", "groups", "supplementary"]
        self.exam_tips = [
            "Use 'usermod -aG group1,group2 user' to append supplementary groups.",
            "Omitting -a will REPLACE all supplementary groups -- be careful!",
            "Create groups first with 'groupadd' if they do not exist.",
        ]
        self.username = None
        self.groups = None

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"staffuser{suffix}")

        group_pool = ["developers", "sysadmin", "dbadmins", "webteam",
                       "security", "ops", "devops", "qa", "netadmin"]
        num_groups = random.randint(2, 3)
        self.groups = params.get("groups", random.sample(group_pool, num_groups))

        groups_str = ", ".join(self.groups)
        self.description = (
            f"Add user '{self.username}' to the following supplementary groups:\n"
            f"  - Groups: {groups_str}\n\n"
            f"  Notes:\n"
            f"  - Create the groups first if they do not already exist.\n"
            f"  - The user must already exist (create if needed).\n"
            f"  - Do NOT remove any existing supplementary group memberships."
        )

        self.hints = [
            "Create missing groups with 'groupadd <groupname>'.",
            "Add supplementary groups: usermod -aG group1,group2 <username>",
            "The -a flag appends (does not replace) supplementary groups.",
            "Verify: groups {0} or id {0}".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: each group exists and user is a member (remaining pts)
        groups_result = execute_safe(["id", "-Gn", self.username])
        actual_groups = set()
        if groups_result.success and groups_result.stdout:
            actual_groups = set(groups_result.stdout.strip().split())

        pts_per_group = 8 // len(self.groups)
        remainder = 8 - (pts_per_group * len(self.groups))

        for i, grp in enumerate(self.groups):
            grp_pts = pts_per_group + (1 if i < remainder else 0)

            # Verify group exists
            grp_check = execute_safe(["getent", "group", grp])
            if not grp_check.success:
                checks.append(ValidationCheck(f"group_{grp}", False, 0,
                              f"Group '{grp}' does not exist", max_points=grp_pts))
                continue

            # Verify membership
            if grp in actual_groups:
                checks.append(ValidationCheck(f"member_{grp}", True, grp_pts,
                              f"User is a member of '{grp}'"))
                total += grp_pts
            else:
                checks.append(ValidationCheck(f"member_{grp}", False, 0,
                              f"User is NOT a member of '{grp}'",
                              max_points=grp_pts))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 4. SetPasswordAgingTask (exam / 12pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class SetPasswordAgingTask(BaseTask):
    """Configure password aging policies for a user via chage."""

    def __init__(self):
        super().__init__(
            id="passwd_aging_002",
            category="users_groups",
            difficulty="exam",
            points=12,
        )
        self.requires_persistence = True
        self.tags = ["chage", "password-aging", "security"]
        self.exam_tips = [
            "Use 'chage' to set password aging: -M max, -m min, -W warn, -I inactive.",
            "Force password change on next login: chage -d 0 <username>.",
            "Verify with: chage -l <username>.",
        ]
        self.username = None
        self.max_days = None
        self.min_days = None
        self.warn_days = None
        self.inactive_days = None
        self.force_change = False

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"ageuser{suffix}")
        self.max_days = params.get("max_days", random.choice([30, 60, 90, 120, 180]))
        self.min_days = params.get("min_days", random.choice([0, 1, 3, 7]))
        self.warn_days = params.get("warn_days", random.choice([7, 10, 14]))
        self.inactive_days = params.get("inactive_days", random.choice([7, 14, 30]))
        self.force_change = params.get("force_change", random.choice([True, False]))

        force_text = (
            "\n  - The user must change their password on next login"
            if self.force_change else ""
        )

        self.description = (
            f"Configure password aging for user '{self.username}':\n"
            f"  - Maximum days between password changes: {self.max_days}\n"
            f"  - Minimum days between password changes: {self.min_days}\n"
            f"  - Warning days before password expiration: {self.warn_days}\n"
            f"  - Days of inactivity after expiration before lock: {self.inactive_days}"
            f"{force_text}\n\n"
            f"  Note: create the user first if it does not exist."
        )

        self.hints = [
            f"chage -M {self.max_days} -m {self.min_days} -W {self.warn_days} "
            f"-I {self.inactive_days} {self.username}",
            "To force password change on next login: chage -d 0 <username>",
            "Verify with: chage -l <username>",
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Get chage output
        chage_result = execute_safe(["chage", "-l", self.username])
        if not chage_result.success:
            checks.append(ValidationCheck("chage_read", False, 0,
                          f"Could not read password aging info: {chage_result.stderr}",
                          max_points=10))
            return ValidationResult(self.id, False, total, self.points, checks)

        output = chage_result.stdout

        def _check_chage_field(field_label, expected_val, check_name, pts):
            nonlocal total
            for line in output.splitlines():
                if field_label in line:
                    if str(expected_val) in line.split(":")[-1]:
                        checks.append(ValidationCheck(check_name, True, pts,
                                      f"{field_label}: {expected_val}"))
                        total += pts
                        return
                    else:
                        actual_val = line.split(":")[-1].strip()
                        checks.append(ValidationCheck(check_name, False, 0,
                                      f"{field_label}: expected {expected_val}, "
                                      f"got {actual_val}", max_points=pts))
                        return
            checks.append(ValidationCheck(check_name, False, 0,
                          f"Could not find '{field_label}' in chage output",
                          max_points=pts))

        # Check 2: max days (3 pts)
        _check_chage_field("Maximum number of days between password change",
                           self.max_days, "max_days", 3)

        # Check 3: min days (2 pts)
        _check_chage_field("Minimum number of days between password change",
                           self.min_days, "min_days", 2)

        # Check 4: warn days (2 pts)
        _check_chage_field("Number of days of warning before password expires",
                           self.warn_days, "warn_days", 2)

        # Check 5: inactive days (2 pts)
        _check_chage_field("Number of days of inactivity",
                           self.inactive_days, "inactive_days", 2)

        # Check 6: force change on next login (1 pt, only if required)
        if self.force_change:
            force_found = False
            for line in output.splitlines():
                if "Last password change" in line:
                    if "password must be changed" in line.lower():
                        force_found = True
                        break
                # Some implementations show "Jan 01, 1970" when forced
                if "Last password change" in line and "1970" in line:
                    force_found = True
                    break
            if force_found:
                checks.append(ValidationCheck("force_change", True, 1,
                              "Password change required on next login"))
                total += 1
            else:
                checks.append(ValidationCheck("force_change", False, 0,
                              "Password change on next login not configured",
                              max_points=1))

        passed = total >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 5. CreateGroupTask (easy / 5pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class CreateGroupTask(BaseTask):
    """Create a group with a specific GID."""

    def __init__(self):
        super().__init__(
            id="group_create_002",
            category="users_groups",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = True
        self.tags = ["groupadd", "gid", "group-management"]
        self.exam_tips = [
            "Use 'groupadd -g <GID> <groupname>' to create a group with a specific GID.",
            "Verify with: getent group <groupname>",
        ]
        self.groupname = None
        self.gid = None

    def generate(self, **params):
        prefixes = ["devteam", "qagroup", "opsgroup", "infrateam",
                     "secteam", "datateam", "cloudops"]
        suffix = random.randint(10, 99)
        self.groupname = params.get("groupname", f"{random.choice(prefixes)}{suffix}")
        self.gid = params.get("gid", random.randint(5000, 7999))

        self.description = (
            f"Create a new group with the following specifications:\n"
            f"  - Group name: {self.groupname}\n"
            f"  - GID: {self.gid}"
        )

        self.hints = [
            f"groupadd -g {self.gid} {self.groupname}",
            "Verify with: getent group {0}".format(self.groupname),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: group exists (3 pts)
        result = execute_safe(["getent", "group", self.groupname])
        if result.success:
            checks.append(ValidationCheck("group_exists", True, 3,
                          f"Group '{self.groupname}' exists"))
            total += 3
        else:
            checks.append(ValidationCheck("group_exists", False, 0,
                          f"Group '{self.groupname}' does not exist",
                          max_points=3))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: correct GID (2 pts)
        fields = result.stdout.strip().split(":")
        actual_gid = fields[2] if len(fields) >= 3 else ""
        if actual_gid == str(self.gid):
            checks.append(ValidationCheck("correct_gid", True, 2,
                          f"GID is correct: {self.gid}"))
            total += 2
        else:
            checks.append(ValidationCheck("correct_gid", False, 0,
                          f"GID mismatch: expected {self.gid}, got {actual_gid}",
                          max_points=2))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 6. ConfigureSudoTask (exam / 12pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class ConfigureSudoTask(BaseTask):
    """Configure sudo access via /etc/sudoers.d/ for a user."""

    def __init__(self):
        super().__init__(
            id="sudo_002",
            category="users_groups",
            difficulty="exam",
            points=12,
        )
        self.requires_persistence = True
        self.tags = ["sudo", "sudoers", "privilege-escalation"]
        self.exam_tips = [
            "Always place custom sudo rules in /etc/sudoers.d/ -- never edit "
            "/etc/sudoers directly on the exam.",
            "File permissions must be 0440 or 0440 for sudoers drop-in files.",
            "Validate syntax with: visudo -cf /etc/sudoers.d/<file>",
        ]
        self.username = None
        self.nopasswd = True
        self.allowed_cmds = None

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"operator{suffix}")
        self.nopasswd = params.get("nopasswd", random.choice([True, False]))

        cmd_sets = [
            "ALL",
            "/usr/bin/systemctl, /usr/bin/journalctl",
            "/usr/sbin/useradd, /usr/sbin/usermod, /usr/sbin/userdel",
            "/usr/bin/mount, /usr/bin/umount",
        ]
        self.allowed_cmds = params.get("commands", random.choice(cmd_sets))

        nopasswd_str = "NOPASSWD: " if self.nopasswd else ""
        passwd_note = " without a password" if self.nopasswd else " (password required)"

        self.description = (
            f"Configure sudo access for user '{self.username}':\n"
            f"  - Allowed commands: {self.allowed_cmds}\n"
            f"  - The user should be able to run these commands as root"
            f"{passwd_note}\n"
            f"  - Configuration must be placed in /etc/sudoers.d/{self.username}\n"
            f"  - File must have correct permissions (0440)\n\n"
            f"  Expected sudoers line:\n"
            f"    {self.username} ALL=(ALL) {nopasswd_str}{self.allowed_cmds}"
        )

        self.hints = [
            f"Create /etc/sudoers.d/{self.username} with the rule.",
            f"Content: {self.username} ALL=(ALL) {nopasswd_str}{self.allowed_cmds}",
            "Set permissions: chmod 0440 /etc/sudoers.d/{0}".format(self.username),
            "Validate: visudo -cf /etc/sudoers.d/{0}".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        user_check = execute_safe(["id", self.username])
        if user_check.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: sudoers file exists (3 pts)
        sudo_file = f"/etc/sudoers.d/{self.username}"
        stat_result = execute_safe(["stat", sudo_file])
        if stat_result.success:
            checks.append(ValidationCheck("sudo_file_exists", True, 3,
                          f"Sudoers file exists: {sudo_file}"))
            total += 3
        else:
            checks.append(ValidationCheck("sudo_file_exists", False, 0,
                          f"Sudoers file not found: {sudo_file}", max_points=3))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 3: file permissions are 0440 (2 pts)
        perm_result = execute_safe(["stat", "-c", "%a", sudo_file])
        actual_perms = perm_result.stdout.strip() if perm_result.success else ""
        if actual_perms in ("440", "0440"):
            checks.append(ValidationCheck("sudo_perms", True, 2,
                          "File permissions are 0440"))
            total += 2
        else:
            checks.append(ValidationCheck("sudo_perms", False, 0,
                          f"Permissions are {actual_perms}, expected 440",
                          max_points=2))

        # Check 4: file contains correct rule (3 pts)
        cat_result = execute_safe(["cat", f"/etc/sudoers.d/{self.username}"])
        if cat_result.success:
            content = cat_result.stdout
            nopasswd_str = "NOPASSWD:" if self.nopasswd else ""
            user_found = self.username in content
            cmd_found = self.allowed_cmds in content or (
                self.allowed_cmds == "ALL" and "ALL" in content)
            nopasswd_ok = True
            if self.nopasswd:
                nopasswd_ok = "NOPASSWD" in content
            elif not self.nopasswd:
                nopasswd_ok = "NOPASSWD" not in content

            if user_found and cmd_found and nopasswd_ok:
                checks.append(ValidationCheck("sudo_rule", True, 3,
                              "Sudo rule is correct"))
                total += 3
            elif user_found and cmd_found:
                checks.append(ValidationCheck("sudo_rule", True, 2,
                              "Sudo rule partially correct (NOPASSWD mismatch)"))
                total += 2
            else:
                checks.append(ValidationCheck("sudo_rule", False, 0,
                              "Sudo rule content is incorrect", max_points=3))
        else:
            checks.append(ValidationCheck("sudo_rule", False, 0,
                          f"Cannot read sudoers file", max_points=3))

        # Check 5: sudo -l works for user (2 pts)
        sudo_check = execute_safe(["sudo", "-l", "-U", self.username])
        if sudo_check.success and "not allowed" not in sudo_check.stdout.lower():
            checks.append(ValidationCheck("sudo_access", True, 2,
                          "Sudo access verified"))
            total += 2
        else:
            checks.append(ValidationCheck("sudo_access", False, 0,
                          "Sudo access verification failed", max_points=2))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 7. LockUnlockUserTask (medium / 8pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class LockUnlockUserTask(BaseTask):
    """Lock or unlock a user account."""

    def __init__(self):
        super().__init__(
            id="user_lock_002",
            category="users_groups",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = False
        self.tags = ["usermod", "passwd", "account-lock"]
        self.exam_tips = [
            "'usermod -L' locks, 'usermod -U' unlocks.",
            "'passwd -S' shows status: LK=locked, PS=password set, NP=no password.",
        ]
        self.username = None
        self.action = None

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"locktest{suffix}")
        self.action = params.get("action", random.choice(["lock", "unlock"]))

        if self.action == "lock":
            self.description = (
                f"Lock the user account '{self.username}':\n"
                f"  - Prevent the user from logging in via password\n"
                f"  - The account must still exist (do NOT delete it)\n"
                f"  - Ensure the account is locked"
            )
        else:
            self.description = (
                f"Unlock the user account '{self.username}':\n"
                f"  - The account is currently locked\n"
                f"  - Re-enable password-based authentication\n"
                f"  - Ensure the account is fully unlocked"
            )

        self.hints = [
            "Lock:   usermod -L <username>  or  passwd -l <username>",
            "Unlock: usermod -U <username>  or  passwd -u <username>",
            "Verify: passwd -S <username>  (LK = locked, PS = password set)",
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (3 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 3,
                          f"User '{self.username}' exists"))
            total += 3
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=3))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: lock status (5 pts)
        status_result = execute_safe(["passwd", "-S", self.username])
        if not status_result.success:
            checks.append(ValidationCheck("lock_status", False, 0,
                          f"Cannot check lock status: {status_result.stderr}",
                          max_points=5))
            return ValidationResult(self.id, False, total, self.points, checks)

        output = status_result.stdout.strip()
        # Format: username LK/PS/NP ...
        is_locked = " LK " in output or " L " in output

        if self.action == "lock":
            if is_locked:
                checks.append(ValidationCheck("account_locked", True, 5,
                              "Account is correctly locked"))
                total += 5
            else:
                checks.append(ValidationCheck("account_locked", False, 0,
                              "Account is NOT locked (expected locked)",
                              max_points=5))
        else:
            if not is_locked:
                checks.append(ValidationCheck("account_unlocked", True, 5,
                              "Account is correctly unlocked"))
                total += 5
            else:
                checks.append(ValidationCheck("account_unlocked", False, 0,
                              "Account is still locked (expected unlocked)",
                              max_points=5))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 8. DeleteUserTask (easy / 5pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class DeleteUserTask(BaseTask):
    """Delete a user account and optionally remove its home directory."""

    def __init__(self):
        super().__init__(
            id="user_delete_002",
            category="users_groups",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = False
        self.tags = ["userdel", "user-management"]
        self.exam_tips = [
            "Use 'userdel -r' to also remove the home directory and mail spool.",
            "Without -r the home directory remains on disk.",
        ]
        self.username = None
        self.remove_home = True

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"removeuser{suffix}")
        self.remove_home = params.get("remove_home", random.choice([True, False]))
        home_action = "Remove" if self.remove_home else "Keep"

        self.description = (
            f"Delete the user account '{self.username}':\n"
            f"  - {home_action} the home directory /home/{self.username}\n"
            f"  - The user should no longer exist on the system"
        )

        self.hints = [
            f"userdel {'-r ' if self.remove_home else ''}{self.username}",
            f"Verify: id {self.username} (should show 'no such user')",
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user must NOT exist (3 pts)
        result = execute_safe(["id", self.username])
        if not result.success:
            checks.append(ValidationCheck("user_deleted", True, 3,
                          f"User '{self.username}' has been deleted"))
            total += 3
        else:
            checks.append(ValidationCheck("user_deleted", False, 0,
                          f"User '{self.username}' still exists", max_points=3))

        # Check 2: home directory status (2 pts)
        home_check = execute_safe(["stat", f"/home/{self.username}"])
        if self.remove_home:
            if not home_check.success:
                checks.append(ValidationCheck("home_removed", True, 2,
                              "Home directory has been removed"))
                total += 2
            else:
                checks.append(ValidationCheck("home_removed", False, 0,
                              "Home directory still exists", max_points=2))
        else:
            if home_check.success:
                checks.append(ValidationCheck("home_kept", True, 2,
                              "Home directory correctly preserved"))
                total += 2
            else:
                checks.append(ValidationCheck("home_kept", False, 0,
                              "Home directory was removed (should have been kept)",
                              max_points=2))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 9. SetDefaultShellTask (easy / 5pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class SetDefaultShellTask(BaseTask):
    """Change the default login shell for a user."""

    def __init__(self):
        super().__init__(
            id="user_shell_002",
            category="users_groups",
            difficulty="easy",
            points=5,
        )
        self.requires_persistence = True
        self.tags = ["usermod", "chsh", "shell"]
        self.exam_tips = [
            "Use 'usermod -s /path/to/shell <username>' to change the shell.",
            "Alternatively use 'chsh -s /path/to/shell <username>'.",
        ]
        self.username = None
        self.shell = None

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"shelluser{suffix}")
        shells = ["/bin/bash", "/bin/sh", "/bin/zsh", "/bin/tcsh",
                  "/sbin/nologin", "/bin/false"]
        self.shell = params.get("shell", random.choice(shells))

        self.description = (
            f"Change the default login shell for user '{self.username}':\n"
            f"  - New shell: {self.shell}\n"
            f"  - Create the user first if it does not exist."
        )

        self.hints = [
            f"usermod -s {self.shell} {self.username}",
            "Verify: getent passwd {0}".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Check 2: correct shell (3 pts)
        passwd = execute_safe(["getent", "passwd", self.username])
        shell = ""
        if passwd.success and passwd.stdout:
            fields = passwd.stdout.strip().split(":")
            if len(fields) >= 7:
                shell = fields[6]
        if shell == self.shell:
            checks.append(ValidationCheck("correct_shell", True, 3,
                          f"Shell is correct: {self.shell}"))
            total += 3
        else:
            checks.append(ValidationCheck("correct_shell", False, 0,
                          f"Shell is '{shell}', expected {self.shell}",
                          max_points=3))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 10. CreateServiceAccountTask (medium / 8pts) [PERSIST]
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class CreateServiceAccountTask(BaseTask):
    """Create a system (service) account with no home directory."""

    def __init__(self):
        super().__init__(
            id="svc_account_001",
            category="users_groups",
            difficulty="medium",
            points=8,
        )
        self.requires_persistence = True
        self.tags = ["useradd", "system-account", "service"]
        self.exam_tips = [
            "Use 'useradd -r' to create a system account (UID below 1000).",
            "Combine with '-s /sbin/nologin' and '-M' (no home directory).",
        ]
        self.username = None
        self.comment = None

    def generate(self, **params):
        services = ["nginx", "redis", "tomcat", "grafana", "prometheus",
                     "elasticsearch", "kafka", "rabbitmq", "consul", "vault"]
        svc = random.choice(services)
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"{svc}svc{suffix}")
        self.comment = params.get("comment",
                                  f"{svc.capitalize()} Service Account")

        self.description = (
            f"Create a system (service) account:\n"
            f"  - Username: {self.username}\n"
            f"  - Must be a system account (UID in the system range, below 1000)\n"
            f"  - No home directory should be created\n"
            f"  - Shell: /sbin/nologin\n"
            f"  - GECOS / comment: \"{self.comment}\""
        )

        self.hints = [
            f"useradd -r -M -s /sbin/nologin -c \"{self.comment}\" {self.username}",
            "The -r flag creates a system account with UID < 1000.",
            "The -M flag suppresses home directory creation.",
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        # Parse passwd entry
        passwd = execute_safe(["getent", "passwd", self.username])
        fields = []
        if passwd.success and passwd.stdout:
            fields = passwd.stdout.strip().split(":")

        # Check 2: UID < 1000 (system account) (2 pts)
        uid_result = execute_safe(["id", "-u", self.username])
        actual_uid = int(uid_result.stdout.strip()) if uid_result.success else 9999
        if actual_uid < 1000:
            checks.append(ValidationCheck("system_uid", True, 2,
                          f"UID {actual_uid} is in system range (< 1000)"))
            total += 2
        else:
            checks.append(ValidationCheck("system_uid", False, 0,
                          f"UID {actual_uid} is not in system range (expected < 1000)",
                          max_points=2))

        # Check 3: no home directory (2 pts)
        home_dir = fields[5] if len(fields) > 5 else f"/home/{self.username}"
        home_check = execute_safe(["stat", home_dir])
        if not home_check.success:
            checks.append(ValidationCheck("no_home", True, 2,
                          "No home directory exists (correct)"))
            total += 2
        else:
            checks.append(ValidationCheck("no_home", False, 0,
                          f"Home directory {home_dir} exists (should not)",
                          max_points=2))

        # Check 4: shell is nologin (2 pts)
        shell = fields[6] if len(fields) > 6 else ""
        nologin_shells = ["/sbin/nologin", "/usr/sbin/nologin", "/bin/false"]
        if shell in nologin_shells:
            checks.append(ValidationCheck("nologin", True, 2,
                          f"Shell is {shell} (no login)"))
            total += 2
        else:
            checks.append(ValidationCheck("nologin", False, 0,
                          f"Shell is '{shell}', expected /sbin/nologin",
                          max_points=2))

        passed = total >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 11. BulkUserCreationTask (hard / 15pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class BulkUserCreationTask(BaseTask):
    """Create multiple users from a specification."""

    def __init__(self):
        super().__init__(
            id="bulk_users_001",
            category="users_groups",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = False
        self.tags = ["useradd", "scripting", "bulk"]
        self.exam_tips = [
            "Write a small bash for-loop or use a script to create users quickly.",
            "Double-check each user with 'id <username>' after creation.",
        ]
        self.users = []
        self.common_group = None

    def generate(self, **params):
        first_names = ["anna", "ben", "clara", "dan", "ella",
                        "finn", "gina", "hugo", "iris", "jake"]
        num_users = params.get("count", random.randint(3, 5))
        selected = random.sample(first_names, num_users)

        group_pool = ["engineering", "marketing", "finance", "support", "research"]
        self.common_group = params.get("group", random.choice(group_pool))

        shells = ["/bin/bash", "/bin/sh"]
        self.users = []
        base_uid = random.randint(3000, 4000)
        for i, name in enumerate(selected):
            self.users.append({
                "username": f"{name}_{self.common_group[:3]}",
                "uid": base_uid + i,
                "shell": random.choice(shells),
            })

        user_lines = "\n".join(
            f"  - {u['username']} (UID: {u['uid']}, shell: {u['shell']})"
            for u in self.users
        )

        self.description = (
            f"Create the following users and add them all to the group "
            f"'{self.common_group}':\n{user_lines}\n\n"
            f"  Requirements:\n"
            f"  - Create the group '{self.common_group}' if it does not exist.\n"
            f"  - Each user must have the specified UID and shell.\n"
            f"  - Each user must be a member of '{self.common_group}' "
            f"(supplementary group).\n"
            f"  - Each user must have a home directory under /home/."
        )

        self.hints = [
            f"groupadd {self.common_group}   # create group first",
            "Then for each user: useradd -u <UID> -s <SHELL> "
            f"-G {self.common_group} -m <USERNAME>",
            "Consider a for-loop in bash to speed things up.",
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: group exists (2 pts)
        grp_result = execute_safe(["getent", "group", self.common_group])
        if grp_result.success:
            checks.append(ValidationCheck("group_exists", True, 2,
                          f"Group '{self.common_group}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("group_exists", False, 0,
                          f"Group '{self.common_group}' does not exist",
                          max_points=2))

        # Points per user
        remaining_pts = 13
        pts_per_user = remaining_pts // len(self.users)
        leftover = remaining_pts - (pts_per_user * len(self.users))

        for i, user_spec in enumerate(self.users):
            uname = user_spec["username"]
            expected_uid = str(user_spec["uid"])
            expected_shell = user_spec["shell"]
            user_pts = pts_per_user + (1 if i < leftover else 0)

            # Does user exist?
            id_result = execute_safe(["id", uname])
            if not id_result.success:
                checks.append(ValidationCheck(f"user_{uname}", False, 0,
                              f"User '{uname}' does not exist",
                              max_points=user_pts))
                continue

            earned = 0
            sub_max = user_pts
            issues = []

            # UID
            uid_result = execute_safe(["id", "-u", uname])
            actual_uid = uid_result.stdout.strip() if uid_result.success else ""
            if actual_uid != expected_uid:
                issues.append(f"UID {actual_uid} != {expected_uid}")
            else:
                earned += 1

            # Shell
            passwd = execute_safe(["getent", "passwd", uname])
            actual_shell = ""
            if passwd.success:
                f = passwd.stdout.strip().split(":")
                actual_shell = f[6] if len(f) > 6 else ""
            if actual_shell != expected_shell:
                issues.append(f"shell {actual_shell} != {expected_shell}")
            else:
                earned += 1

            # Group membership
            groups_result = execute_safe(["id", "-Gn", uname])
            actual_groups = set()
            if groups_result.success:
                actual_groups = set(groups_result.stdout.strip().split())
            if self.common_group in actual_groups:
                earned += 1
            else:
                issues.append(f"not in group {self.common_group}")

            # Scale earned to user_pts
            score = round(user_pts * earned / 3)
            total += score

            if issues:
                checks.append(ValidationCheck(
                    f"user_{uname}", score > 0, score,
                    f"User '{uname}': {'; '.join(issues)}",
                    max_points=user_pts))
            else:
                checks.append(ValidationCheck(
                    f"user_{uname}", True, score,
                    f"User '{uname}' configured correctly"))

        passed = total >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total, self.points, checks)


# ---------------------------------------------------------------------------
# 12. TroubleshootUserAccessTask (hard / 15pts)
# ---------------------------------------------------------------------------
@TaskRegistry.register("users_groups")
class TroubleshootUserAccessTask(BaseTask):
    """Diagnose and fix why a user cannot log in."""

    def __init__(self):
        super().__init__(
            id="troubleshoot_user_001",
            category="users_groups",
            difficulty="hard",
            points=15,
        )
        self.requires_persistence = False
        self.tags = ["troubleshooting", "login", "passwd", "shadow"]
        self.exam_tips = [
            "Check: account locked? shell set to /sbin/nologin? password expired? "
            "account expired?",
            "Use 'passwd -S', 'chage -l', 'getent passwd' to investigate.",
        ]
        self.username = None
        self.problem = None
        self.expected_shell = "/bin/bash"

    def generate(self, **params):
        suffix = random.randint(10, 99)
        self.username = params.get("username", f"troubleuser{suffix}")

        problems = [
            {
                "type": "locked",
                "desc_extra": "The user's account appears to be locked.",
                "fix": "Unlock the account and ensure the user can log in.",
            },
            {
                "type": "nologin_shell",
                "desc_extra": "The user's shell has been changed to /sbin/nologin.",
                "fix": "Set the shell back to /bin/bash.",
            },
            {
                "type": "expired_account",
                "desc_extra": "The user's account has expired.",
                "fix": "Remove the account expiration (set to never expire).",
            },
            {
                "type": "expired_password",
                "desc_extra": "The user's password has expired and must be renewed.",
                "fix": "Reset password aging so the password is not expired. "
                       "Set maximum days to 90.",
            },
        ]

        self.problem = params.get("problem", random.choice(problems))

        self.description = (
            f"User '{self.username}' reports they cannot log in to the system.\n"
            f"  Symptom: {self.problem['desc_extra']}\n\n"
            f"  Task: {self.problem['fix']}\n\n"
            f"  After fixing, the user should be able to log in with:\n"
            f"  - An unlocked account\n"
            f"  - Shell set to /bin/bash\n"
            f"  - No account or password expiration blocking access"
        )

        self.hints = [
            "Investigate: passwd -S {0}".format(self.username),
            "Investigate: chage -l {0}".format(self.username),
            "Investigate: getent passwd {0}".format(self.username),
            "Unlock: usermod -U {0}".format(self.username),
            "Change shell: usermod -s /bin/bash {0}".format(self.username),
            "Remove expiration: chage -E -1 {0}".format(self.username),
            "Fix password aging: chage -M 90 {0}".format(self.username),
        ]
        return self

    def validate(self):
        checks = []
        total = 0

        # Check 1: user exists (2 pts)
        result = execute_safe(["id", self.username])
        if result.success:
            checks.append(ValidationCheck("user_exists", True, 2,
                          f"User '{self.username}' exists"))
            total += 2
        else:
            checks.append(ValidationCheck("user_exists", False, 0,
                          f"User '{self.username}' does not exist", max_points=2))
            return ValidationResult(self.id, False, total, self.points, checks)

        problem_type = self.problem["type"]

        # Check 2: account is not locked (4 pts)
        status = execute_safe(["passwd", "-S", self.username])
        is_locked = False
        if status.success:
            out = status.stdout.strip()
            is_locked = " LK " in out or " L " in out
        if not is_locked:
            checks.append(ValidationCheck("not_locked", True, 4,
                          "Account is not locked"))
            total += 4
        else:
            checks.append(ValidationCheck("not_locked", False, 0,
                          "Account is still locked", max_points=4))

        # Check 3: shell is /bin/bash (3 pts)
        passwd = execute_safe(["getent", "passwd", self.username])
        shell = ""
        if passwd.success:
            fields = passwd.stdout.strip().split(":")
            shell = fields[6] if len(fields) > 6 else ""
        if shell == "/bin/bash":
            checks.append(ValidationCheck("shell_bash", True, 3,
                          "Shell is /bin/bash"))
            total += 3
        else:
            checks.append(ValidationCheck("shell_bash", False, 0,
                          f"Shell is '{shell}', expected /bin/bash",
                          max_points=3))

        # Check 4: account not expired (3 pts)
        chage_result = execute_safe(["chage", "-l", self.username])
        account_expired = False
        if chage_result.success:
            for line in chage_result.stdout.splitlines():
                if "Account expires" in line:
                    value = line.split(":")[-1].strip().lower()
                    if value != "never" and value != "":
                        # Check if date is in the past
                        import datetime
                        try:
                            # Try common formats
                            for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"]:
                                try:
                                    exp_date = datetime.datetime.strptime(
                                        value.strip(), fmt).date()
                                    if exp_date < datetime.date.today():
                                        account_expired = True
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            pass

        if not account_expired:
            checks.append(ValidationCheck("not_expired", True, 3,
                          "Account is not expired"))
            total += 3
        else:
            checks.append(ValidationCheck("not_expired", False, 0,
                          "Account is expired", max_points=3))

        # Check 5: password not expired (3 pts)
        password_ok = True
        if chage_result.success:
            output = chage_result.stdout.lower()
            if "password must be changed" in output:
                password_ok = False
            for line in chage_result.stdout.splitlines():
                if "Last password change" in line and "1970" in line:
                    password_ok = False
                    break
        if password_ok:
            checks.append(ValidationCheck("password_ok", True, 3,
                          "Password is not in forced-change state"))
            total += 3
        else:
            checks.append(ValidationCheck("password_ok", False, 0,
                          "Password appears expired or forced-change",
                          max_points=3))

        passed = total >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total, self.points, checks)
