#!/usr/bin/env bash
# ==============================================================================
# Roblox Multi-Instance Master Controller - Fast Launcher
# ==============================================================================

if [ -f "shell/termux_setup.sh" ]; then
    bash shell/termux_setup.sh
else
    python controller.py
fi
