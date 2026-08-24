#!/usr/bin/env bash
# ==============================================================================
# PYTHON ENVIRONMENT & VIRTUALENV MANAGER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra môi trường Python..."
$PYTHON_CMD --version
pip list 2>/dev/null | grep -E "requests|urllib3|psutil" || echo "Pip packages checked."
