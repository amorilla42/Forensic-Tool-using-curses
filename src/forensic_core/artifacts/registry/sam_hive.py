import sqlite3
from Registry import Registry
from Cryptodome.Cipher import ARC4, DES
from Cryptodome.Hash import MD5
import struct


def transform_des_key(key_7):
    key = []
    for i in range(7):
        key.append(key_7[i])
    s = bytearray(8)
    s[0] = key[0] & 0xFE
    s[1] = ((key[0] << 7) | (key[1] >> 1)) & 0xFE
    s[2] = ((key[1] << 6) | (key[2] >> 2)) & 0xFE
    s[3] = ((key[2] << 5) | (key[3] >> 3)) & 0xFE
    s[4] = ((key[3] << 4) | (key[4] >> 4)) & 0xFE
    s[5] = ((key[4] << 3) | (key[5] >> 5)) & 0xFE
    s[6] = ((key[5] << 2) | (key[6] >> 6)) & 0xFE
    s[7] = (key[6] << 1) & 0xFE
    for i in range(8):
        b = s[i]
        b = b & 0xFE
        if bin(b).count('1') % 2 == 0:
            s[i] |= 1
    return bytes(s)


def sid_to_key(rid):
    key1 = transform_des_key(struct.pack('<L', (rid & 0xFFFFFFFF) << 1)[:7])
    key2 = transform_des_key(struct.pack('<L', (((rid & 0xFFFFFFFF) << 1) | 1) & 0xFFFFFFFF)[:7])
    return key1, key2


def decrypt_hash(encrypted_hash, rid, bootkey):
    if not encrypted_hash or len(encrypted_hash) != 16:
        return None

    h = MD5.new()
    h.update(bootkey + struct.pack('<L', rid))
    rc4_key = h.digest()
    cipher = ARC4.new(rc4_key)
    obfuscated_hash = cipher.decrypt(encrypted_hash)

    des_k1, des_k2 = sid_to_key(rid)

    des1 = DES.new(des_k1, DES.MODE_ECB)
    des2 = DES.new(des_k2, DES.MODE_ECB)

    decrypted = des1.decrypt(obfuscated_hash[:8]) + des2.decrypt(obfuscated_hash[8:])
    return decrypted.hex()


def extraer_bootkey_system(path_system_hive):
    reg = Registry.Registry(path_system_hive)
    controlset = obtener_controlset_activo(reg)
    lsa_key = reg.open(f"{controlset}\\Control\\Lsa")
    parts = []
    for name in ["JD", "Skew1", "GBG", "Data"]:
        subkey = lsa_key.subkey(name)
        values = subkey.values()
        val = values[0].value() if values else b""
        parts.append(val)
    raw_bootkey = b"".join(parts)
    key_permutation = [0x8, 0x5, 0x4, 0x2, 0xB, 0x9, 0xD, 0x3,
                       0x0, 0x6, 0x1, 0xC, 0xE, 0xA, 0xF, 0x7]
    bootkey = bytearray(16)
    for i, pos in enumerate(key_permutation):
        bootkey[i] = raw_bootkey[pos]
    return bytes(bootkey)


def obtener_controlset_activo(reg):
    select_key = reg.open("Select")
    current = select_key.value("Current").value()
    return f"ControlSet{current:03d}"



def extraer_usuarios_sam(sam_hive_path, bootkey, db_path):
    reg = Registry.Registry(sam_hive_path)
    
    # Detectar si hay un contenedor raíz tipo CMI-CreateHive
    root_key = reg.root()
    subkeys = root_key.subkeys()
    real_root = None
    for sub in subkeys:
        if sub.name().startswith("CMI-CreateHive"):
            real_root = sub
            break
    if real_root is None:
        real_root = root_key

    try:
        users_key = real_root.subkey("SAM\\Domains\\Account\\Users")
    except Registry.RegistryKeyNotFoundException:
        print("No se pudo encontrar la clave de usuarios en el SAM.")
        return

    cursor = sqlite3.connect(db_path).cursor()

    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            rid INTEGER PRIMARY KEY,
            username TEXT,
            fullname TEXT,
            last_login TEXT,
            lm_hash TEXT,
            nt_hash TEXT
        )
    """)

    for user_subkey in users_key.subkeys():
        rid = int(user_subkey.name(), 16)
        v = user_subkey.value("V").value()
        # La estructura binaria de V contiene información del usuario, extraemos hashes y nombre
        # Para simplificar extraemos el nombre y hashes NT y LM
        # Aquí debes parsear bien la estructura V, aquí un ejemplo simple:
        # Offset para username (32 bytes, utf-16), lm_hash y nt_hash offsets conocidos
        try:
            username_len = int.from_bytes(v[0x0C:0x0E], "little")
            username_off = int.from_bytes(v[0x0E:0x10], "little")
            username = v[username_off:username_off + username_len].decode("utf-16le")

            lm_hash_off = int.from_bytes(v[0x9C:0xA0], "little")
            lm_hash_len = int.from_bytes(v[0xA0:0xA4], "little")
            lm_hash_enc = v[lm_hash_off:lm_hash_off + lm_hash_len]

            nt_hash_off = int.from_bytes(v[0xA4:0xA8], "little")
            nt_hash_len = int.from_bytes(v[0xA8:0xAC], "little")
            nt_hash_enc = v[nt_hash_off:nt_hash_off + nt_hash_len]

            lm_hash = decrypt_hash(lm_hash_enc, rid, bootkey)
            nt_hash = decrypt_hash(nt_hash_enc, rid, bootkey)

            # Por ejemplo, extraemos también la última hora de login en formato Windows FILETIME (8 bytes)
            last_login_raw = v[0x78:0x80]
            last_login = _filetime_to_dt(last_login_raw)

            cursor.execute("""
                INSERT OR REPLACE INTO users (rid, username, fullname, last_login, lm_hash, nt_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rid, username, username, last_login, lm_hash, nt_hash))

        except Exception as e:
            print(f"Error procesando usuario RID {rid}: {e}")

    cursor.connection.commit()
    cursor.connection.close()


def _filetime_to_dt(filetime_bytes):
    """Convierte FILETIME (Windows) a cadena ISO."""
    if len(filetime_bytes) != 8:
        return None
    ft = int.from_bytes(filetime_bytes, byteorder='little', signed=False)
    if ft == 0:
        return None
    # FILETIME es en 100 nanosegundos desde 1601-01-01
    import datetime
    us = ft / 10
    dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=us)
    return dt.isoformat()


# Uso:
# 1) extraer bootkey del SYSTEM
# 2) con bootkey y SAM, extraer usuarios y hashes desencriptados
# 3) guardar todo en la base SQLite

def extraer_sam(db_path, sam_hive_path, system_hive_path):
    bootkey = extraer_bootkey_system(system_hive_path)
    extraer_usuarios_sam(sam_hive_path, bootkey, db_path)
    # Aquí puedes agregar la lógica para analizar el archivo .reg
    
    
