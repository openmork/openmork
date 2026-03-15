@echo off
REM ============================================================================
REM OpenMork Installer for Windows (CMD wrapper)
REM ============================================================================
REM This batch file launches the PowerShell installer for users running CMD.
REM
REM Usage:
REM   curl -fsSL https://raw.githubusercontent.com/openmork/openmork/main/scripts/install.cmd -o install.cmd && install.cmd && del install.cmd
REM
REM Or if you're already in PowerShell, use the direct command instead:
REM   irm https://raw.githubusercontent.com/openmork/openmork/main/scripts/install.ps1 | iex
REM ============================================================================

echo.
echo  OpenMork Installer
echo  Launching PowerShell installer...
echo.

powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://raw.githubusercontent.com/openmork/openmork/main/scripts/install.ps1 | iex"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  Installation failed. Please try running PowerShell directly:
    echo    powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/openmork/openmork/main/scripts/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo.
echo  [DEPRECATED COMPAT] Legacy command name 'hermes' is temporarily supported via alias after install.
echo  Please migrate scripts and docs to use 'openmork'.
echo.