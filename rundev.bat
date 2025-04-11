@echo off
REM Stock Analysis System Launcher
REM Version 2.1 - Cross-Platform Ready

:: ---------------------------
:: Initialization Checks
:: ---------------------------
where python 3.10 >nul 2>&1 || (
    echo [ERROR] Python 3.10 not detected
    timeout /t 5
    exit /b 1
)

where node >nul 2>&1 || (
    echo [ERROR] Node.js not detected
    timeout /t 5
    exit /b 1
)

:: ---------------------------
:: Environment Setup
:: ---------------------------
if not exist ".venv\" (
    echo Initializing virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    @REM pip install -r backend\requirements.txt >nul 2>&1
)

:: ---------------------------
:: Service Launcher
:: ---------------------------
start "Backend Server" cmd /k "call .venv\Scripts\activate.bat && cd backend && echo [BACKEND] Starting at http://localhost:8000 && uvicorn main:app --reload"

timeout /t 3 >nul

start "Frontend Server" cmd /k "cd frontend && echo [FRONTEND] Starting at http://localhost:3000 && npm run dev"

:: ---------------------------
:: Auto-Open Browser (Optional)
:: ---------------------------
@REM timeout /t 5 >nul
@REM start "" "http://localhost:3000"

:: ---------------------------
:: Process Monitor
:: ---------------------------
echo.
echo System Status:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo.
echo Keep this window open to monitor services
echo Press CTRL+C to terminate all processes

:monitor_loop
timeout /t 30 >nul
goto monitor_loop