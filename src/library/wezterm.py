"""A powerful cross-platform terminal emulator and multiplexer.

Written by https://github.com/wez and implemented in Rust.
"""

import shutil
import urllib.request
import json
import subprocess
import pathlib

import typer

import pulsar_env
import pulsar_console
import star_map
from spell_book_class import SpellBook
from summoning_circle.summoner_goblin_class import SummonerGoblin

wezterm_book = SpellBook('wezterm')

@wezterm_book.install.define()
def install() -> None:
    """Install Wezterm"""
    import summoning_circle

    goblin = summoning_circle.summon_goblin_worker(wezterm_book)

    if wezterm_book.is_installed():
        if goblin.reinstall_command:
            uninstall()
        else:
            goblin.logger.info("Wezterm already installed.")
            goblin.complete()
            return

    locked_data = star_map.read('wezterm')
    version = _get_version(goblin, locked_data)
    url, filename = _get_download_url(goblin, version, locked_data)

    goblin.logger.info('Installing version %s', version)

    wezterm_book.cache_dir.mkdir(exist_ok=True, parents=True)
    download_path = wezterm_book.cache_dir / filename

    _download_file(goblin, url, download_path)

    if pulsar_env.OS == 'linux':
        _install_linux(goblin, download_path, version)
    elif pulsar_env.OS == 'windows':
        _install_windows(goblin, download_path, version)

    goblin.logger.info("Wezterm installed successfully")

    goblin.complete()

@wezterm_book.uninstall.define()
def uninstall() -> None:
    """Uninstall Wezterm"""
    # Remove the wezterm directory for both Linux and Windows
    install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
    if install_dir.exists():
        pulsar_env.remove_directories(install_dir)

@wezterm_book.typer_app.callback(invoke_without_command=True)
def launch(ctx: typer.Context) -> None:
    """Launch Wezterm terminal"""
    if ctx.invoked_subcommand is None:
        if not wezterm_book.installed_with_pulsar():
            pulsar_console.console.print("Wezterm is not installed. Run 'pulsar install wezterm' first.")
            raise typer.Exit(code=1)

        # Determine the wezterm executable path
        if pulsar_env.OS == 'linux':
            wezterm_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm' / 'usr' / 'bin' / 'wezterm'
        elif pulsar_env.OS == 'windows':
            wezterm_path = pulsar_env.PULSAR_BIN_DIR / 'wezterm' / 'wezterm.exe'
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
            pulsar_console.console.print(f"Failed to launch wezterm: {e}")
            raise typer.Exit(code=1)
        
@wezterm_book.installed_with_pulsar.define()
def check_pulsar_installation() -> bool:
    """Check if wezterm is installed in pulsar bin folder."""
    if pulsar_env.OS == 'linux':
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        return install_dir.exists() and (install_dir / 'usr' / 'bin' / 'wezterm').exists()
    elif pulsar_env.OS == 'windows':
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        exe_path = install_dir / 'wezterm.exe'
        return exe_path.exists()
    return False

@wezterm_book.installed_with_system.define()
def check_system_installation() -> bool:
    """Check if wezterm is installed system-wide."""
    return shutil.which('wezterm') is not None

@wezterm_book.version.define()
def get_installed_version() -> str | None:
    """Query wezterm for its version"""
    # Try Pulsar-installed wezterm first
    wezterm_path = None
    if pulsar_env.OS == 'linux':
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        local_wezterm = install_dir / 'usr' / 'bin' / 'wezterm'
        if local_wezterm.exists():
            wezterm_path = str(local_wezterm)
    elif pulsar_env.OS == 'windows':
        install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
        local_wezterm = install_dir / 'wezterm.exe'
        if local_wezterm.exists():
            wezterm_path = str(local_wezterm)

    # Fall back to system wezterm if Pulsar version not found
    if wezterm_path is None:
        wezterm_path = 'wezterm'

    try:
        result = subprocess.run(
            [wezterm_path, '--version'],
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
        
def _get_version(goblin: SummonerGoblin, locked_data: dict | None) -> str:
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

def _get_download_url(goblin: SummonerGoblin, version: str, locked_data: dict | None) -> tuple[str, str]:
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

def _download_file(goblin: SummonerGoblin, url: str, download_path: pathlib.Path) -> None:
    """Download file if needed based on cache settings."""
    if goblin.no_cache_command or not download_path.exists():
        if goblin.no_cache_command:
            goblin.logger.info('no_cache enabled, redownloading')
        else:
            goblin.logger.info('Downloading %s', download_path.name)
        goblin.download(url, download_path)
    else:
        goblin.logger.info('Using cached download: %s', download_path.name)

def _install_linux(goblin: SummonerGoblin, download_path: pathlib.Path, version: str) -> None:
    """Extract and install AppImage on Linux."""
    goblin.logger.info('Making AppImage executable')
    download_path.chmod(0o755)

    extract_dir = wezterm_book.cache_dir / f'wezterm-{version}-extracted'
    extract_dir.mkdir(exist_ok=True)

    goblin.logger.info('Extracting AppImage to %s', extract_dir)
    result = subprocess.run(
        [str(download_path), '--appimage-extract'],
        cwd=extract_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f'Failed to extract AppImage: {result.stderr}')

    goblin.logger.info('Locating wezterm binary in extracted files')
    squashfs_root = extract_dir / 'squashfs-root'
    wezterm_bin = squashfs_root / 'usr' / 'bin' / 'wezterm'

    if not wezterm_bin.exists():
        wezterm_bin = squashfs_root / 'wezterm'

    if not wezterm_bin.exists():
        raise RuntimeError('Could not find wezterm binary in extracted AppImage')

    install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
    if install_dir.exists():
        goblin.logger.info('Removing existing installation')
        pulsar_env.remove_directories(install_dir)

    goblin.logger.info('Moving files to %s', install_dir)
    shutil.move(str(squashfs_root), str(install_dir))

def _install_windows(goblin: SummonerGoblin, download_path: pathlib.Path, version: str) -> None:
    """Extract and install on Windows."""
    extract_dir = pulsar_env.PULSAR_CACHE_DIR / f'wezterm-{version}'
    goblin.extract(download_path, extract_dir)

    # Find the directory containing wezterm.exe
    exe_path = list(extract_dir.rglob('wezterm.exe'))[0]
    source_dir = exe_path.parent

    # Install to a wezterm subdirectory to keep all files together
    install_dir = pulsar_env.PULSAR_BIN_DIR / 'wezterm'
    if install_dir.exists():
        pulsar_env.remove_directories(install_dir)
    shutil.copytree(source_dir, install_dir)
