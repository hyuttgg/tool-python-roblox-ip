#!/usr/bin/env bash
# ==============================================================================
# PER-TAG MULTI-GAME MANAGER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

$PYTHON_CMD -c "from core.game_selector import game_manager, POPULAR_ROBLOX_GAMES; print('=== DANH SÁCH GAME MỤC TIÊU ==='); [print(f'[{g.id}] {g.name:<25} (PlaceId: {g.place_id})') for g in POPULAR_ROBLOX_GAMES]"
