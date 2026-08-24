#!/usr/bin/env bash
# ==============================================================================
# STRUCTURED LOGGER
# ==============================================================================

LOG_DIR="${TOOLKIT_LOGS:-$TOOLKIT_ROOT/logs}"
LOG_FILE="${LOG_DIR}/toolkit.log"

mkdir -p "$LOG_DIR" 2>/dev/null

log_message() {
    local level="$1"
    shift
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$timestamp] [$level] $*" >> "$LOG_FILE" 2>/dev/null
}

log_info() {
    log_message "INFO" "$@"
    echo -e "${C_CYAN:-}[INFO]${C_RESET:-} $*"
}

log_success() {
    log_message "SUCCESS" "$@"
    echo -e "${C_GREEN:-}[SUCCESS]${C_RESET:-} $*"
}

log_warn() {
    log_message "WARN" "$@"
    echo -e "${C_YELLOW:-}[WARN]${C_RESET:-} $*"
}

log_error() {
    log_message "ERROR" "$@"
    echo -e "${C_RED:-}[ERROR]${C_RESET:-} $*" >&2
}

log_step() {
    local current="$1"
    local total="$2"
    shift 2
    echo -e "${C_YELLOW:-}[$current/$total] [*]${C_RESET:-} $*"
}
