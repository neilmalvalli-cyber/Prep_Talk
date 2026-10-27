@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="auth" goto auth
if /i "%~1"=="api" goto api
if /i "%~1"=="web" goto web

where wsl.exe >nul 2>nul
if errorlevel 1 goto missing_wsl
where npm.cmd >nul 2>nul
if errorlevel 1 goto missing_npm
if not exist "apps\web\node_modules\.bin\vite.cmd" goto missing_dependencies

rem Refuse occupied ports rather than start duplicate servers or change URLs.
powershell.exe -NoProfile -Command "$ports = @(8000,8001,5173); foreach ($port in $ports) { $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue; if ($listener) { Write-Host ('Port ' + $port + ' is already in use. Close the existing server before starting Fieldnote.'); exit 1 } }; exit 0"
if errorlevel 1 goto failed

start "Fieldnote Auth" /D "%~dp0" cmd.exe /d /c call "%~f0" auth
start "Fieldnote API" /D "%~dp0" cmd.exe /d /c call "%~f0" api
start "Fieldnote Web" /D "%~dp0" cmd.exe /d /c call "%~f0" web
echo.
echo Fieldnote starting in three windows. Keep all open.
echo Open http://localhost:5173 after Vite reports ready.
echo Close those windows to stop the servers.
echo The runner is not started or installed.
pause
exit /b 0

:api
rem Use the existing WSL speech environment and single-worker startup script.
rem The environment override takes precedence over the saved .env origin.
set "FIELDNOTE_ORIGIN=http://localhost:5173"
set "WSLENV=%WSLENV%:FIELDNOTE_ORIGIN"
wsl.exe -d Ubuntu -- bash -lc "bash apps/api/run-local-speech.sh"
if errorlevel 1 goto failed
exit /b 0

:auth
call :set_auth_host
if errorlevel 1 goto auth_host_failed
cd /d "%~dp0apps\web"
set "FIELDNOTE_ORIGIN=http://localhost:5173"
call npm.cmd run auth
if errorlevel 1 goto failed
exit /b 0

:web
call :set_auth_host
if errorlevel 1 goto auth_host_failed
cd /d "%~dp0apps\web"
call npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
if errorlevel 1 goto failed
exit /b 0

:set_auth_host
set "FIELDNOTE_AUTH_HOST="
for /f "tokens=3" %%G in ('wsl.exe -d Ubuntu -- ip -4 route show default') do set "FIELDNOTE_AUTH_HOST=%%G"
if not defined FIELDNOTE_AUTH_HOST exit /b 1
exit /b 0

:auth_host_failed
echo Could not determine the WSL host address for the account service.
goto failed

:missing_wsl
echo WSL is required. Provision Ubuntu and the local speech runtime first; see README.md.
goto failed
:missing_npm
echo npm is missing from PATH. Install Node.js, then reopen this launcher.
goto failed
:missing_dependencies
echo Frontend dependencies are missing. Run npm ci in apps\web first.
goto failed
:failed
echo.
echo Fieldnote could not start. Review the error above and README.md.
pause
exit /b 1
