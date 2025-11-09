#!/usr/bin/env bash

# install.sh

set -euo pipefail

# --- Load Common Library ---
# Find and source the common.sh file relative to this script's location
_script_src="${BASH_SOURCE[0]:-$0}"
_script_dir="$(cd "$(dirname "${_script_src}")" >/dev/null 2>&1 && pwd)"
source "$_script_dir/common.sh"
# All log functions, colors, and SCRIPT_DIR are now available
# ---------------------------


# -------------------------
#      START SCRIPT
# -------------------------
log_section "${ICON_TOOL} Starting Dependency Installer"

# Change to home
cd "$HOME"
log "INFO" "Changed directory to $HOME"

# -------------------------
# Install nvm, node, and pnpm
# -------------------------
log_section "${ICON_PKG} Node.js Environment (nvm, node, pnpm)"
log "INFO" "Checking for nvm installation in $HOME/.nvm..."
if [ -d "$HOME/.nvm" ]; then
    log "WARN" "nvm directory found. Skipping nvm installation."
else
    log "RUN" "nvm not found. Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    log "SUCCESS" "nvm installed."
fi

# Source nvm to make it available in this script
log "INFO" "Sourcing nvm..."
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
else
    log_error_and_exit "nvm.sh not found. Cannot proceed. Please restart your shell and re-run."
fi
log "SUCCESS" "nvm is sourced."

log "RUN" "Installing/verifying Node.js v24 (this is idempotent)..."
nvm install 24
log "SUCCESS" "Node.js v24 is ready. Active version: $(node -v)"

log "RUN" "Enabling and preparing pnpm with corepack (non-interactive)..."
corepack enable pnpm
corepack prepare pnpm@latest --activate
PNPM_VERSION=$(pnpm --version)
log "SUCCESS" "pnpm is ready. Active version: $PNPM_VERSION"

# --- Add persistence warning ---
log "WARN" "To make nvm permanent, you MUST close and re-open"
log "WARN" "your terminal, or run: ${BOLD}source ~/.bashrc${RESET} (or ~/.zshrc)"

# -------------------------
# Install apt packages
# -------------------------
log_section "${ICON_PKG} System Dependencies (apt)"
log "RUN" "Updating apt package lists... (requires sudo)"
sudo apt update -y
log "RUN" "Installing software-properties-common..."
sudo apt install -y software-properties-common
log "SUCCESS" "software-properties-common is installed."

log "INFO" "Adding deadsnakes PPA for newer Python versions..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
log "RUN" "Updating package lists from all repositories..."
sudo apt update -y && sudo apt upgrade -y
log "SUCCESS" "Package lists and system upgraded."

log "RUN" "Installing core dependencies via apt..."
sudo apt-get install -y \
    git \
    make \
    cmake \
    automake \
    libtool \
    libusb-1.0-0-dev \
    libfftw3-dev \
    build-essential \
    libpam0g-dev \
    docbook-utils \
    python3.13-full \
    libpython3.13 \
    pkg-config
log "SUCCESS" "All apt dependencies are installed/verified."
# -------------------------
# Install hackrf from source
# -------------------------
log_section "${ICON_PKG} HackRF Tools (from source)"
log "INFO" "Checking for existing 'hackrf_info' in your system PATH..."

# Use 'command -v' to check if the command exists anywhere in the PATH 
# (e.g., /usr/bin OR /usr/local/bin). This is the most reliable check
# and does NOT execute the program.
if command -v hackrf_info >/dev/null 2>&1; then
    local HACKRF_PATH
    HACKRF_PATH=$(command -v hackrf_info)
    log "WARN" "hackrf_info found in PATH at: $HACKRF_PATH"
    log "WARN" "Skipping build from source."
else
    log "RUN" "hackrf_info not found in PATH. Building and installing from source..."
    
    # Run in a subshell to avoid changing the main script's directory
    (
        cd "$HOME"
        log "INFO" "Cloning hackrf repository..."
        if [ -d "hackrf" ]; then
            log "INFO" "hackrf directory already exists. Pulling latest changes."
            cd hackrf
            git pull
        else
            git clone https://github.com/greatscottgadgets/hackrf.git
            cd hackrf
        fi
        
        log "RUN" "Configuring build with cmake..."
        mkdir -p host/build
        cd host/build
        cmake ..
        log "RUN" "Building hackrf (this may take a few minutes)..."
        make
        log "RUN" "Installing hackrf (requires sudo)..."
        # This 'make install' will place binaries in /usr/local/bin
        sudo make install
        sudo ldconfig
        log "SUCCESS" "hackrf installed from source."
    )
fi
log "SUCCESS" "HackRF tools are installed/verified."

# -------------------------
log "SUCCESS" "All dependencies have been successfully installed or verified."


log_section "${ICON_SUCCESS} Installation Complete"
echo