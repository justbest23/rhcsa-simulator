"""
Domain 1: Software Management
Categories: packages, repos (NEW), flatpak (NEW), modules (NEW)
"""

CONTENT = {
    "packages": {
        "name": "Package Management (dnf/rpm)",
        "explanation": """
Package management in RHEL 8/9 uses DNF (Dandified YUM) as the primary tool.
RPM is the underlying package format. You must know how to install, remove,
query packages, manage repositories, and work with module streams.

KEY CONCEPTS:
  Package: Software bundled with metadata (name-version-release.arch.rpm)
  Repository: Collection of packages with metadata
  Module Stream: Version stream of related packages (e.g., nodejs:18, php:8.1)
  Group: Collection of packages installed together (e.g., "Development Tools")

IMPORTANT DIRECTORIES:
  /etc/yum.repos.d/       - Repository configuration files
  /var/cache/dnf/         - Package cache
  /var/log/dnf.log        - DNF transaction log
        """,
        "commands": [
            {
                "name": "Install Package",
                "syntax": "dnf install <package>",
                "example": "dnf install httpd vim-enhanced",
                "flags": {
                    "install": "Install package(s)",
                    "-y": "Assume yes to prompts",
                    "--downloadonly": "Download without installing",
                    "reinstall": "Reinstall package",
                },
            },
            {
                "name": "Remove Package",
                "syntax": "dnf remove <package>",
                "example": "dnf remove httpd",
                "flags": {
                    "remove": "Remove package and unused deps",
                    "autoremove": "Remove orphaned dependencies",
                    "-y": "Assume yes",
                },
            },
            {
                "name": "Search Packages",
                "syntax": "dnf search <keyword>",
                "example": "dnf search web server",
                "flags": {
                    "search": "Search package names and descriptions",
                    "provides": "Find which package provides a file",
                    "info": "Show package details",
                },
            },
            {
                "name": "Query Installed (RPM)",
                "syntax": "rpm -q <package>",
                "example": "rpm -qa | grep httpd",
                "flags": {
                    "-q": "Query package",
                    "-qa": "Query all installed",
                    "-qi": "Query info",
                    "-ql": "Query file list",
                    "-qf /path/file": "Which package owns file",
                    "-qc": "Query config files",
                    "-qd": "Query documentation files",
                },
            },
            {
                "name": "Package Groups",
                "syntax": "dnf group install '<group>'",
                "example": "dnf group install 'Development Tools'",
                "flags": {
                    "group list": "List available groups",
                    "group install": "Install group",
                    "group remove": "Remove group",
                    "group info": "Show group contents",
                },
            },
            {
                "name": "Transaction History",
                "syntax": "dnf history",
                "example": "dnf history\ndnf history undo 15",
                "flags": {
                    "history": "List transactions",
                    "history info N": "Show transaction details",
                    "history undo N": "Undo transaction",
                    "history redo N": "Redo transaction",
                },
            },
        ],
        "common_mistakes": [
            "Using yum instead of dnf (works but dnf is preferred)",
            "Forgetting -y flag in scripts",
            "Not enabling required repository",
            "Wrong module stream syntax (use name:stream format)",
            "Forgetting to run 'module enable' before 'module install'",
        ],
        "exam_tricks": [
            "rpm -qf /path/to/file - find which package owns a file",
            "dnf provides /path/to/file - find package that provides file",
            "Module streams: enable first, then install",
            "Group names often need quotes: 'Development Tools'",
            "Check dnf history if something breaks - you can undo",
        ],
    },
    "repos": {
        "name": "Repository Configuration",
        "explanation": """
Repository management is essential for installing packages from the correct
sources. RHEL 8/9 uses BaseOS and AppStream as default repositories.
You must know how to configure, enable, disable, and create custom repos.

REPO STRUCTURE:
  BaseOS:     Core OS packages (kernel, glibc, systemd)
  AppStream:  Applications and developer tools (versioned via modules)
  EPEL:       Extra Packages for Enterprise Linux (community)
  Custom:     Third-party or internal repos

REPO FILE FORMAT (/etc/yum.repos.d/*.repo):
  [repo-id]
  name=Human Readable Name
  baseurl=https://server/path/   OR  mirrorlist=https://...
  enabled=1
  gpgcheck=1
  gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

KEY DIRECTORIES:
  /etc/yum.repos.d/       - Repository config files (.repo)
  /etc/pki/rpm-gpg/       - GPG keys for package signing
  /var/cache/dnf/         - Downloaded package cache
        """,
        "commands": [
            {
                "name": "List Repositories",
                "syntax": "dnf repolist [all]",
                "example": "dnf repolist all",
                "flags": {
                    "repolist": "List enabled repos",
                    "repolist all": "List all repos (enabled and disabled)",
                    "repoinfo": "Show detailed repo info",
                    "repoinfo <repo-id>": "Show specific repo details",
                },
            },
            {
                "name": "Enable/Disable Repository",
                "syntax": "dnf config-manager --enable/--disable <repo-id>",
                "example": "dnf config-manager --enable crb",
                "flags": {
                    "--enable": "Enable a disabled repository",
                    "--disable": "Disable an enabled repository",
                    "--set-enabled": "Alternative to --enable",
                    "--set-disabled": "Alternative to --disable",
                },
            },
            {
                "name": "Add Repository",
                "syntax": "dnf config-manager --add-repo <url>",
                "example": "dnf config-manager --add-repo https://rpm.example.com/repo",
                "flags": {
                    "--add-repo": "Add a .repo file from URL or local path",
                    "Creates": "File in /etc/yum.repos.d/ automatically",
                },
            },
            {
                "name": "Create Repo File Manually",
                "syntax": "vi /etc/yum.repos.d/<name>.repo",
                "example": "[myrepo]\nname=My Custom Repo\nbaseurl=https://rpm.example.com/el9/\nenabled=1\ngpgcheck=0",
                "flags": {
                    "[repo-id]": "Unique identifier for the repo",
                    "name=": "Human-readable description",
                    "baseurl=": "URL to repo directory (http/https/ftp/file)",
                    "mirrorlist=": "URL to mirror list (alternative to baseurl)",
                    "enabled=": "1 to enable, 0 to disable",
                    "gpgcheck=": "1 to verify signatures, 0 to skip",
                    "gpgkey=": "Path/URL to GPG public key",
                },
            },
            {
                "name": "Import GPG Key",
                "syntax": "rpm --import <key-url>",
                "example": "rpm --import https://www.redhat.com/security/data/fd431d51.txt",
                "flags": {
                    "--import": "Import GPG public key for package verification",
                    "rpm -qa gpg-pubkey*": "List imported GPG keys",
                },
            },
            {
                "name": "Clean Cache",
                "syntax": "dnf clean all",
                "example": "dnf clean all && dnf makecache",
                "flags": {
                    "clean all": "Remove all cached data",
                    "clean metadata": "Remove repo metadata cache",
                    "clean packages": "Remove cached packages",
                    "makecache": "Rebuild metadata cache",
                },
            },
        ],
        "common_mistakes": [
            "Typos in .repo file (baseurl, enabled, gpgcheck are case-sensitive)",
            "Missing gpgkey when gpgcheck=1 (install fails with GPG error)",
            "Using baseurl AND mirrorlist (use one or the other)",
            "Forgetting to run 'dnf clean all' after repo changes",
            "Wrong baseurl path (must point to directory with repodata/)",
            "File permissions on .repo files (should be 644)",
        ],
        "exam_tricks": [
            "Exam often provides a repo URL - create .repo file in /etc/yum.repos.d/",
            "If gpgcheck fails, set gpgcheck=0 or import the GPG key",
            "dnf config-manager --add-repo is fastest for URL-based repos",
            "Always verify with 'dnf repolist' after adding a repo",
            "Use 'dnf clean all && dnf makecache' if repos aren't refreshing",
            "CRB repo (CodeReady Builder) is often needed for development packages",
        ],
    },
    "flatpak": {
        "name": "Flatpak Application Management",
        "explanation": """
Flatpak is a framework for distributing desktop applications on Linux.
It provides sandboxed applications independent of the host distribution.
RHEL 9 includes Flatpak support as an alternative application delivery method.

KEY CONCEPTS:
  Remote:      Repository source for Flatpak apps (like Flathub)
  Runtime:     Shared libraries and frameworks apps depend on
  Application: Sandboxed application package
  Ref:         Full application identifier (e.g., org.mozilla.Firefox)

FLATPAK vs RPM:
  - Flatpak apps are sandboxed (isolated from host system)
  - Flatpak apps include their own dependencies
  - Flatpak apps update independently of system packages
  - RPM packages are the primary method for system components

KEY DIRECTORIES:
  /var/lib/flatpak/         - System-wide installations
  ~/.local/share/flatpak/   - Per-user installations
        """,
        "commands": [
            {
                "name": "Add Remote Repository",
                "syntax": "flatpak remote-add --if-not-exists <name> <url>",
                "example": "flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo",
                "flags": {
                    "remote-add": "Add a Flatpak remote/repository",
                    "--if-not-exists": "Skip if remote already configured",
                    "--user": "Add for current user only",
                    "--system": "Add system-wide (default, requires root)",
                },
            },
            {
                "name": "List and Search Applications",
                "syntax": "flatpak search <keyword> / flatpak list",
                "example": "flatpak search firefox\nflatpak list --app",
                "flags": {
                    "search": "Search available applications",
                    "list": "List installed applications and runtimes",
                    "list --app": "List only installed applications",
                    "list --runtime": "List only installed runtimes",
                    "remote-ls <remote>": "List all apps in a remote",
                },
            },
            {
                "name": "Install Application",
                "syntax": "flatpak install <remote> <app-id>",
                "example": "flatpak install flathub org.mozilla.Firefox",
                "flags": {
                    "install": "Install application from remote",
                    "-y": "Assume yes to prompts",
                    "--user": "Install for current user only",
                    "--system": "Install system-wide (default)",
                },
            },
            {
                "name": "Run Application",
                "syntax": "flatpak run <app-id>",
                "example": "flatpak run org.mozilla.Firefox",
                "flags": {
                    "run": "Launch installed application",
                    "info <app-id>": "Show application details",
                },
            },
            {
                "name": "Update and Remove",
                "syntax": "flatpak update / flatpak uninstall <app-id>",
                "example": "flatpak update\nflatpak uninstall org.mozilla.Firefox",
                "flags": {
                    "update": "Update all installed applications",
                    "uninstall": "Remove application",
                    "uninstall --unused": "Remove unused runtimes",
                    "remote-delete <name>": "Remove a remote repository",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting to add Flathub remote before installing apps",
            "Using wrong app ID (use 'flatpak search' to find correct ID)",
            "Not distinguishing --user vs --system installations",
            "Forgetting to update runtimes (flatpak update handles both)",
            "Leaving unused runtimes after uninstalling apps",
        ],
        "exam_tricks": [
            "flatpak remote-add --if-not-exists is idempotent (safe to repeat)",
            "App IDs use reverse-DNS format: org.mozilla.Firefox",
            "Use 'flatpak list --app' to see only applications (not runtimes)",
            "System-wide installs need root; --user installs don't",
            "Flatpak apps are isolated - they can't access host files by default",
        ],
    },
    "modules": {
        "name": "Package Module Streams",
        "explanation": """
Module streams in RHEL 8/9 allow multiple versions of software to coexist
in the same repository. AppStream repo provides modules for languages,
databases, and web servers at different version streams.

KEY CONCEPTS:
  Module:   A set of packages representing a component (e.g., nodejs, php)
  Stream:   A version of the module (e.g., nodejs:18, nodejs:20)
  Profile:  A set of packages within a stream (common, devel, minimal)
  Default:  Stream and profile used when none specified

MODULE STATES:
  [d] Default  - Stream is the default version
  [e] Enabled  - Stream is enabled for installation
  [x] Disabled - Module is disabled
  [i] Installed - Module profile is installed

WORKFLOW:
  1. List modules:  dnf module list
  2. Enable stream: dnf module enable <module>:<stream>
  3. Install:       dnf module install <module>:<stream>/<profile>
  4. To switch:     dnf module reset <module> first, then enable new stream
        """,
        "commands": [
            {
                "name": "List Available Modules",
                "syntax": "dnf module list [module-name]",
                "example": "dnf module list\ndnf module list nodejs",
                "flags": {
                    "module list": "List all available modules and streams",
                    "module list <name>": "List streams for specific module",
                    "--enabled": "Show only enabled modules",
                    "--installed": "Show only installed modules",
                },
            },
            {
                "name": "Enable Module Stream",
                "syntax": "dnf module enable <module>:<stream>",
                "example": "dnf module enable nodejs:18",
                "flags": {
                    "module enable": "Enable a specific stream (doesn't install)",
                    "<module>:<stream>": "Module name and version stream",
                    "-y": "Assume yes to prompts",
                },
            },
            {
                "name": "Install Module",
                "syntax": "dnf module install <module>:<stream>[/<profile>]",
                "example": "dnf module install nodejs:18/common\ndnf module install php:8.1",
                "flags": {
                    "module install": "Install module packages",
                    ":<stream>": "Specific version stream",
                    "/<profile>": "Specific profile (common, devel, minimal)",
                    "Default profile": "Used when /<profile> is omitted",
                },
            },
            {
                "name": "Switch Module Stream",
                "syntax": "dnf module reset <module> && dnf module enable <module>:<new-stream>",
                "example": "dnf module reset nodejs\ndnf module enable nodejs:20\ndnf module install nodejs:20",
                "flags": {
                    "module reset": "Reset module to initial state",
                    "module disable": "Disable module entirely",
                    "Then enable": "Enable the new stream after reset",
                    "Then install": "Install the new stream packages",
                },
            },
            {
                "name": "Module Info",
                "syntax": "dnf module info <module>:<stream>",
                "example": "dnf module info nodejs:18",
                "flags": {
                    "module info": "Show module details",
                    "--profile": "Show available profiles",
                    "Profiles": "common, devel, minimal (varies by module)",
                },
            },
        ],
        "common_mistakes": [
            "Installing module without enabling stream first",
            "Trying to enable two streams of the same module (must reset first)",
            "Forgetting to reset before switching to a different stream",
            "Confusing module name with package name",
            "Not specifying stream when multiple are available",
        ],
        "exam_tricks": [
            "Enable first, then install: dnf module enable, then dnf module install",
            "To switch streams: reset -> enable new stream -> install",
            "Default stream has [d] marker in 'dnf module list'",
            "[e] means enabled, [i] means installed, [x] means disabled",
            "Some modules have multiple profiles - exam may specify which one",
            "'dnf module list --installed' to verify what's active",
        ],
    },
}
