
import pulsar_env

def enchant_shell():
    
    output = _get_bash_script() \
    if pulsar_env.SHELL == 'bash' \
    else _get_pwsh_script()

    if len(output) == 0:
        return
    
    print(pulsar_env.OUTPUT_DELIMITER)
    print(output)
    print(pulsar_env.OUTPUT_DELIMITER)


def _get_bash_script() -> str:
    return ''


def _get_pwsh_script() -> str:
    return ''