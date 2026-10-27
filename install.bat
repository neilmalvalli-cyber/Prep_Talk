@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-windows.ps1" %*
set "INSTALL_RESULT=%ERRORLEVEL%"
echo.
if not "%INSTALL_RESULT%"=="0" echo Setup is incomplete. Review the message above, then run install.bat again.
if not defined FIELDNOTE_INSTALL_NO_PAUSE pause
exit /b %INSTALL_RESULT%
