# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pulsar is a portable Python-based package manager for development tools. It installs and manages development tools (like WezTerm, Neovim, lazygit) in a self-contained directory structure, similar to how package managers like pip/npm work, but for system applications.

## Commands

### Development Setup
```bash
# Activate the Pulsar environment (sets up env vars and adds bin/ to PATH)
source activate

# Run Pulsar CLI (after activation)
pulsar --help
pulsar install wezterm
pulsar list
pulsar uninstall wezterm --yes
pulsar clean
```

### Python Environment
```bash
# Sync Python dependencies (uses uv)
uv sync --directory src/

# Run directly without activation
src/.venv/bin/python src/pulsar.py --help
```

### Launch Scripts
- `pulsar-launch` - Quick launcher for WezTerm (bash)
- `pulsar-launch.bat` - Windows batch launcher (NOT WORKING YET)
- `pulsar-launch.ps1` - Windows PowerShell launcher (NOT WORKING YET)

## Architecture

### Core Components

**src/pulsar.py** - Main CLI entry point built with Typer. Defines all user-facing commands (install, uninstall, list, clean, activate). Uses Rich for beautiful terminal output.

**src/pulsar_env.py** - Environment detection and configuration. Detects OS (linux/windows) and architecture (x86_64/aarch64). Defines all Pulsar directory paths (PULSAR_BIN_DIR, PULSAR_CACHE_DIR, etc.) with environment variable overrides.

**src/package_classes.py** - Abstract base class `_PulsarPackage` and OS-specific bases (`LinuxPackage`, `WindowsPackage`). All package plugins inherit from these. Includes download progress tracking and logging infrastructure.

**src/package_installer.py** - `PackageInstaller` class handles parallel installation with ThreadPoolExecutor. Manages package installation state, version checking, and provides a live Rich UI display during installation.

**src/packages/** - Package plugin directory. Each file defines OS-specific package implementations (e.g., `WeztermLinux`, `WeztermWindows`). The `__init__.py` automatically imports all modules.

### Package Plugin System

Packages are implemented as classes inheriting from `LinuxPackage` or `WindowsPackage`. Each must implement:
- `is_installed()` - Check if installed anywhere on system
- `is_installed_with_pulsar()` - Check if installed in Pulsar bin directory
- `get_version()` - Get installed version string
- `on_env_activate()` - Called when environment is activated
- `install(version, reinstall, refresh_cache)` - Download, extract, and install binaries
- `uninstall()` - Remove package from Pulsar

Packages are automatically registered in `PACKAGE_LIST` via `__init_subclass__`.

### Directory Structure

The Pulsar environment is organized following XDG Base Directory specification:
- `bin/` - Installed executables (added to PATH)
- `.cache/` - Download cache (mapped to XDG_CACHE_HOME)
- `.local/share/` - Application data (mapped to XDG_DATA_HOME)
- `.local/state/` - State files (mapped to XDG_STATE_HOME)
- `config/` - Configuration files (mapped to XDG_CONFIG_HOME)
- `src/` - Pulsar source code and Python venv

### Activation System

The `activate` script (sourced with `source activate`):
1. Sets PULSAR_ROOT and all directory environment variables
2. Creates directory structure
3. Installs `uv` if not present
4. Syncs Python dependencies
5. Adds bin/ to PATH
6. Defines `pulsar()` bash function that wraps the Python CLI

Special handling for `pulsar activate` - the command outputs shell export statements that are eval'd by the wrapper function.

## Important Details

- **OS Detection**: Platform detection happens at import time in `pulsar_env.py`. Code must handle both Windows and Linux.
- **Class Registration**: Package classes are auto-registered via `__init_subclass__` metaclass pattern.
- **Parallel Installation**: Multiple packages install concurrently (default 4 workers). Progress is displayed in a live-updating Rich table.
- **Version Handling**: Package names support version pinning with `==` syntax (e.g., `wezterm==20230712-072601-f4abf8fd`).
- **Caching**: Downloads are cached in `.cache/<package_name>/`. Use `--refresh-cache` to force redownload.
- **Windows Support**: Windows launcher scripts (`.bat` and `.ps1`) are present but not yet working according to recent commits.
