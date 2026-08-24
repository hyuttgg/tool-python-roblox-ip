#!/usr/bin/env bash
# ==============================================================================
# AUTOEXEC INJECTOR FOR ANDROID EXECUTORS
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Đang quét và bơm file Lua vào các Executor Android (/sdcard/Arceus X, Delta, Codex...)..."

$PYTHON_CMD -c "from controller import MasterController; mc = MasterController(); insts = mc._get_combined_tag_instances(); res = mc.sync_system_state(insts, use_live_proxies=False); print(f'Đã đồng bộ thành công vào {res[\"autoexec_synced_count\"]} thư mục Autoexec!')"
