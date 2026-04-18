@echo off
REM Pulsar Launcher - Quick launch for WezTerm (Windows)

REM Determine script directory
set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "PULSAR_ROOT=%SCRIPT_DIR%"
set "PULSAR_BIN_DIR=%PULSAR_ROOT%\bin"
set "PULSAR_SRC_DIR=%PULSAR_ROOT%\src"
set "WEZTERM_EXE=%PULSAR_BIN_DIR%\wezterm.exe"

REM Check if wezterm is installed
if exist "%WEZTERM_EXE%" (
    start "" "%WEZTERM_EXE%"
    exit /b 0
)

REM wezterm not found, offer to install
echo ================================================
echo ⭐ Pulsar Package Manager
echo ================================================
echo.
echo WezTerm is not installed.
echo.

choice /C YN /M "Would you like to install WezTerm now"
if errorlevel 2 goto cancel
if errorlevel 1 goto install

:cancel
echo.
echo Installation cancelled.
pause
exit /b 0

:install
echo.
echo Setting up environment...

REM Set up environment variables
set "PULSAR_CONFIG_DIR=%PULSAR_ROOT%\config"
set "PULSAR_CACHE_DIR=%PULSAR_ROOT%\.cache"
set "PULSAR_DATA_DIR=%PULSAR_ROOT%\.local\share"
set "PULSAR_STATE_DIR=%PULSAR_ROOT%\.local\state"

REM Create directories
if not exist "%PULSAR_BIN_DIR%" mkdir "%PULSAR_BIN_DIR%"
if not exist "%PULSAR_CACHE_DIR%\uv" mkdir "%PULSAR_CACHE_DIR%\uv"
if not exist "%PULSAR_DATA_DIR%\uv\python" mkdir "%PULSAR_DATA_DIR%\uv\python"
if not exist "%PULSAR_DATA_DIR%\uv\tools" mkdir "%PULSAR_DATA_DIR%\uv\tools"

REM Check if uv exists
if not exist "%PULSAR_BIN_DIR%\uv.exe" (
    echo Installing uv package manager...
    set "UV_INSTALL_DIR=%PULSAR_BIN_DIR%"
    set "INSTALLER_NO_MODIFY_PATH=1"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Install Python dependencies with uv
echo Setting up Pulsar...
"%PULSAR_BIN_DIR%\uv.exe" sync --directory "%PULSAR_SRC_DIR%" --quiet

REM Check if Python venv was created
if not exist "%PULSAR_SRC_DIR%\.venv\Scripts\python.exe" (
    echo.
    echo ✗ Error: Failed to set up Python environment.
    pause
    exit /b 1
)

echo Installing WezTerm...
"%PULSAR_SRC_DIR%\.venv\Scripts\python.exe" "%PULSAR_SRC_DIR%\pulsar.py" install wezterm

if %errorlevel% equ 0 (
    echo.
    echo ✓ Installation complete!
    echo Launching WezTerm...
    timeout /t 1 /nobreak >nul
    start "" "%WEZTERM_EXE%"
    exit /b 0
) else (
    echo.
    echo ✗ Installation failed.
    pause
    exit /b 1
)
