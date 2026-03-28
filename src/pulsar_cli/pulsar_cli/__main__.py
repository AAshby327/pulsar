"""Main CLI entry point for pulsar package manager."""

import sys
from pathlib import Path

# Add fallback for tomllib on Python < 3.11
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli package required for Python < 3.11")
        print("Install with: pip install tomli")
        sys.exit(1)

try:
    import typer
    from typing_extensions import Annotated
except ImportError:
    print("Error: typer package not found")
    print("This usually means the CLI tool needs to be installed via UV")
    print("\nPlease run from the Pulsar root directory:")
    print("  ./bin/uv tool install --editable ./src/pulsar_cli")
    sys.exit(1)

from pulsar_cli.package_manager import (
    install_package,
    uninstall_package,
    list_packages,
    list_available_packages,
    list_installed_packages,
    clear_cache,
    reset_data,
    install_required_packages,
)

app = typer.Typer(
    name="pulsar",
    help="Package manager for Pulsar portable development environment",
    add_completion=False,
)


@app.command()
def install(
    package: Annotated[str, typer.Argument(help="Name of the package to install")]
):
    """Install a package (tool, LSP, or plugin)."""
    install_package(package)


@app.command()
def uninstall(
    package: Annotated[str, typer.Argument(help="Name of the package to uninstall")]
):
    """Uninstall a package."""
    uninstall_package(package)


@app.command()
def list(
    available: Annotated[
        bool, typer.Option("--available", "-a", help="Show only available packages")
    ] = False,
    installed: Annotated[
        bool, typer.Option("--installed", "-i", help="Show only installed packages")
    ] = False,
):
    """List packages (both available and installed by default)."""
    if available and not installed:
        list_available_packages()
    elif installed and not available:
        list_installed_packages()
    else:
        list_packages()


@app.command()
def info(
    package: Annotated[str, typer.Argument(help="Name of the package")]
):
    """Show detailed information about a package."""
    from pulsar_cli.package_manager import get_database, load_package_catalog
    from pulsar_cli.platform_detect import get_platform

    try:
        catalog = load_package_catalog()
        packages = catalog.get("packages", {})

        if package not in packages:
            typer.echo(f"✗ Package '{package}' not found in catalog")
            raise typer.Exit(1)

        pkg_info = packages[package]
        db = get_database()
        is_installed = db.is_installed(package)

        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"  {package}")
        typer.echo(f"{'=' * 60}\n")
        typer.echo(f"Description:  {pkg_info.get('description', 'No description')}")
        typer.echo(f"Type:         {pkg_info.get('type', 'unknown')}")
        typer.echo(f"Category:     {pkg_info.get('category', 'unknown')}")
        typer.echo(f"Installed:    {'Yes ✓' if is_installed else 'No'}")

        if is_installed:
            pkg_data = db.get_package(package)
            if pkg_data:
                _, version, _, _, installed_at = pkg_data
                typer.echo(f"Version:      {version}")
                typer.echo(f"Installed at: {installed_at}")

        # Show platform availability
        os_type, arch = get_platform()

        if pkg_info.get("type") == "nvim_plugin":
            typer.echo(f"\nRepository:   {pkg_info.get('repo', 'N/A')}")
            if "tag" in pkg_info:
                typer.echo(f"Tag:          {pkg_info['tag']}")
            if "branch" in pkg_info:
                typer.echo(f"Branch:       {pkg_info['branch']}")
        elif pkg_info.get("install_method") == "uv_tool":
            typer.echo(f"\nInstall via:  UV tool")
            typer.echo(f"UV package:   {pkg_info.get('uv_package', package)}")
        elif os_type in pkg_info and arch in pkg_info[os_type]:
            platform_info = pkg_info[os_type][arch]
            typer.echo(f"\nDownload URL: {platform_info.get('url', 'N/A')}")
            typer.echo(f"Format:       {platform_info.get('archive_format', 'N/A')}")
        else:
            typer.echo(f"\n⚠ Not available for {os_type} {arch}")

        typer.echo()

    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def version():
    """Show pulsar CLI version."""
    from pulsar_cli import __version__
    typer.echo(f"pulsar v{__version__}")


@app.command(name="clear-cache")
def clear_cache_cmd():
    """Clear downloaded files cache."""
    clear_cache()


@app.command()
def reset(
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation prompt")
    ] = False,
):
    """Reset all data (uninstall all packages and clear cache)."""
    if not force:
        typer.echo("⚠️  WARNING: This will uninstall all packages and clear the cache!")
        typer.echo("   You can reinstall packages later with 'pulsar install <package>'")
        typer.echo()
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    reset_data()


@app.command()
def bootstrap():
    """Install all required packages (wezterm, neovim, etc.)."""
    install_required_packages()


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
