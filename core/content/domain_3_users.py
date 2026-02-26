"""
Domain 3: Users, Groups & Permissions
Categories: users_groups, permissions
"""

CONTENT = {
    "users_groups": {
        "name": "Users & Groups Management",
        "explanation": """
User and group management is fundamental to Linux system administration.
You'll need to create users with specific UIDs, assign them to groups,
configure sudo access, and manage user properties. The exam tests your
ability to use useradd, usermod, groupadd, and sudo configuration.

KEY FILES TO KNOW:
  /etc/passwd    - User account info (username:x:UID:GID:comment:home:shell)
  /etc/shadow    - Encrypted passwords and aging info
  /etc/group     - Group definitions (groupname:x:GID:members)
  /etc/gshadow   - Group passwords
  /etc/login.defs - Default settings for new users
  /etc/skel/     - Template files copied to new home directories
  /etc/sudoers.d/ - Drop-in sudo configuration files

UID RANGES (RHEL defaults):
  0         - root
  1-999     - System accounts
  1000+     - Regular users
        """,
        "commands": [
            {
                "name": "Create User with UID",
                "syntax": "useradd -u <UID> -m <username>",
                "example": "useradd -u 2500 -m -c 'Exam User' examuser",
                "flags": {
                    "-u": "Specify user ID (UID)",
                    "-m": "Create home directory",
                    "-M": "Do NOT create home directory",
                    "-g": "Primary group (name or GID)",
                    "-G": "Supplementary groups (comma-separated)",
                    "-s": "Login shell",
                    "-c": "Comment/GECOS field (full name)",
                    "-d": "Home directory path",
                    "-e": "Account expiration date (YYYY-MM-DD)",
                    "-r": "Create system account (UID < 1000)",
                },
            },
            {
                "name": "Modify User",
                "syntax": "usermod [OPTIONS] <username>",
                "example": "usermod -aG wheel,developers examuser",
                "flags": {
                    "-aG": "Add to supplementary groups (APPEND - critical!)",
                    "-G": "Set supplementary groups (REPLACES all existing!)",
                    "-L": "Lock account (adds ! to password in shadow)",
                    "-U": "Unlock account",
                    "-s": "Change login shell",
                    "-l": "Change login name",
                    "-d": "Change home directory",
                    "-m": "Move home directory contents (use with -d)",
                    "-e": "Set account expiration date",
                },
            },
            {
                "name": "Delete User",
                "syntax": "userdel [-r] <username>",
                "example": "userdel -r olduser",
                "flags": {
                    "userdel user": "Delete user (keeps home directory)",
                    "-r": "Remove home directory and mail spool",
                    "-f": "Force deletion even if user logged in",
                },
            },
            {
                "name": "Set Password",
                "syntax": "passwd <username>",
                "example": "passwd examuser",
                "flags": {
                    "passwd": "Change own password",
                    "passwd user": "Change another user's password (root)",
                    "--stdin": "Read password from stdin (scripting)",
                    "-l": "Lock account",
                    "-u": "Unlock account",
                    "-d": "Delete password (passwordless)",
                    "-e": "Expire password (force change on next login)",
                },
            },
            {
                "name": "Password Aging (chage)",
                "syntax": "chage [OPTIONS] <username>",
                "example": "chage -M 90 -W 7 examuser",
                "flags": {
                    "-l": "List password aging info",
                    "-d 0": "Force password change on next login",
                    "-M": "Maximum days between password changes",
                    "-m": "Minimum days between password changes",
                    "-W": "Warning days before expiration",
                    "-I": "Inactive days after password expires",
                    "-E": "Account expiration date (YYYY-MM-DD)",
                },
            },
            {
                "name": "Configure Sudo Access",
                "syntax": "echo 'user ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/user",
                "example": "echo 'examuser ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/examuser && chmod 0440 /etc/sudoers.d/examuser",
                "flags": {
                    "ALL=(ALL)": "Run as any user on any host",
                    "NOPASSWD:": "No password required",
                    "ALL": "Can run any command",
                    "%groupname": "Apply to group (e.g., %wheel)",
                    "visudo": "Safe way to edit sudoers (checks syntax)",
                },
            },
            {
                "name": "Create Group",
                "syntax": "groupadd -g <GID> <groupname>",
                "example": "groupadd -g 3000 developers",
                "flags": {
                    "-g": "Specify group ID (GID)",
                    "-r": "Create system group (GID < 1000)",
                },
            },
            {
                "name": "Modify/Delete Group",
                "syntax": "groupmod / groupdel",
                "example": "groupmod -n newname oldname",
                "flags": {
                    "groupmod -n": "Rename group",
                    "groupmod -g": "Change GID",
                    "groupdel": "Delete group (must have no users)",
                },
            },
            {
                "name": "View User/Group Info",
                "syntax": "id / groups / getent",
                "example": "id examuser && groups examuser",
                "flags": {
                    "id user": "Show UID, GID, and groups",
                    "groups user": "Show group memberships",
                    "getent passwd user": "Query user from all sources",
                    "getent group grp": "Query group from all sources",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting -m flag -> No home directory created",
            "Using -G without -a -> REMOVES user from ALL existing groups (critical!)",
            "Sudo file wrong permissions (must be 0440 or 0400)",
            "Creating sudo file in /etc/sudoers instead of /etc/sudoers.d/",
            "Not using visudo -> Syntax errors can break ALL sudo access",
            "Forgetting to run 'chage -d 0' when password change on login is required",
            "Using userdel without -r leaves orphaned files",
            "Not verifying with 'id username' after user creation",
        ],
        "exam_tricks": [
            "Exam may specify exact UID - don't let system auto-assign",
            "Multiple supplementary groups - must add ALL of them",
            "Persistent sudo access - must survive reboot (use /etc/sudoers.d/)",
            "User must exist but account might need to be locked (usermod -L)",
            "'Password must change on next login' = chage -d 0 username",
            "Account expiry vs password expiry - they're different!",
            "Always verify with 'id username' and 'sudo -l -U username'",
        ],
    },
    "permissions": {
        "name": "File Permissions & ACLs",
        "explanation": """
Linux permissions control file access using owner, group, and other.
Special permissions (setuid, setgid, sticky) add advanced functionality.
ACLs (Access Control Lists) provide fine-grained access control beyond
traditional permissions. The exam tests chmod, chown, setfacl, and
understanding of permission inheritance and special bits.

PERMISSION STRUCTURE:
  -rwxrwxrwx = type + owner + group + others

  Type: - (file), d (directory), l (link), b (block), c (char)

NUMERIC VALUES:
  r = 4 (read)
  w = 2 (write)
  x = 1 (execute)

  Example: rwxr-xr-- = 754
    Owner: rwx = 4+2+1 = 7
    Group: r-x = 4+0+1 = 5
    Others: r-- = 4+0+0 = 4

DIRECTORY PERMISSIONS:
  r = list contents (ls)
  w = create/delete files within
  x = access/traverse (cd into)

  Note: Without x, you can't access files even with r!

SPECIAL PERMISSIONS:
  SUID (4) - setuid: File runs as FILE OWNER
  SGID (2) - setgid: File runs as GROUP / Dir inherits group
  Sticky (1) - Only owner can delete their files (e.g., /tmp)

  ls -l shows: s (SUID/SGID with x), S (without x), t (sticky with x), T (without x)
        """,
        "commands": [
            {
                "name": "Set Permissions (Octal)",
                "syntax": "chmod <octal> <file>",
                "example": "chmod 755 /usr/local/bin/myscript",
                "flags": {
                    "4": "Read permission",
                    "2": "Write permission",
                    "1": "Execute permission",
                    "Owner": "First digit (rwx = 7)",
                    "Group": "Second digit (r-x = 5)",
                    "Other": "Third digit (r-- = 4)",
                    "-R": "Recursive (apply to all files in directory)",
                },
            },
            {
                "name": "Set Permissions (Symbolic)",
                "syntax": "chmod [ugoa][+-=][rwx] <file>",
                "example": "chmod u+x,g-w,o=r script.sh",
                "flags": {
                    "u": "User (owner)",
                    "g": "Group",
                    "o": "Others",
                    "a": "All (u+g+o)",
                    "+": "Add permission",
                    "-": "Remove permission",
                    "=": "Set exact permission",
                },
            },
            {
                "name": "Set Special Permissions",
                "syntax": "chmod <special><perms> <file>",
                "example": "chmod 2755 /shared/directory",
                "flags": {
                    "4xxx": "Setuid (4755) - file executes as owner",
                    "2xxx": "Setgid (2755) - file as group / dir inherits group",
                    "1xxx": "Sticky bit (1777) - only owner can delete files",
                    "u+s": "Set SUID (symbolic)",
                    "g+s": "Set SGID (symbolic)",
                    "+t": "Set sticky bit (symbolic)",
                },
            },
            {
                "name": "Change Ownership",
                "syntax": "chown <user>:<group> <file>",
                "example": "chown apache:apache /var/www/html/index.html",
                "flags": {
                    "user:group": "Set both owner and group",
                    "user": "Set owner only",
                    "user:": "Set owner, group to user's login group",
                    ":group": "Set group only (or use chgrp)",
                    "-R": "Recursive (for directories)",
                    "--reference=file": "Copy ownership from another file",
                },
            },
            {
                "name": "Change Group",
                "syntax": "chgrp <group> <file>",
                "example": "chgrp developers /project/code",
                "flags": {
                    "chgrp group file": "Change group ownership",
                    "-R": "Recursive",
                },
            },
            {
                "name": "Set Default Permissions (umask)",
                "syntax": "umask <mask>",
                "example": "umask 027",
                "flags": {
                    "umask": "Display current umask",
                    "umask 022": "Files: 644, Dirs: 755 (default)",
                    "umask 027": "Files: 640, Dirs: 750",
                    "umask 077": "Files: 600, Dirs: 700 (private)",
                    "/etc/bashrc": "Set persistent umask here",
                    "Calculation": "666-umask (files), 777-umask (dirs)",
                },
            },
            {
                "name": "Set ACL",
                "syntax": "setfacl -m u:<user>:<perms> <file>",
                "example": "setfacl -m u:nginx:rw /var/log/app.log",
                "flags": {
                    "-m": "Modify ACL (add/change entry)",
                    "u:user:rwx": "User ACL entry",
                    "g:group:rx": "Group ACL entry",
                    "o::r": "Others entry",
                    "-x u:user": "Remove specific ACL entry",
                    "-b": "Remove ALL ACLs",
                    "-R": "Recursive",
                    "-d": "Set DEFAULT ACL (new files inherit, dirs only)",
                    "--set": "Replace all ACLs",
                },
            },
            {
                "name": "View ACL",
                "syntax": "getfacl <file>",
                "example": "getfacl /data/shared",
                "flags": {
                    "getfacl file": "Show all ACL entries",
                    "ls -l": "+ at end indicates ACL exists",
                    "mask::": "Maximum effective permissions",
                },
            },
            {
                "name": "Default ACLs (Inheritance)",
                "syntax": "setfacl -d -m u:<user>:<perms> <directory>",
                "example": "setfacl -d -m u:developer:rwx /projects",
                "flags": {
                    "-d -m": "Set default ACL (affects NEW files)",
                    "d:u:user:rwx": "Default user ACL",
                    "d:g:group:rx": "Default group ACL",
                    "Note": "Default ACLs ONLY work on directories",
                },
            },
        ],
        "common_mistakes": [
            "Mixing symbolic and octal notation in same command",
            "Forgetting -R flag for recursive changes on directories",
            "Wrong order in chown (it's user:group, not group:user)",
            "ACL syntax errors (missing colons in u:user:perms)",
            "Not setting DEFAULT ACLs on directories (new files won't inherit)",
            "chmod 755 removes any special permissions - use chmod 2755 to keep SGID",
            "Forgetting x permission on directories (can't cd or access files)",
            "Setting ACL but not checking mask (mask limits effective permissions)",
            "Using chcon instead of setfacl (chcon is for SELinux contexts)",
        ],
        "exam_tricks": [
            "May ask for special permissions - know 4/2/1 prefix (SUID/SGID/Sticky)",
            "SGID on directories = new files inherit group ownership (common exam task)",
            "Sticky bit on shared dirs = users can only delete their own files",
            "ACL + sign in ls -l output indicates ACL exists",
            "Default ACLs (-d) only apply to NEW files/dirs, not existing ones",
            "Verify ACLs with getfacl, not ls -l (ls only shows +)",
            "Capital S or T in ls -l means special permission WITHOUT execute",
            "umask 027 is common for restricting others' access",
        ],
    },
}
