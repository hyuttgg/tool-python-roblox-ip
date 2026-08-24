#!/usr/bin/env bash
# ==============================================================================
# MAGISK / KERNELSU AUTO-BOOT SERVICE INSTALLER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/magisk.sh"
source "$TOOLKIT_CORE/permissions.sh"

ACTION="${1:-install}"

case "$ACTION" in
    install|enable)
        install_magisk_boot_service
        ;;
    remove|disable)
        remove_magisk_boot_service
        ;;
    *)
        echo "Sử dụng: $0 {install|remove}"
        ;;
esac
