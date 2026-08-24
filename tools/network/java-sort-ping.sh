#!/usr/bin/env bash
# ==============================================================================
# JAVA SELECTION SORT & LATENCY PROBER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Thực thi Java Selection Sort Engine kiểm tra độ trễ..."
$PYTHON_CMD -c "from core.java_sort_bridge import SelectionSortBridge; res = SelectionSortBridge.probe_ip_latency_java('8.8.8.8', 53); print('Google DNS Latency via Java:', res)"
