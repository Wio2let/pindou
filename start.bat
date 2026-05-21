@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title XHS Monitor

rem Switch to the script's own directory so double-clicking from anywhere works
pushd "%~dp0"

echo ========================================
echo  XHS Monitor (Backend + Frontend)
echo ========================================
echo.

rem ---------- Pick Python interpreter ----------
set "PY="
if exist ".venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
    echo [*] Using project venv: .venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [X] Python not found. Install Python or create .venv first.
        goto :fail
    )
    set "PY=python"
    echo [^^!] No .venv found, falling back to system python ^(may miss deps^)
)

rem ---------- Ensure Python deps are installed ----------
"%PY%" -c "import uvicorn, fastapi" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing Python deps from requirements.txt ^(first run^)...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] pip install failed
        goto :fail
    )
)

rem ---------- Check npm ----------
where npm >nul 2>&1
if errorlevel 1 (
    echo [X] npm not found. Install Node.js from https://nodejs.org/
    goto :fail
)

rem ---------- Install frontend deps on first run ----------
if not exist "frontend\node_modules" (
    echo [*] Installing frontend deps for the first time...
    pushd frontend
    call npm install
    set "NPM_ERR=%ERRORLEVEL%"
    popd
    if not "%NPM_ERR%"=="0" (
        echo [X] npm install failed
        goto :fail
    )
)

rem ---------- Auto-launch Chrome with debug port if not already running ----------
echo.
netstat -an 2>nul | findstr ":9222 " | findstr "LISTENING" >nul
if errorlevel 1 (
    set "CHROME="
    if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    if not defined CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    if not defined CHROME if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

    if defined CHROME (
        if not exist "C:\chrome-debug" mkdir "C:\chrome-debug" >nul 2>&1
        echo [*] Launching Chrome with --remote-debugging-port=9222...
        echo     Profile dir: C:\chrome-debug ^(separate from your normal Chrome^)
        start "" "!CHROME!" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug" "https://www.xiaohongshu.com"
        echo     If first time, scan the QR code to log in to Xiaohongshu.
    ) else (
        echo [^^!] Chrome not found in standard install paths. Launch it manually:
        echo     chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"
    )
) else (
    echo [*] Port 9222 already in use ^(Chrome debug likely running^) — skipping launch.
)
echo.

rem ---------- Launch backend (window stays open on error) ----------
echo [*] Starting backend on port 8765...
start "XHS-Backend" /D "%~dp0" cmd /k ""%PY%" run.py"

rem Give backend a head start so the frontend's first request doesn't fail
timeout /t 3 >nul

rem ---------- Launch frontend ----------
echo [*] Starting frontend on port 5173...
start "XHS-Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo [OK] Started.
echo     Backend:  http://127.0.0.1:8765
echo     Frontend: http://localhost:5173
echo.
echo If either window shows an error, it will stay open so you can read it.
echo.

rem Print Chinese hint via PowerShell so encoding is reliable
powershell -NoProfile -Command "Write-Host '提示: 在那个调试端口的 Chrome 里先扫码登录小红书, 再到前端点立即运行。' -ForegroundColor Yellow"

popd
endlocal
pause
exit /b 0

:fail
echo.
popd
endlocal
pause
exit /b 1
