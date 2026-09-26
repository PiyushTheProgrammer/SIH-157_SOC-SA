@echo off
setlocal enabledelayedexpansion
title SAT-SA Runner

:: Check if first-time setup is needed
set NEED_SETUP=0
if not exist "backend\venv" set NEED_SETUP=1
if not exist "backend\.env" set NEED_SETUP=1
if not exist "frontend\node_modules" set NEED_SETUP=1
if "%1"=="--setup" set NEED_SETUP=1
if "%1"=="-s" set NEED_SETUP=1

if !NEED_SETUP! EQU 1 (
    echo ============================================================
    echo   First-Time Setup Detected (or --setup specified)
    echo   Running Automated Setup and Database Initialization...
    echo ============================================================
    echo.
    python setup.py
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo [ERROR] Setup encountered an issue. Please review the details above.
        pause
        exit /b !ERRORLEVEL!
    )
    echo.
    echo [OK] Setup completed successfully! Starting services...
    echo.
)

:: Start Backend and Frontend
echo ============================================================
echo   Starting SAT-SA Prototype (Backend & Frontend)
echo ============================================================
echo.

:: Start Backend in a separate window
echo Starting Backend (FastAPI on http://127.0.0.1:8000)...
start "SAT-SA Backend (FastAPI)" cmd /k "cd backend && (if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) && uvicorn main:app --reload --port 8000"

:: Wait 2 seconds for backend to start
timeout /t 2 /nobreak >nul

:: Start Frontend in a separate window
echo Starting Frontend (Next.js on http://localhost:3000)...
start "SAT-SA Frontend (Next.js)" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo   Services Launched!
echo   - Backend API: http://127.0.0.1:8000/docs
echo   - Frontend App: http://localhost:3000
echo ============================================================
echo.
