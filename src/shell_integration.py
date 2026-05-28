import pulsar_env

def enchant_shell():

    # print('enchant shell called')
    
    output = ''
    if pulsar_env.SHELL == 'bash':
        output = _get_bash_script()
    elif pulsar_env.SHELL == 'powershell':
        output = _get_pwsh_script()
    else:
        raise EnvironmentError(f"Unsupported shell type: {pulsar_env.SHELL}")

    if len(output) == 0:
        return

    file_name = pulsar_env.PULSAR_SHELL_FILE

    with open(file_name, 'w') as f:
        f.write(output)


def _get_bash_script() -> str:
    output = ''

    for key, val in pulsar_env.env_vars.items():
        output += f'export {key}="{val}"\n'

    return output


def _get_pwsh_script() -> str:
    output = ''

    for key, val in pulsar_env.env_vars.items():
        output += f'$env:{key} = "{val}"\n'

    return output