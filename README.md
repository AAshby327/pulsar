# Pulsar - Portable WezTerm + Neovim Environment

Pulsar is a fully portable, self-contained development environment featuring WezTerm and Neovim. Install it on any Linux or Windows computer, and uninstall by simply deleting the directory.

## Features

- **Fully Portable**: Everything installs within the repository directory
- **Cross-Platform**: Works on Linux and Windows without modifications
- **Zero System Pollution**: No PATH modifications or system-wide installations
- **Easy Uninstall**: Just delete the directory when done
- **Package Management**: Built-in CLI for managing tools, LSPs, and plugins
- **Modern Stack**: WezTerm, Neovim, UV package manager

## Quick Start

### Installation

1. **Clone this repository**:
   ```bash
   git clone <repository-url> pulsar
   cd pulsar
   ```

2. **Run the installer**:
   ```bash
   # Linux/macOS
   python install.py

   # Windows
   python install.py
   ```

3. **Launch the environment**:
   ```bash
   # Linux/macOS
   ./launch.sh

   # Windows
   .\launch.ps1
   ```

That's it! WezTerm will open with Neovim pre-configured.

## Usage

### Launching the Environment

**Linux/macOS**:
```bash
./launch.sh
```

**Windows**:
```powershell
.\launch.ps1
```

### Activating in Your Current Shell

If you want to use the tools in your existing terminal without launching WezTerm:

**Linux/macOS**:
```bash
source ./activate.sh
```

**Windows**:
```powershell
. .\activate.ps1
```

### Package Management

Pulsar includes a CLI tool for managing optional packages:

```bash
# List all packages
pulsar list

# Install a tool
pulsar install ripgrep
pulsar install fd
pulsar install fzf

# Install an LSP
pulsar install lua-language-server
pulsar install pyright

# Install a Neovim plugin
pulsar install telescope.nvim
pulsar install nvim-lspconfig

# Show package info
pulsar info ripgrep

# Uninstall a package
pulsar uninstall ripgrep

# Show version
pulsar version

# Clear download cache (frees up space)
pulsar clear-cache

# Reset everything (uninstall all packages + clear cache)
pulsar reset              # Interactive confirmation
pulsar reset --force      # Skip confirmation
```

## Available Packages

### Tools
- **ripgrep** - Fast grep replacement (rg)
- **fd** - Fast find replacement
- **fzf** - Fuzzy finder
- **bat** - Cat with syntax highlighting
- **eza** - Modern ls replacement
- **delta** - Better git diff viewer

### Language Servers (LSPs)
- **lua-language-server** - Lua LSP
- **pyright** - Python LSP
- **rust-analyzer** - Rust LSP

### Neovim Plugins
- **telescope.nvim** - Fuzzy finder
- **plenary.nvim** - Lua utilities
- **nvim-treesitter** - Syntax highlighting
- **nvim-lspconfig** - LSP configuration
- **mason.nvim** - LSP installer
- **nvim-cmp** - Autocompletion
- **tokyonight.nvim** - Colorscheme
- **neo-tree.nvim** - File explorer
- **gitsigns.nvim** - Git decorations
- And many more!

## Directory Structure

```
pulsar/
├── install.py              # Main installer
├── launch.sh/ps1           # Launch WezTerm
├── activate.sh/ps1         # Activate environment in current shell
├── bin/                    # All executables (wezterm, nvim, etc.)
├── .cache/                 # Download cache
├── .config/                # Configuration files
│   ├── wezterm/
│   ├── nvim/
│   └── pulsar/
├── .local/                 # Application data
└── src/                    # CLI tool source code
```

## Configuration

### WezTerm

Edit `.config/wezterm/wezterm.lua` to customize WezTerm settings.

### Neovim

- Main config: `.config/nvim/init.lua`
- Plugin config: `.config/nvim/lua/plugins.lua`

Neovim uses [lazy.nvim](https://github.com/folke/lazy.nvim) for plugin management. Plugins added via `pulsar install` are automatically configured.

## Requirements

- **Python 3.9+** (for running install.py)
- **Git** (for cloning plugins)
- **curl** (for downloading binaries)
- **Internet connection** (for initial installation)

## Platform Support

| Platform | Status |
|----------|--------|
| Linux x86_64 | ✅ Fully supported |
| Windows x86_64 | ✅ Fully supported |
| Linux ARM64 | ⚠️ Partial (some packages unavailable) |
| Windows ARM64 | ⚠️ Partial (some packages unavailable) |
| macOS | ❌ Not yet implemented |

## Uninstallation

Simply delete the pulsar directory:

```bash
# Linux/macOS
rm -rf pulsar/

# Windows
Remove-Item -Recurse -Force pulsar\
```

Everything is self-contained, so there's nothing else to clean up!

## Troubleshooting

### "UV not found"

Make sure UV was installed correctly:
```bash
./bin/uv --version
```

If missing, run the UV installer:
```bash
# Linux/macOS
./install_uv.sh

# Windows
.\install_uv.ps1
```

### "WezTerm won't start"

Check that WezTerm was downloaded:
```bash
# Linux
ls -lh bin/wezterm

# Windows
dir bin\wezterm.exe
```

Try running it directly:
```bash
./bin/wezterm --version
```

### "Neovim plugins not installing"

Make sure you have Git installed and accessible. Plugins are installed by lazy.nvim when you first open Neovim.

### AppImage won't run on Linux

If you see "FUSE not found" errors, extract the AppImage manually:
```bash
./bin/wezterm --appimage-extract
./bin/nvim --appimage-extract
```

## Development

### Adding New Packages

Edit `.config/pulsar/packages.toml` to add new package definitions:

```toml
[packages.mypackage]
description = "My awesome package"
type = "binary"
category = "tool"

[packages.mypackage.linux.x86_64]
url = "https://github.com/example/mypackage/releases/download/v1.0.0/mypackage-linux.tar.gz"
archive_format = "tar.gz"
binary_path = "mypackage"
```

### Modifying the CLI

The CLI source is in `src/pulsar_cli/`. After making changes, reinstall it:

```bash
./bin/uv tool install --force --editable ./src/pulsar_cli
```

## License

MIT

## Contributing

Contributions welcome! Feel free to open issues or submit pull requests.
