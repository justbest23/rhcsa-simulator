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
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create installation directory
echo "Creating installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Warning: Installation directory already exists${NC}"
    read -p "Remove existing installation? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Installation cancelled"
        exit 1
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
echo "Installing fstab safety guard"
echo "========================================="
echo
# The simulator and candidate add /etc/fstab entries (swap, mounts, fault
# injection). If a session is interrupted those can be left behind and break the
# next boot. This guard restores a known-good baseline at shutdown and early
# boot so the system always comes up clean.
GUARD_SRC="$SCRIPT_DIR/tools/rhcsa-fstab-guard.sh"
GUARD_UNIT_SRC="$SCRIPT_DIR/tools/rhcsa-fstab-guard.service"
GUARD_DST="/usr/local/sbin/rhcsa-fstab-guard.sh"
GUARD_UNIT_DST="/etc/systemd/system/rhcsa-fstab-guard.service"

if [ -f "$GUARD_SRC" ] && [ -f "$GUARD_UNIT_SRC" ]; then
    install -m 755 "$GUARD_SRC" "$GUARD_DST"
    install -m 644 "$GUARD_UNIT_SRC" "$GUARD_UNIT_DST"

    # Capture the current (clean) fstab as the baseline.
    "$GUARD_DST" init || echo -e "${YELLOW}Warning: could not capture fstab baseline (fstab not currently valid?)${NC}"

    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload
        if systemctl enable rhcsa-fstab-guard.service >/dev/null 2>&1; then
            # Activate now so the shutdown hook is armed this boot too.
            systemctl start rhcsa-fstab-guard.service >/dev/null 2>&1 || true
            echo -e "${GREEN}✓ fstab guard installed and enabled${NC}"
        else
            echo -e "${YELLOW}Warning: could not enable rhcsa-fstab-guard.service${NC}"
        fi
    else
        echo -e "${YELLOW}systemctl not available — guard installed but not enabled${NC}"
    fi
else
    echo -e "${YELLOW}Guard files not found in tools/ — skipping${NC}"
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
read -p "Populate DNF transaction history now? [Y/n]: " -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
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
