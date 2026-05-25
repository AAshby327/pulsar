import pulsar_env

def enchant_shell():
    
    output = ''
    if pulsar_env.SHELL == 'bash':
        output = _get_bash_script()
    elif pulsar_env.SHELL == 'powershell':
        output = _get_pwsh_script()
    else:
        raise EnvironmentError(f"Unsupported shell type: {pulsar_env.SHELL}")

    if len(output) == 0:
        return
    
    print(pulsar_env.OUTPUT_DELIMITER)
    print(output)
    print(pulsar_env.OUTPUT_DELIMITER)


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