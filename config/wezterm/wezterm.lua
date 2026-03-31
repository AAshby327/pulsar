local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- Set up Pulsar environment variables
-- Try to detect PULSAR_ROOT from environment first
local pulsar_root = os.getenv('PULSAR_ROOT')

-- If not set, try to infer from config directory
-- This config is in PULSAR_ROOT/.config/wezterm/wezterm.lua
-- So we go up two directories from XDG_CONFIG_HOME
if not pulsar_root then
  local xdg_config = os.getenv('XDG_CONFIG_HOME')
  if xdg_config then
    -- Remove trailing slash if present
    xdg_config = xdg_config:gsub('/$', '')
    -- Go up one level from .config to get PULSAR_ROOT
    pulsar_root = xdg_config:match('(.*)/.config$') or xdg_config .. '/..'
  else
    -- Last resort: assume ~/.pulsar
    pulsar_root = wezterm.home_dir .. '/.pulsar'
  end
end

-- Add Pulsar bin directories to PATH
local path_sep = ':'
if wezterm.target_triple:find('windows') then
  path_sep = ';'
end

local pulsar_bin = pulsar_root .. '/bin'
local pulsar_local_bin = pulsar_root .. '/.local/bin'

-- Set environment variables for the shell
config.set_environment_variables = {
  PULSAR_ROOT = pulsar_root,
  PULSAR_BIN_DIR = pulsar_bin,
  PULSAR_CONFIG_DIR = pulsar_root .. '/.config',
  PULSAR_CACHE_DIR = pulsar_root .. '/.cache',
  PULSAR_DATA_DIR = pulsar_root .. '/.local/share',
  PULSAR_STATE_DIR = pulsar_root .. '/.local/state',
  XDG_CONFIG_HOME = pulsar_root .. '/.config',
  XDG_CACHE_HOME = pulsar_root .. '/.cache',
  XDG_DATA_HOME = pulsar_root .. '/.local/share',
  XDG_STATE_HOME = pulsar_root .. '/.local/state',
  PATH = pulsar_bin .. path_sep .. pulsar_local_bin .. path_sep .. os.getenv('PATH'),
}

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
