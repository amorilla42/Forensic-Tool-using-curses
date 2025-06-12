import subprocess
import tempfile
import os

HASH_LM_VACIO = "aad3b435b51404eeaad3b435b51404ee"
HASH_NT_VACIO = "31d6cfe0d16ae931b73c59d7e0c089c0"

def is_hashcat_installed():
    try:
        subprocess.run(["hashcat", "--help"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        # Hashcat se ejecutó pero devolvió código de error (normal si --help se interpreta raro)
        return True


def crack_hash_with_hashcat(hash_value, mode, wordlist):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as hash_file:
        hash_file.write(hash_value + '\n')
        hash_file_path = hash_file.name

    try:
        subprocess.run([
            "hashcat", "-m", str(mode), "-a", "0", hash_file_path, wordlist, "--quiet"
        ], check=True)

        output = subprocess.check_output([
            "hashcat", "--show", "-m", str(mode), hash_file_path
        ], text=True)

        if ":" in output:
            return output.strip().split(":")[1]
        else:
            return None

    except subprocess.CalledProcessError as e:
        return None

    finally:
        os.remove(hash_file_path)


def crack_usuario(usuario, wordlist_path="rockyou.txt"):
    resultados = {}
    lm = usuario['lm_hash'].lower()
    nt = usuario['nt_hash'].lower()

    if lm != HASH_LM_VACIO:
        resultado_lm = crack_hash_with_hashcat(lm, 3000, wordlist_path)
        resultados['lm_password'] = resultado_lm if resultado_lm else "(no encontrada)"
    else:
        resultados['lm_password'] = "(vacía o no aplicable)"

    if nt != HASH_NT_VACIO:
        resultado_nt = crack_hash_with_hashcat(nt, 1000, wordlist_path)
        resultados['nt_password'] = resultado_nt if resultado_nt else "(no encontrada)"
    else:
        resultados['nt_password'] = "(vacía)"

    return resultados