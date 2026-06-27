#!/bin/bash
#
# RHCSA Mock Exam Simulator - Installation Script
#
# This script installs the RHCSA simulator to /opt/rhcsa-simulator
# and creates a symlink for easy access.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/rhcsa-simulator"
BIN_LINK="/usr/local/bin/rhcsa-simulator"
REQUIRED_PYTHON_VERSION="3.6"

# Defaults / argument parsing
ASSUME_YES=false      # auto-answer all [y/N] prompts (overwrite, non-RHEL continue)
POPULATE=""           # ""=ask/auto, "yes"=force populate, "no"=skip populate

usage() {
    cat <<EOF
Usage: $0 [options]

  -y, --yes, --force   Run unattended: overwrite an existing installation and
                       continue on non-RHEL systems without prompting.
      --populate       Populate DNF transaction history without prompting.
      --no-populate    Skip populating DNF transaction history.
  -h, --help           Show this help and exit.

If stdin is not a TTY (e.g. piped or run from a script), unattended mode is
assumed automatically.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes|--force) ASSUME_YES=true ;;
        --populate) POPULATE="yes" ;;
        --no-populate) POPULATE="no" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
    shift
done

# No controlling terminal on stdin -> can't prompt, so assume unattended.
if [ ! -t 0 ]; then
    ASSUME_YES=true
fi

echo "========================================="
echo "RHCSA Mock Exam Simulator - Installation"
echo "========================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install.sh"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.6 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python ${PYTHON_VERSION}"

if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]; then
    echo -e "${RED}Error: Python ${REQUIRED_PYTHON_VERSION} or later is required${NC}"
    exit 1
fi

# Check OS
echo "Checking operating system..."
if [ -f /etc/redhat-release ]; then
    OS_INFO=$(cat /etc/redhat-release)
    echo "Detected: ${OS_INFO}"
else
    echo -e "${YELLOW}Warning: This tool is designed for RHEL/Rocky/Alma Linux${NC}"
    if [ "$ASSUME_YES" = true ]; then
        echo "Continuing anyway (unattended mode)."
    else
        read -p "Continue anyway? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Create installation directory
echo "Creating installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Warning: Installation directory already exists${NC}"
    if [ "$ASSUME_YES" = true ]; then
        echo "Removing existing installation (unattended mode)..."
        rm -rf "$INSTALL_DIR"
    else
        read -p "Remove existing installation? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            echo "Installation cancelled"
            exit 1
        fi
    fi
fi

mkdir -p "$INSTALL_DIR"

# Copy files
echo "Copying files..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

# Set permissions
echo "Setting permissions..."
chmod -R 644 "$INSTALL_DIR"/*.py
chmod -R 755 "$INSTALL_DIR"/{config,core,tasks,validators,utils}
chmod -R 755 "$INSTALL_DIR"/data
chmod 755 "$INSTALL_DIR/rhcsa_simulator.py"

# Create symlink
echo "Creating symlink..."
if [ -L "$BIN_LINK" ] || [ -f "$BIN_LINK" ]; then
    rm -f "$BIN_LINK"
fi

ln -s "$INSTALL_DIR/rhcsa_simulator.py" "$BIN_LINK"
chmod 755 "$BIN_LINK"

# Create requirements.txt (empty - stdlib only)
echo "# No external dependencies required - Python stdlib only" > "$INSTALL_DIR/requirements.txt"

# Verify installation
echo "Verifying installation..."
if [ -f "$INSTALL_DIR/rhcsa_simulator.py" ] && [ -L "$BIN_LINK" ]; then
    echo -e "${GREEN}✓ Installation successful!${NC}"
    echo
    echo "Installation Details:"
    echo "  Location: $INSTALL_DIR"
    echo "  Executable: $BIN_LINK"
    echo
    echo "Usage:"
    echo "  sudo rhcsa-simulator"
    echo
    echo -e "${YELLOW}Note: You must run as root (sudo) to validate system state${NC}"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

echo
echo "========================================="
echo "Optional: Populate Practice Environment"
echo "========================================="
echo
echo "Some practice tasks (e.g. DNF history) work best with a populated"
echo "transaction history. This installs and removes small packages to"
echo "build up ~12 DNF transactions. Nothing is permanently changed."
echo
# Decide whether to populate: explicit flag wins, then unattended default (yes),
# otherwise ask.
if [ "$POPULATE" = "yes" ]; then
    do_populate=true
elif [ "$POPULATE" = "no" ]; then
    do_populate=false
elif [ "$ASSUME_YES" = true ]; then
    do_populate=true
else
    read -p "Populate DNF transaction history now? [Y/n]: " -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then do_populate=false; else do_populate=true; fi
fi

if [ "$do_populate" = true ]; then
    echo "Building DNF transaction history..."
    PRACTICE_PKGS=(tree dos2unix bc mtr strace lsof pv screen nmap zip ltrace telnet whois jq)
    CYCLES=0
    TARGET=12
    for pkg in "${PRACTICE_PKGS[@]}"; do
        if [ "$CYCLES" -ge "$TARGET" ]; then
            break
        fi
        if rpm -q "$pkg" &>/dev/null; then
            continue  # already installed — skip
        fi
        echo "  Installing $pkg..."
        if dnf install -y --quiet "$pkg" &>/dev/null 2>&1; then
            echo "  Removing $pkg..."
            dnf remove -y --quiet "$pkg" &>/dev/null 2>&1
            CYCLES=$((CYCLES + 1))
        fi
    done
    if [ "$CYCLES" -gt 0 ]; then
        echo -e "${GREEN}✓ Completed $CYCLES install/remove cycles ($((CYCLES * 2)) new DNF transactions)${NC}"
    else
        echo -e "${YELLOW}No cycles completed — check DNF repo access with: dnf repolist${NC}"
    fi
else
    echo "Skipped. Run 'Setup → Populate Practice Environment' in the simulator later."
fi

echo
echo "========================================="
echo "Installation Complete!"
echo "========================================="
