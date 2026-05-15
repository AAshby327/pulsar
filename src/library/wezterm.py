"""A powerful cross-platform terminal emulator and multiplexer.

Written by https://github.com/wez and implemented in Rust.
"""

import typer
import shutil
import urllib.request
import json
import subprocess

import pulsar_env
import star_map
from spell_book_class import SpellBook

wezterm_book = SpellBook('wezterm')

# Check installation status on module import
def _check_pulsar_installation():
    """Check if wezterm is installed in pulsar bin folder."""
    if pulsar_env.OS == 'linux':
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        return install_dir.exists() and (install_dir / 'usr' / 'bin' / 'wezterm').exists()
    elif pulsar_env.OS == 'windows':
        exe_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm.exe'
        return exe_path.exists()
    return False

def _check_system_installation():
    """Check if wezterm is installed system-wide."""
    return shutil.which('wezterm') is not None

def _get_installed_version():
    """Query wezterm for its version."""
    try:
        result = subprocess.run(
            ['wezterm', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse version from output (e.g., "wezterm 20240203-110809-5046fc22")
            output = result.stdout.strip()
            parts = output.split()
            if len(parts) >= 2:
                return parts[1]
        return None
    except Exception:
        return None

# Set installation status
wezterm_book.installed_with_pulsar = _check_pulsar_installation()
wezterm_book.installed = wezterm_book.installed_with_pulsar or _check_system_installation()
wezterm_book.version = _get_installed_version() if wezterm_book.installed else None

def _get_version(goblin, locked_data):
    """Get the version to install from star_map or GitHub API."""
    if locked_data and 'version' in locked_data:
        version = locked_data['version']
        goblin.logger.info('Using locked version %s from star_map', version)
        return version

    goblin.logger.info('Fetching latest version from GitHub')
    url = 'https://api.github.com/repos/wez/wezterm/releases/latest'
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    version = data['tag_name']
    goblin.logger.info('Latest version: %s', version)
    return version

def _get_download_url(goblin, version, locked_data):
    """Get download URL and filename from cache or GitHub API."""
    platform_data = locked_data.get(pulsar_env.OS) if locked_data else None

    if platform_data and 'url' in platform_data and 'filename' in platform_data:
        goblin.logger.info('Using cached download URL')
        return platform_data['url'], platform_data['filename']

    goblin.logger.info('Fetching release info from GitHub API for version %s', version)
    api_url = f'https://api.github.com/repos/wez/wezterm/releases/tags/{version}'
    with urllib.request.urlopen(api_url) as response:
        release_data = json.loads(response.read().decode())

    assets = release_data['assets']

    if pulsar_env.OS == 'windows':
        asset = next((a for a in assets if 'windows' in a['name'].lower() and a['name'].endswith('.zip')), None)
    elif pulsar_env.OS == 'linux':
        asset = next((a for a in assets if 'ubuntu' in a['name'].lower() and a['name'].endswith('.AppImage')), None)
    else:
        raise ValueError(f'Unsupported platform: {pulsar_env.OS}')

    if asset is None:
        raise ValueError(f'No suitable download found for {pulsar_env.OS}')

    url = asset['browser_download_url']
    filename = asset['name']

    # Cache the download info
    if locked_data is None:
        locked_data = {}
    locked_data['version'] = version
    locked_data[pulsar_env.OS] = {'url': url, 'filename': filename}
    star_map.plot('wezterm', locked_data)

    return url, filename

def _download_file(goblin, url, download_path):
    """Download file if needed based on cache settings."""
    if goblin.no_cache_command or not download_path.exists():
        if goblin.no_cache_command:
            goblin.logger.info('no_cache enabled, redownloading')
        else:
            goblin.logger.info('Downloading %s', download_path.name)
        goblin.download(url, download_path)
    else:
        goblin.logger.info('Using cached download: %s', download_path.name)

def _install_linux(download_path, version):
    """Extract and install AppImage on Linux."""
    download_path.chmod(0o755)

    extract_dir = wezterm_book.cache_dir / f'wezterm-{version}-extracted'
    extract_dir.mkdir(exist_ok=True)

    result = subprocess.run(
        [str(download_path), '--appimage-extract'],
        cwd=extract_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f'Failed to extract AppImage: {result.stderr}')

    squashfs_root = extract_dir / 'squashfs-root'
    wezterm_bin = squashfs_root / 'usr' / 'bin' / 'wezterm'

    if not wezterm_bin.exists():
        wezterm_bin = squashfs_root / 'wezterm'

    if not wezterm_bin.exists():
        raise RuntimeError('Could not find wezterm binary in extracted AppImage')

    install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
    if install_dir.exists():
        shutil.rmtree(install_dir)
    shutil.move(str(squashfs_root), str(install_dir))

def _install_windows(goblin, download_path, version):
    """Extract and install on Windows."""
    extract_dir = pulsar_env.PULSAR_CACHE_DIR / f'wezterm-{version}'
    goblin.extract(download_path, extract_dir)

    exe_path = list(extract_dir.rglob('wezterm.exe'))[0]
    shutil.copy(exe_path, pulsar_env.PULSAR_BIN_DIR / 'wezterm.exe')

@wezterm_book.installer
def install():
    """Install Wezterm"""
    import summoning_circle

    goblin = summoning_circle.summon_goblin_worker(wezterm_book)

    if goblin.reinstall_command:
        uninstall()

    locked_data = star_map.read('wezterm')
    version = _get_version(goblin, locked_data)
    url, filename = _get_download_url(goblin, version, locked_data)

    goblin.logger.info('Installing version %s', version)

    wezterm_book.cache_dir.mkdir(exist_ok=True, parents=True)
    download_path = wezterm_book.cache_dir / filename

    _download_file(goblin, url, download_path)

    if pulsar_env.OS == 'linux':
        _install_linux(download_path, version)
    elif pulsar_env.OS == 'windows':
        _install_windows(goblin, download_path, version)

    goblin.complete()

@wezterm_book.uninstaller
def uninstall():
    """Uninstall Wezterm"""

    if pulsar_env.OS == 'linux':
        # Remove the wezterm directory
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        if install_dir.exists():
            shutil.rmtree(install_dir)
    elif pulsar_env.OS == 'windows':
        # Remove the wezterm.exe file
        exe_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm.exe'
        if exe_path.exists():
            exe_path.unlink()

@wezterm_book.typer_app.callback(invoke_without_command=True)
def launch(ctx: typer.Context):
    """Launch Wezterm terminal"""
    if ctx.invoked_subcommand is None:
        if not wezterm_book.installed_with_pulsar:
            typer.echo("Wezterm is not installed. Run 'pulsar install wezterm' first.")
            raise typer.Exit(code=1)

        # Determine the wezterm executable path
        if pulsar_env.OS == 'linux':
            wezterm_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm' / 'usr' / 'bin' / 'wezterm'
        elif pulsar_env.OS == 'windows':
            wezterm_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm.exe'
        else:
            wezterm_path = 'wezterm'

        # Launch wezterm detached from this shell session
        try:
            if pulsar_env.OS == 'windows':
                # On Windows, use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
                subprocess.Popen(
                    [str(wezterm_path)],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            else:
                # On Linux/Unix, use nohup or double fork
                subprocess.Popen(
                    [str(wezterm_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
        except Exception as e:
            typer.echo(f"Failed to launch wezterm: {e}")
            raise typer.Exit(code=1)

