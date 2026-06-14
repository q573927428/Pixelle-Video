@echo off
chcp 65001 >nul 2>&1
setlocal

echo 🚀 Starting Pixelle-Video Modern UI...
echo.
echo Modern UI: http://localhost:8000/modern
echo API Docs:  http://localhost:8000/docs
echo.

:: Open browser automatically
start http://localhost:8000/modern

uv run python api/app.py --host 0.0.0.0 --port 8000

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
    echo ========================================
    echo.
    pause
)

endlocal
