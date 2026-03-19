@echo off
REM Rightmove Scraper - Start All Services
REM Run this to start the scraper system manually

echo ============================================================
echo      Rightmove Scraper - Production System
echo ============================================================
echo.

REM Check if Redis is running
echo [1/3] Checking Redis...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo     Redis is NOT running!
    echo     Starting Redis...
    start "Redis Server" "C:\Program Files\Redis\redis-server.exe"
    timeout /t 3 /nobreak >nul
) else (
    echo     Redis is running ✓
)
echo.

REM Start Celery worker in new window
echo [2/3] Starting Celery worker...
start "Celery Worker" cmd /k "cd /d %~dp0 && celery -A app.celery worker --loglevel=info --pool=solo --concurrency=3"
echo     Celery worker started ✓
echo.

REM Start Flask web server
echo [3/3] Starting web server...
echo.
echo ============================================================
echo     System is ready!
echo     Access at: http://localhost:5000
echo     Or from network: http://YOUR_IP:5000
echo ============================================================
echo.
echo Find your IP: ipconfig
echo.
echo Press Ctrl+C to stop the web server (Celery runs in separate window)
echo.

waitress-serve --host=0.0.0.0 --port=5000 app:app
