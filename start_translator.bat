@echo off
title AI Translator
cd /d "%~dp0"

echo ========================================
echo AI Translator with Auto-Restart
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

REM Run with restart wrapper
python run_with_restart.py

pause
