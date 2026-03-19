@echo off
REM Diagnostic script for Rightmove Scraper
echo ============================================================
echo      Rightmove Scraper - System Diagnostics
echo ============================================================
echo.

echo [1] Python Installation
python --version 2>nul
if %errorlevel% neq 0 (
    echo     ERROR: Python not found! Install Python 3.10+
) else (
    echo     OK: Python installed
)
echo.

echo [2] Required Packages
python -c "import flask; print('  - Flask:', flask.__version__)" 2>nul || echo     ERROR: Flask not installed
python -c "import celery; print('  - Celery:', celery.__version__)" 2>nul || echo     ERROR: Celery not installed
python -c "import redis; print('  - Redis:', redis.__version__)" 2>nul || echo     ERROR: Redis client not installed
python -c "import selenium; print('  - Selenium:', selenium.__version__)" 2>nul || echo     ERROR: Selenium not installed
echo.

echo [3] Redis Server
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo     ERROR: Redis is not running!
    echo     Start Redis: "C:\Program Files\Redis\redis-server.exe"
) else (
    echo     OK: Redis is running
    redis-cli info | findstr "redis_version"
)
echo.

echo [4] Network Configuration
echo   Your IP addresses:
ipconfig | findstr "IPv4" | findstr /v "127.0.0.1"
echo.

echo [5] Port 5000 Status
netstat -an | findstr ":5000" >nul 2>&1
if %errorlevel% neq 0 (
    echo     Port 5000 is FREE (good - ready to start server)
) else (
    echo     Port 5000 is IN USE:
    netstat -ano | findstr ":5000"
)
echo.

echo [6] Firewall Status
echo   Checking Windows Firewall for port 5000...
netsh advfirewall firewall show rule name="Rightmove Scraper" >nul 2>&1
if %errorlevel% neq 0 (
    echo     WARNING: Firewall rule not found!
    echo     Create rule: Run as Admin:
    echo     netsh advfirewall firewall add rule name="Rightmove Scraper" dir=in action=allow protocol=TCP localport=5000
) else (
    echo     OK: Firewall rule exists
)
echo.

echo [7] Disk Space
echo   Available space on current drive:
for /f "tokens=3" %%a in ('dir /-c ^| find "bytes free"') do echo     %%a bytes
echo.

echo [8] Chrome Installation
where chrome >nul 2>&1
if %errorlevel% neq 0 (
    reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
    if %errorlevel% neq 0 (
        echo     WARNING: Chrome not found in PATH
    ) else (
        echo     OK: Chrome installed
    )
) else (
    echo     OK: Chrome installed
)
echo.

echo [9] Project Files
if exist "app.py" (
    echo     OK: app.py found
) else (
    echo     ERROR: app.py not found! Are you in the right directory?
)

if exist "data\cities.json" (
    echo     OK: data/cities.json found
) else (
    echo     ERROR: data/cities.json not found!
)

if exist ".env" (
    echo     OK: .env configuration found
) else (
    echo     WARNING: .env not found - using defaults
)
echo.

echo [10] Current Services Status
echo   Checking if services are running...

tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I /N "python.exe" >nul
if %errorlevel% neq 0 (
    echo     No Python processes running
) else (
    echo     Python processes found:
    tasklist /FI "IMAGENAME eq python.exe" | findstr "python.exe"
)
echo.

echo ============================================================
echo      Diagnostics Complete
echo ============================================================
echo.
echo If you see any ERRORs above, fix them before starting the system.
echo.

pause
