@echo off
echo ========================================
echo   AI Accent Backend Server
echo ========================================
echo.

REM Change to backend directory
cd /d %~dp0backend
if not exist "main.py" (
    echo ERROR: Cannot find main.py
    echo Make sure you're running this from the project root directory
    pause
    exit /b 1
)

echo Current directory: %CD%
echo.
echo Starting server on http://localhost:8000
echo.
echo Press CTRL+C to stop the server
echo.
echo ========================================
echo.

python -m uvicorn main:app --reload --port 8000

pause

