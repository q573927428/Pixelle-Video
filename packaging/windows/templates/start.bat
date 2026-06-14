@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Pixelle-Video - Windows Launcher
echo ========================================
echo.

:: Set environment variables
set "PYTHON_HOME=%~dp0python\python311"
set "PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%~dp0tools\ffmpeg\bin;%PATH%"
set "PROJECT_ROOT=%~dp0Pixelle-Video"

:: Change to project directory
cd /d "%PROJECT_ROOT%"

:: Set PYTHONPATH to project root for module imports
set "PYTHONPATH=%PROJECT_ROOT%"

:: Set PIXELLE_VIDEO_ROOT environment variable for reliable path resolution
set "PIXELLE_VIDEO_ROOT=%PROJECT_ROOT%"

:: Start API Server
echo [Starting] Pixelle-Video API Server...
echo.
echo Web UI: http://localhost:8000/modern
echo API Docs: http://localhost:8000/docs
echo.
echo Note: Configure API keys and settings in the Web UI.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

:: Open browser after server starts
start http://localhost:8000/modern

"%PYTHON_HOME%\python.exe" api/app.py --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start. Please check:
    echo   1. Python is properly installed
    echo   2. Dependencies are installed
    echo.
    pause
)

