#!/usr/bin/env bash
# ==============================================================================
# TELEPORT ROUTER & SERVER HOP MANAGER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra Router Teleport & Server Hop..."
$PYTHON_CMD -c "from core.game_selector import game_manager; print('Per-Tag Mode:', game_manager.per_tag_mode); print('Current Game:', game_manager.get_current_game())"
