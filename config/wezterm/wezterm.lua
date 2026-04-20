local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- Detect platform
local is_windows = wezterm.target_triple:find('windows') ~= nil

-- Set up Pulsar environment variables
-- Try to detect PULSAR_ROOT from environment first
local pulsar_root = os.getenv('PULSAR_ROOT')

-- If not set, try to infer from config directory
if not pulsar_root then
  local xdg_config = os.getenv('XDG_CONFIG_HOME')
  if xdg_config then
    -- Remove trailing slash/backslash if present
    xdg_config = xdg_config:gsub('[/\\]$', '')
    -- Go up one level from .config to get PULSAR_ROOT
    pulsar_root = xdg_config:match('(.*)[\\/]%.?config$') or xdg_config .. '/..'
  else
    -- Last resort
    if is_windows then
      pulsar_root = wezterm.home_dir .. '\\pulsar'
    else
      pulsar_root = wezterm.home_dir .. '/.pulsar'
    end
  end
end

-- Set path separator and directory separator based on platform
local path_sep = is_windows and ';' or ':'
local dir_sep = is_windows and '\\' or '/'

local pulsar_bin = pulsar_root .. dir_sep .. 'bin'
local pulsar_local_bin = pulsar_root .. dir_sep .. '.local' .. dir_sep .. 'bin'

-- Set environment variables for the shell
config.set_environment_variables = {
  PULSAR_ROOT = pulsar_root,
  PULSAR_BIN_DIR = pulsar_bin,
  PULSAR_CONFIG_DIR = pulsar_root .. dir_sep .. 'config',
  PULSAR_CACHE_DIR = pulsar_root .. dir_sep .. '.cache',
  PULSAR_DATA_DIR = pulsar_root .. dir_sep .. '.local' .. dir_sep .. 'share',
  PULSAR_STATE_DIR = pulsar_root .. dir_sep .. '.local' .. dir_sep .. 'state',
  XDG_CONFIG_HOME = pulsar_root .. dir_sep .. 'config',
  XDG_CACHE_HOME = pulsar_root .. dir_sep .. '.cache',
  XDG_DATA_HOME = pulsar_root .. dir_sep .. '.local' .. dir_sep .. 'share',
  XDG_STATE_HOME = pulsar_root .. dir_sep .. '.local' .. dir_sep .. 'state',
  PATH = pulsar_bin .. path_sep .. pulsar_local_bin .. path_sep .. os.getenv('PATH'),
}

-- Configure shell to source the appropriate Pulsar activation script
if is_windows then
  -- Windows: use Pulsar's PowerShell with activation script
  local pwsh_path = pulsar_bin .. dir_sep .. 'pwsh' .. dir_sep .. 'pwsh.exe'
  local activate_path = pulsar_root .. dir_sep .. 'activate.ps1'

  -- Check if Pulsar PowerShell exists, otherwise fall back to system PowerShell
  local pwsh_exists = false
  local f = io.open(pwsh_path, "r")
  if f ~= nil then
    io.close(f)
    pwsh_exists = true
  end

  if pwsh_exists then
    config.default_prog = { pwsh_path, '-NoLogo', '-NoExit', '-Command', '. "' .. activate_path .. '"' }
  else
    -- Fallback to system PowerShell
    config.default_prog = { 'powershell.exe', '-NoExit', '-File', activate_path }
  end
  -- Alternative for cmd.exe: { 'cmd.exe', '/k', pulsar_root .. dir_sep .. 'activate.bat' }
else
  -- Linux/Mac: use bash with rcfile
  local activate_path = pulsar_root .. dir_sep .. 'activate'
  config.default_prog = { '/bin/bash', '--rcfile', activate_path }
end

-- Color scheme
config.color_scheme = 'Tokyo Night'

-- Font configuration
config.font_size = 11.0

-- Window settings
config.window_padding = {
  left = 5,
  right = 5,
  top = 5,
  bottom = 5,
}

-- Tab bar
config.hide_tab_bar_if_only_one_tab = true
config.use_fancy_tab_bar = false

-- Performance
config.front_end = "WebGpu"

return config