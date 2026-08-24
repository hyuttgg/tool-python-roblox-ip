@echo off
chcp 65001 >nul
title Roblox Multi-Tag Master Controller
cls
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Python! Vui long cai dat Python 3 tu python.org va tick 'Add Python to PATH'.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt --quiet >nul 2>nul
python controller.py %*
if %errorlevel% neq 0 (
    pause
)
