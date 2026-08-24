#!/usr/bin/env bash
# ==============================================================================
# ROBLOX CLONE PROFILES & DUAL APP SCANNER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Quét danh sách các bản Clone / Multi-Instance Roblox..."
$PYTHON_CMD -c "from core.clone_scanner import ClonedProfileScanner; scanner = ClonedProfileScanner(); profiles = scanner.scan_all_profiles(); print(f'Tìm thấy {len(profiles)} cấu hình Clone!')"
