@echo off
REM Pulsar activation script for cmd.exe

REM Determine PULSAR_ROOT from script location
set "PULSAR_ROOT=%~dp0"
REM Remove trailing backslash
set "PULSAR_ROOT=%PULSAR_ROOT:~0,-1%"

set "PULSAR_BIN_DIR=%PULSAR_ROOT%\bin"
set "PULSAR_SRC_DIR=%PULSAR_ROOT%\src"
set "PULSAR_CONFIG_DIR=%PULSAR_ROOT%\config"
set "PULSAR_CACHE_DIR=%PULSAR_ROOT%\.cache"
set "PULSAR_DATA_DIR=%PULSAR_ROOT%\.local\share"
set "PULSAR_STATE_DIR=%PULSAR_ROOT%\.local\state"

REM Create directory structure
if not exist "%PULSAR_BIN_DIR%" mkdir "%PULSAR_BIN_DIR%"
if not exist "%PULSAR_CACHE_DIR%\uv" mkdir "%PULSAR_CACHE_DIR%\uv"
if not exist "%PULSAR_CONFIG_DIR%" mkdir "%PULSAR_CONFIG_DIR%"
if not exist "%PULSAR_DATA_DIR%\uv\python" mkdir "%PULSAR_DATA_DIR%\uv\python"
if not exist "%PULSAR_DATA_DIR%\uv\tools" mkdir "%PULSAR_DATA_DIR%\uv\tools"
if not exist "%PULSAR_STATE_DIR%" mkdir "%PULSAR_STATE_DIR%"

REM Set XDG directories for portable apps
set "XDG_CONFIG_HOME=%PULSAR_CONFIG_DIR%"
set "XDG_CACHE_HOME=%PULSAR_CACHE_DIR%"
set "XDG_DATA_HOME=%PULSAR_DATA_DIR%"
set "XDG_STATE_HOME=%PULSAR_STATE_DIR%"

REM UV environment variables
set "UV_TOOL_DIR=%PULSAR_DATA_DIR%\uv\tools"
set "UV_PYTHON_INSTALL_DIR=%PULSAR_DATA_DIR%\uv\python"
set "UV_CACHE_DIR=%PULSAR_CACHE_DIR%\uv"

REM Install uv if not already installed
if not exist "%PULSAR_BIN_DIR%\uv.exe" (
    echo Installing uv to %PULSAR_BIN_DIR%...

    REM Download and install uv
    set "UV_INSTALL_DIR=%PULSAR_BIN_DIR%"
    set "INSTALLER_NO_MODIFY_PATH=1"
    powershell -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"

    echo.
    echo ✓ uv installed successfully
)

REM Install pulsar system packages
"%PULSAR_BIN_DIR%\uv.exe" sync --directory "%PULSAR_SRC_DIR%" --quiet

REM Add bin directory to PATH
set "PATH=%PULSAR_BIN_DIR%;%PATH%"

REM Display banner
echo.
echo ⭐ Pulsar environment activated
echo Type 'pulsar --help' for usage information
echo.

REM Note: doskey doesn't work well in batch scripts for persistent aliases
REM Users should manually call: pulsar <command>
