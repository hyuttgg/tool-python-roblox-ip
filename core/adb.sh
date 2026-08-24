#!/usr/bin/env bash
# ==============================================================================
# ADB WRAPPER FOR EMULATORS & CLOUD PHONES
# ==============================================================================

get_adb_cmd() {
    if command -v adb >/dev/null 2>&1; then
        echo "adb"
    elif [ -x "$PREFIX/bin/adb" ]; then
        echo "$PREFIX/bin/adb"
    else
        echo ""
    fi
}

list_connected_adb_devices() {
    local adb_bin=$(get_adb_cmd)
    if [ -n "$adb_bin" ]; then
        $adb_bin devices 2>/dev/null | grep -v "List of devices" | grep "device$" | awk '{print $1}'
    fi
}
