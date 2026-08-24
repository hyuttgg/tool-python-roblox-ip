#!/usr/bin/env bash
# ==============================================================================
# JAVA ENVIRONMENT & COMPILER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra JDK / JRE trên Termux..."
java -version 2>&1 || log_warn "Chưa cài OpenJDK (chạy: pkg install openjdk-17)"
