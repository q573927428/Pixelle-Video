@echo off
chcp 65001 >nul 2>&1
setlocal

set UI_MODE=%~1

if "%UI_MODE%"=="" (
    echo 🚀 Pixelle-Video UI Launcher
    echo.
    echo Please choose a UI:
    echo   [1] Classic UI  - Streamlit full toolset
    echo   [2] Modern UI   - FastAPI + Vue 3 software-style UI
    echo.
    choice /C 12 /N /M "Select 1 or 2: "
    if errorlevel 2 set UI_MODE=modern
    if errorlevel 1 set UI_MODE=classic
)

if /I "%UI_MODE%"=="2" set UI_MODE=modern
if /I "%UI_MODE%"=="1" set UI_MODE=classic

echo.
if /I "%UI_MODE%"=="modern" (
    echo 🚀 Starting Pixelle-Video Modern UI...
    echo.
    echo Modern UI: http://localhost:8000/modern
    echo API Docs:  http://localhost:8000/docs
    echo.
    uv run python api/app.py --host 0.0.0.0 --port 8000
) else (
    echo 🚀 Starting Pixelle-Video Classic Streamlit UI...
    echo.
    echo Classic UI keeps all existing tools fully available.
    echo.
    uv run streamlit run web/app.py
)

if errorlevel 1 (
    echo.
    echo ========================================
    echo   [ERROR] Failed to Start
    echo ========================================
    echo.
    echo It appears you downloaded the SOURCE CODE directly.
    echo.
    echo ========================================
    echo   For Regular Users:
    echo ========================================
    echo Please download the ONE-CLICK PACKAGE from:
    echo https://github.com/AIDC-AI/Pixelle-Video/releases
    echo.
    echo The one-click package includes:
    echo   ✓ Pre-configured Python environment
    echo   ✓ All required dependencies
    echo   ✓ FFmpeg tools
    echo   ✓ Ready to use, no setup needed
    echo.
    echo ========================================
    echo   For Developers:
    echo ========================================
    echo If you intend to develop or modify the code:
    echo   1. Install uv: https://docs.astral.sh/uv/
    echo   2. Run: uv sync
    echo   3. Then run this script again
    echo.
    echo Usage:
    echo   start_web.bat classic
    echo   start_web.bat modern
    echo.
    echo ========================================
    echo.
    pause
)

endlocal