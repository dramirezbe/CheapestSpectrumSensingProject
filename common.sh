#!/usr/bin/env bash

# common.sh

# --- Configuration ---

# Turn colors off if TTY is not available
if [ -t 1 ]; then
    # --- ANSI Color Codes ---
    RESET='\033[0m'
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
else
    RESET=''
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
fi

# --- Emojis ---
ICON_INFO="ℹ️"
ICON_SUCCESS="✅"
ICON_WARN="⚠️"
ICON_ERROR="❌"
ICON_RUN="⏳"
ICON_PKG="📦"
ICON_TOOL="🛠️"

# --- Logger ---

# Central logging function
# Usage: log "LEVEL" "Message"
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    local color=$RESET
    local icon=$ICON_INFO
    
    case "$level" in
        INFO)
            color=$BLUE
            icon=$ICON_INFO
            ;;
        SUCCESS)
            color=$GREEN
            icon=$ICON_SUCCESS
            ;;
        WARN)
            color=$YELLOW
            icon=$ICON_WARN
            ;;
        ERROR)
            color=$RED
            icon=$ICON_ERROR
            ;;
        RUN)
            color=$CYAN
            icon=$ICON_RUN
            ;;
    esac
    
    # Format: [TIMESTAMP] [ICON] [LEVEL] MESSAGE
    echo -e "${color}[${timestamp}] ${icon} [${level}] ${message}${RESET}"
}

# Helper for section headers
log_section() {
    echo
    log "INFO" "${BOLD}=================================================${RESET}"
    log "INFO" "${BOLD}$1${RESET}"
    log "INFO" "${BOLD}=================================================${RESET}"
}

# Helper for critical errors
log_error_and_exit() {
    log "ERROR" "$1"
    exit 1
}

# -------------------------
# Resolve Script Path
# -------------------------
# This defines SCRIPT_PATH and SCRIPT_DIR for the script that *sources* this file.
# Note: This variable is relative to the *sourcing* script, not common.sh itself.
_script_src="${BASH_SOURCE[1]:-${BASH_SOURCE[0]:-$0}}"

resolve_abs() {
  local p="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath -- "$p"
  elif command -v readlink >/dev/null 2>&1 && readlink -f / >/dev/null 2>&1; then
    readlink -f -- "$p"
  else
    if command -v python3 >/dev/null 2>&1; then
      python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$p"
    else
      python -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$p"
    fi
  fi
}
SCRIPT_PATH="$(resolve_abs "$_script_src")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" >/dev/null 2>&1 && pwd)"


# --- Exports ---
# Export all functions and variables to make them available to the sourcing script
export RESET RED GREEN YELLOW BLUE CYAN BOLD
export ICON_INFO ICON_SUCCESS ICON_WARN ICON_ERROR ICON_RUN ICON_PKG ICON_TOOL
export -f log
export -f log_section
export -f log_error_and_exit
export -f resolve_abs
export SCRIPT_PATH SCRIPT_DIR