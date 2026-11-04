@echo off
setlocal enabledelayedexpansion
title Nexus Personnel Intelligence Platform

echo ========================================================================
echo    Starting Nexus Personnel Intelligence Platform (Windows Launcher)
echo ========================================================================

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please install Python 3.10+ from python.org and check "Add to PATH".
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating Python virtual environment in .\venv ...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install or update dependencies
echo [INFO] Verifying dependencies...
pip install -r requirements.txt -q

:: Run portal
echo [INFO] Launching Nexus Portal on http://localhost:8000 ...
python main.py

pause
