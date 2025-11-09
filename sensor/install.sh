#!/usr/bin/env bash

# sensor/install.sh

set -euo pipefail

# --- Load Common Library ---
# Find and source the common.sh file relative to this script's location
_script_src="${BASH_SOURCE[0]:-$0}"
_script_dir="$(cd "$(dirname "${_script_src}")" >/dev/null 2>&1 && pwd)"
source "$_script_dir/../common.sh" # <-- Note the ../ to go up one level
# All log functions, colors, and SCRIPT_DIR are now available
# ---------------------------

#
# SCRIPT_DIR is now correctly set by common.sh to *this* script's directory
#

cd "$SCRIPT_DIR"

log_section "${ICON_TOOL} Python Dependencies (pip)"
if [ -d "venv" ]; then
    log "WARN" "venv directory found. Skipping venv creation."
else
    log "RUN" "Creating venv in $SCRIPT_DIR/venv..."
    python3.13 -m venv venv
    log "SUCCESS" "venv created."
fi

log "RUN" "Activating venv..."
source "venv/bin/activate"
pip install --upgrade pip
log "RUN" "Installing dependencies with pip..."
pip install -r "requirements.txt"
log "SUCCESS" "All Python dependencies are installed/verified."

deactivate

log_section "${ICON_SUCCESS} Sensor Backend Setup Complete"
echo