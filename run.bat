@echo off
title Mega Hack Installer

REM Change to the directory where the .bat file is located
cd /d "%~dp0"

REM Check if python is available
python --version >nul 2>&1
if %errorlevel% equ 0 (
    python -u crack.py %*
    pause
    exit /b
)

REM Check if py is available (Windows Store Python)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    py -u crack.py %*
    pause
    exit /b
)

REM Neither found
echo Python not found. Please install Python 3.8 or higher and ensure it's in your PATH.
echo Download from: https://www.python.org/downloads/windows/
pause
exit /b 1