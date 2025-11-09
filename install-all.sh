#!/usr/bin/env bash

# install-all.sh

set -euo pipefail

# --- Load Common Library ---
# Find and source the common.sh file relative to this script's location
_script_src="${BASH_SOURCE[0]:-$0}"
_script_dir="$(cd "$(dirname "${_script_src}")" >/dev/null 2>&1 && pwd)"
source "$_script_dir/common.sh"
# All log functions, colors, and SCRIPT_DIR are now available
# ---------------------------

# --- Start Script ---
log_section "🚀 Starting Full Project Installation"
log "INFO" "This script will run the main installer and then the sensor installer."
echo

# --- 1. Run Main Installer ---
log_section "Step 1/2: Running Main Dependency Installer"
if [ ! -f "$SCRIPT_DIR/install.sh" ]; then
    log_error_and_exit "Could not find main 'install.sh' in $SCRIPT_DIR"
fi

"$SCRIPT_DIR/install.sh"
log "SUCCESS" "Main dependency installer finished."
echo

# --- 2. Run Sensor Backend Installer ---
log_section "Step 2/2: Running Sensor Backend Installer"
if [ ! -f "$SCRIPT_DIR/sensor/install.sh" ]; then
    log_error_and_exit "Could not find 'sensor/install.sh' in $SCRIPT_DIR"
fi

"$SCRIPT_DIR/sensor/install.sh"
log "SUCCESS" "Sensor backend installer finished."
echo

# --- All Done ---
log_section "${ICON_SUCCESS} Full Project Installation Complete"
log "INFO" "All components have been successfully installed or verified."
echo