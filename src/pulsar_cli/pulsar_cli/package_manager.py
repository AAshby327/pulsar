"""Package management operations."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pulsar_cli.database import PackageDatabase
from pulsar_cli.downloader import download_and_extract
from pulsar_cli.platform_detect import get_platform, get_exe_suffix, is_windows


def get_pulsar_root() -> Path:
    """Get the Pulsar root directory from environment or infer it."""
    root = os.getenv("PULSAR_ROOT")
    if root:
        return Path(root)

    # Infer from current file location
    # This file is in src/pulsar_cli/, so root is ../../
    return Path(__file__).parent.parent.parent.resolve()


def load_package_catalog() -> Dict[str, Any]:
    """Load the package catalog from packages.toml."""
    root = get_pulsar_root()
    catalog_path = root / ".config" / "pulsar" / "packages.toml"

    if not catalog_path.exists():
        raise FileNotFoundError(f"Package catalog not found: {catalog_path}")

    with open(catalog_path, "rb") as f:
        return tomllib.load(f)


def get_database() -> PackageDatabase:
    """Get the package database instance."""
    root = get_pulsar_root()
    db_path = root / ".local" / "state" / "pulsar.db"
    return PackageDatabase(db_path)


def make_executable(path: Path):
    """Make a file executable (Unix only)."""
    if not is_windows():
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)


def install_binary_package(
    name: str, pkg_info: Dict[str, Any], platform_info: Dict[str, Any]
):
    """Install a binary package."""
    root = get_pulsar_root()
    cache_dir = root / ".cache"
    bin_dir = root / "bin"

    # Download and extract
    url = platform_info["url"]
    archive_format = platform_info["archive_format"]
    binary_path = platform_info["binary_path"]

    print(f"📦 Installing {name}...")
    extract_dir = download_and_extract(url, cache_dir, archive_format)

    # Handle AppImage extraction if needed
    if archive_format == "appimage" and platform_info.get("extract_appimage", False):
        appimage_file = extract_dir / binary_path
        if not appimage_file.exists():
            # The file might be directly in extract_dir with the original name
            for f in extract_dir.iterdir():
                if f.suffix == ".AppImage" or f.name.endswith(".appimage"):
                    appimage_file = f
                    break

        if not appimage_file.exists():
            raise FileNotFoundError(f"AppImage not found in {extract_dir}")

        make_executable(appimage_file)

        # Try to run it to check if FUSE works
        try:
            subprocess.run([str(appimage_file), "--version"],
                          capture_output=True, check=True, timeout=5)
            # FUSE works, just copy the AppImage
            source_binary = appimage_file
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # FUSE doesn't work, extract the AppImage
            print("  FUSE not detected, extracting AppImage...")
            extracted_name = f"{name}-extracted"

            subprocess.run([str(appimage_file), "--appimage-extract"],
                          cwd=extract_dir, capture_output=True, check=True)

            squashfs_dir = extract_dir / "squashfs-root"
            extracted_dir = bin_dir / extracted_name

            if extracted_dir.exists():
                shutil.rmtree(extracted_dir)

            squashfs_dir.rename(extracted_dir)

            # Find the actual binary in the extracted contents
            binary_name = Path(binary_path).name
            source_binary = extracted_dir / "usr" / "bin" / binary_name

            if not source_binary.exists():
                # Try to find it
                for candidate in extracted_dir.rglob(binary_name):
                    if candidate.is_file():
                        source_binary = candidate
                        break

            # Create symlink
            dest_binary = bin_dir / binary_name
            if dest_binary.exists() or dest_binary.is_symlink():
                dest_binary.unlink()
            dest_binary.symlink_to(source_binary.relative_to(bin_dir))
            print(f"✓ Installed {name} to {dest_binary} (extracted)")

            # Record in database
            db = get_database()
            db.add_package(
                name=name,
                version=platform_info.get("version", "unknown"),
                pkg_type=pkg_info.get("type", "binary"),
                category=pkg_info.get("category", "unknown"),
                files=[str(dest_binary), str(extracted_dir)],
            )
            return
    else:
        # Find the binary in the extracted files
        # Support searching for binaries with wildcards or search_binary flag
        if platform_info.get("search_binary", False) or "*" in binary_path:
            # Search for the binary
            binary_name = Path(binary_path).name.replace("*", "")
            source_binary = None
            for candidate in extract_dir.rglob(binary_name):
                if candidate.is_file():
                    source_binary = candidate
                    break

            if not source_binary:
                raise FileNotFoundError(f"Binary {binary_name} not found in {extract_dir}")
        else:
            source_binary = extract_dir / binary_path

            if not source_binary.exists():
                raise FileNotFoundError(f"Binary not found at {source_binary}")

    # Determine destination
    # For AppImages and search_binary, use the desired binary_path name
    # For explicit paths, use the actual source binary name
    if archive_format == "appimage" or platform_info.get("search_binary", False):
        binary_name = Path(binary_path).name
    else:
        binary_name = source_binary.name
    dest_binary = bin_dir / binary_name

    # Handle extract_all for packages that need entire directory structure
    if platform_info.get("extract_all", False):
        # Copy entire directory structure from the parent of the binary
        if platform_info.get("search_binary", False):
            # For searched binaries, use the parent directory
            source_dir = source_binary.parent
        else:
            # For explicit paths, get the root directory (e.g., nvim-win64)
            source_dir = extract_dir / Path(binary_path).parent.parent

        if source_dir.exists():
            print(f"  Copying all files from {source_dir.name} to bin...")
            for item in source_dir.iterdir():
                dest = bin_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # The binary should now be directly in bin_dir
            dest_binary = bin_dir / binary_name

            # Check if it's in a bin subdirectory (like nvim-win64/bin/nvim.exe)
            if not dest_binary.exists() and (bin_dir / "bin" / binary_name).exists():
                dest_binary = bin_dir / "bin" / binary_name
    else:
        # Copy binary
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_binary, dest_binary)
        make_executable(dest_binary)

    print(f"✓ Installed {name} to {dest_binary}")

    # Record in database
    db = get_database()
    db.add_package(
        name=name,
        version=platform_info.get("version", "unknown"),
        pkg_type=pkg_info.get("type", "binary"),
        category=pkg_info.get("category", "unknown"),
        files=[str(dest_binary)],
    )


def install_uv_tool_package(name: str, pkg_info: Dict[str, Any]):
    """Install a package via UV tool install."""
    root = get_pulsar_root()
    uv_binary = root / "bin" / f"uv{get_exe_suffix()}"

    if not uv_binary.exists():
        raise FileNotFoundError("UV not found. Please run install.py first.")

    uv_package = pkg_info.get("uv_package", name)

    print(f"📦 Installing {name} via UV...")

    # Set up UV environment
    env = os.environ.copy()
    env["UV_TOOL_DIR"] = str(root / ".local" / "share" / "uv" / "tools")
    env["UV_PYTHON_INSTALL_DIR"] = str(root / ".local" / "share" / "uv" / "python")
    env["UV_CACHE_DIR"] = str(root / ".cache" / "uv")

    # Install via UV
    subprocess.run(
        [str(uv_binary), "tool", "install", uv_package],
        check=True,
        env=env,
    )

    print(f"✓ Installed {name} via UV")

    # Record in database
    db = get_database()
    tool_bin = root / ".local" / "share" / "uv" / "tools" / name / "bin" / f"{name}{get_exe_suffix()}"
    db.add_package(
        name=name,
        version="latest",
        pkg_type=pkg_info.get("type", "lsp"),
        category=pkg_info.get("category", "lsp"),
        files=[str(tool_bin)] if tool_bin.exists() else [],
    )


def install_nvim_plugin(name: str, pkg_info: Dict[str, Any]):
    """Install a Neovim plugin by updating plugins.lua."""
    root = get_pulsar_root()
    plugins_file = root / ".config" / "nvim" / "lua" / "plugins.lua"

    if not plugins_file.exists():
        raise FileNotFoundError(f"Neovim plugins file not found: {plugins_file}")

    # Read current content
    content = plugins_file.read_text()

    # Check if plugin already exists
    repo = pkg_info.get("repo")
    if not repo:
        raise ValueError(f"Plugin {name} missing 'repo' field")

    if repo in content:
        print(f"⚠ Plugin {name} already configured")
        return

    # Build plugin spec
    plugin_spec = f"  {{\n    '{repo}'"

    # Add optional fields
    if "tag" in pkg_info:
        plugin_spec += f",\n    tag = '{pkg_info['tag']}'"
    if "branch" in pkg_info:
        plugin_spec += f",\n    branch = '{pkg_info['branch']}'"
    if "build" in pkg_info:
        plugin_spec += f",\n    build = '{pkg_info['build']}'"
    if "main" in pkg_info:
        plugin_spec += f",\n    main = '{pkg_info['main']}'"
    if "dependencies" in pkg_info:
        deps = ", ".join(f"'{dep}'" for dep in pkg_info["dependencies"])
        plugin_spec += f",\n    dependencies = {{ {deps} }}"

    plugin_spec += ",\n  },"

    # Find the insertion point (before the closing braces)
    # Look for the pattern: "})" at the end
    insert_marker = "\n  -- Additional plugins will be added below by pulsar CLI"
    if insert_marker in content:
        # Insert after the marker
        content = content.replace(
            insert_marker,
            f"{insert_marker}\n{plugin_spec}"
        )
    else:
        # Fallback: insert before the closing }), {
        # Find the last occurrence of "})" and insert before it
        last_brace_idx = content.rfind("}),")
        if last_brace_idx != -1:
            content = content[:last_brace_idx] + plugin_spec + "\n" + content[last_brace_idx:]
        else:
            raise ValueError("Could not find insertion point in plugins.lua")

    # Write back
    plugins_file.write_text(content)

    print(f"✓ Added {name} to Neovim configuration")
    print("  ℹ Restart Neovim to install the plugin with lazy.nvim")

    # Record in database
    db = get_database()
    db.add_package(
        name=name,
        version=pkg_info.get("tag", pkg_info.get("branch", "latest")),
        pkg_type="nvim_plugin",
        category="plugin",
        files=[str(plugins_file)],  # Track the config file
    )


def install_package(package_name: str):
    """
    Install a package.

    Args:
        package_name: Name of the package to install
    """
    try:
        # Load catalog
        catalog = load_package_catalog()
        packages = catalog.get("packages", {})

        if package_name not in packages:
            print(f"✗ Package '{package_name}' not found in catalog")
            print("\nAvailable packages:")
            list_available_packages()
            sys.exit(1)

        # Check if already installed
        db = get_database()
        if db.is_installed(package_name):
            print(f"⚠ Package '{package_name}' is already installed")
            print("  Use 'pulsar uninstall' to remove it first")
            sys.exit(0)

        pkg_info = packages[package_name]
        pkg_type = pkg_info.get("type", "binary")

        # Handle different package types
        if pkg_type == "nvim_plugin":
            install_nvim_plugin(package_name, pkg_info)

        elif pkg_info.get("install_method") == "uv_tool":
            install_uv_tool_package(package_name, pkg_info)

        else:
            # Binary package - needs platform-specific download
            os_type, arch = get_platform()

            if os_type not in pkg_info or arch not in pkg_info[os_type]:
                print(f"✗ Package '{package_name}' not available for {os_type} {arch}")
                sys.exit(1)

            platform_info = pkg_info[os_type][arch]
            install_binary_package(package_name, pkg_info, platform_info)

        print(f"\n🎉 Successfully installed {package_name}!")

    except Exception as e:
        print(f"✗ Installation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def uninstall_package(package_name: str):
    """
    Uninstall a package.

    Args:
        package_name: Name of the package to uninstall
    """
    try:
        db = get_database()

        if not db.is_installed(package_name):
            print(f"✗ Package '{package_name}' is not installed")
            sys.exit(1)

        print(f"📦 Uninstalling {package_name}...")

        # Get package info
        pkg_info = db.get_package(package_name)
        if pkg_info:
            _, _, pkg_type, _, _ = pkg_info

            # Handle Neovim plugins specially
            if pkg_type == "nvim_plugin":
                print("  ℹ Note: Neovim plugins must be manually removed from plugins.lua")
                print("    The plugin will be removed from the database but config remains")

        # Get and delete files
        files = db.get_package_files(package_name)
        for file_path in files:
            path = Path(file_path)
            if path.exists() and path.name != "plugins.lua":  # Don't delete the config file
                path.unlink()
                print(f"  Removed: {file_path}")

        # Remove from database
        db.remove_package(package_name)

        print(f"✓ Uninstalled {package_name}")

    except Exception as e:
        print(f"✗ Uninstallation failed: {e}", file=sys.stderr)
        sys.exit(1)


def list_available_packages():
    """List all available packages in the catalog."""
    try:
        catalog = load_package_catalog()
        packages = catalog.get("packages", {})

        if not packages:
            print("No packages available")
            return

        # Group by category
        by_category: Dict[str, list] = {}
        for name, info in packages.items():
            category = info.get("category", "other")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((name, info.get("description", "No description")))

        # Print by category
        for category in sorted(by_category.keys()):
            print(f"\n{category.upper()}:")
            for name, desc in sorted(by_category[category]):
                print(f"  • {name:25} - {desc}")

    except Exception as e:
        print(f"✗ Failed to list packages: {e}", file=sys.stderr)
        sys.exit(1)


def list_installed_packages():
    """List all installed packages."""
    try:
        db = get_database()
        packages = db.list_installed()

        if not packages:
            print("No packages installed")
            print("\nTry: pulsar list")
            return

        print("Installed packages:\n")
        for name, version, pkg_type, category, installed_at in packages:
            print(f"  • {name:25} ({pkg_type})")
            print(f"    Version: {version}, Category: {category}")
            print(f"    Installed: {installed_at[:10]}")

    except Exception as e:
        print(f"✗ Failed to list installed packages: {e}", file=sys.stderr)
        sys.exit(1)


def list_packages():
    """List both available and installed packages."""
    print("=" * 60)
    print("  Available Packages")
    print("=" * 60)
    list_available_packages()

    print("\n" + "=" * 60)
    print("  Installed Packages")
    print("=" * 60)
    print()
    list_installed_packages()


def clear_cache():
    """Clear the download and extraction cache."""
    try:
        root = get_pulsar_root()
        cache_dir = root / ".cache"
        downloads_dir = cache_dir / "downloads"
        extracted_dir = cache_dir / "extracted"

        total_size = 0
        files_removed = 0
        dirs_exist = False

        # Calculate cache size
        for path in [downloads_dir, extracted_dir]:
            if path.exists():
                dirs_exist = True
                for item in path.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        files_removed += 1

        if not dirs_exist:
            print("✓ Cache directories don't exist")
            return

        if files_removed == 0:
            print("📦 Removing empty cache directories...")
            for path in [downloads_dir, extracted_dir]:
                if path.exists():
                    shutil.rmtree(path)
                    print(f"  Removed: {path}")
            print("✓ Empty cache directories removed")
            return

        # Format size
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"

        print(f"📦 Clearing cache...")
        print(f"  Found {files_removed} files ({size_str})")

        # Remove cache directories completely
        for path in [downloads_dir, extracted_dir]:
            if path.exists():
                shutil.rmtree(path)

        print(f"✓ Cache cleared! Freed {size_str}")
        print(f"  Removed: {downloads_dir}")
        print(f"  Removed: {extracted_dir}")

    except Exception as e:
        print(f"✗ Failed to clear cache: {e}", file=sys.stderr)
        sys.exit(1)


def reset_data():
    """Reset all data: uninstall all packages and clear cache."""
    try:
        root = get_pulsar_root()
        db = get_database()

        # Get list of installed packages
        packages = db.list_installed()

        if not packages:
            print("ℹ No packages installed")
        else:
            print(f"📦 Uninstalling {len(packages)} package(s)...")

            for name, _, pkg_type, _, _ in packages:
                print(f"  Removing {name}...")

                # Get and delete files
                files = db.get_package_files(name)
                for file_path in files:
                    path = Path(file_path)
                    if path.exists() and path.name != "plugins.lua":
                        try:
                            path.unlink()
                        except Exception as e:
                            print(f"    Warning: Could not remove {file_path}: {e}")

                # Remove from database
                db.remove_package(name)

            print(f"✓ Uninstalled {len(packages)} package(s)")

        # Clear cache
        print()
        clear_cache()

        # Reset database
        print()
        print("📦 Resetting database...")
        db_path = root / ".local" / "state" / "pulsar.db"
        if db_path.exists():
            db_path.unlink()
        # Recreate database
        get_database()
        print("✓ Database reset")

        print()
        print("🎉 Reset complete! Your Pulsar environment is clean.")
        print("   Use 'pulsar install <package>' to install packages again.")

    except Exception as e:
        print(f"✗ Reset failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def install_required_packages():
    """Install all packages marked as required in the catalog."""
    try:
        catalog = load_package_catalog()
        packages = catalog.get("packages", {})
        db = get_database()

        # Find required packages
        required_packages = []
        for name, pkg_info in packages.items():
            if pkg_info.get("required", False):
                if not db.is_installed(name):
                    required_packages.append(name)

        if not required_packages:
            print("✓ All required packages are already installed")
            return

        print(f"📦 Installing {len(required_packages)} required package(s)...")
        print()

        for package_name in required_packages:
            try:
                pkg_info = packages[package_name]
                pkg_type = pkg_info.get("type", "binary")

                # Handle different package types
                if pkg_type == "nvim_plugin":
                    install_nvim_plugin(package_name, pkg_info)
                elif pkg_info.get("install_method") == "uv_tool":
                    install_uv_tool_package(package_name, pkg_info)
                else:
                    # Binary package - needs platform-specific download
                    os_type, arch = get_platform()

                    if os_type not in pkg_info or arch not in pkg_info[os_type]:
                        print(f"⚠ Skipping {package_name}: not available for {os_type} {arch}")
                        continue

                    platform_info = pkg_info[os_type][arch]
                    install_binary_package(package_name, pkg_info, platform_info)

                print()

            except Exception as e:
                print(f"✗ Failed to install {package_name}: {e}")
                print()

        print("🎉 Required packages installation complete!")

    except Exception as e:
        print(f"✗ Required packages installation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
