import pulsar_env

def enchant_shell():
    
    output = ''
    if pulsar_env.SHELL == 'bash':
        output = _get_bash_script()
    elif pulsar_env.SHELL == 'powershell':
        output = _get_pwsh_script()
    else:
        raise EnvironmentError(f"Unsupported shell: {pulsar_env.SHELL}")

    output = output.strip()
    
    if len(output) == 0:
        return

    with open(pulsar_env.PULSAR_SHELL_FILE, 'w') as f:
        f.write(output)


def _get_bash_script() -> str:
    output = ''

    for key, val in pulsar_env.env_vars.items():
        output += f'export {key}="{val}"\n'

    for path in pulsar_env.path_entries:
        output += f'export PATH="{path}:${{PATH}}"\n'

    for file in pulsar_env.source_files:
        output += f'source "{file}"\n'

    return output


def _get_pwsh_script() -> str:
    output = ''

    for key, val in pulsar_env.env_vars.items():
        output += f'$env:{key} = "{val}"\n'

    for path in pulsar_env.path_entries:
        output += f'$env:PATH = "{path};$env:PATH"\n'

    for file in pulsar_env.source_files:
        output += f'. "{file}"\n'

    return output