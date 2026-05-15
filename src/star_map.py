import tomllib

import pulsar_env

STAR_MAP_PATH = pulsar_env.PULSAR_ROOT / 'star_map.toml'

def _format_toml_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        items = ', '.join(_format_toml_value(v) for v in value)
        return f'[{items}]'
    else:
        return f'"{value}"'

def _write_toml_section(data: dict, file, prefix=''):
    # First write non-dict values
    for key, value in data.items():
        if not isinstance(value, dict):
            file.write(f'{key} = {_format_toml_value(value)}\n')

    # Then write nested dictionaries as subsections
    for key, value in data.items():
        if isinstance(value, dict):
            section_name = f'{prefix}.{key}' if prefix else key
            file.write(f'\n[{section_name}]\n')
            _write_toml_section(value, file, section_name)

def _write_toml(data: dict, file):
    for key, value in data.items():
        if isinstance(value, dict):
            file.write(f'[{key}]\n')
            _write_toml_section(value, file, key)
            file.write('\n')
        else:
            file.write(f'{key} = {_format_toml_value(value)}\n')

def plot(entry: str, data: dict):
    # Read existing data
    if STAR_MAP_PATH.exists():
        with open(STAR_MAP_PATH, 'rb') as f:
            star_map = tomllib.load(f)
    else:
        star_map = {}

    # Update with new entry
    star_map[entry] = data

    # Write back to file
    STAR_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STAR_MAP_PATH, 'w') as f:
        _write_toml(star_map, f)

def read(entry: str) -> dict | None:
    if not STAR_MAP_PATH.exists():
        return None

    with open(STAR_MAP_PATH, 'rb') as f:
        star_map = tomllib.load(f)

    return star_map.get(entry)