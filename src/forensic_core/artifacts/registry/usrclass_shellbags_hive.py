import os
import sqlite3
import re
from Registry import Registry


def crear_base_datos(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shellbags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            path TEXT,
            key_path TEXT,
            timestamp TEXT,
            FOREIGN KEY(user) REFERENCES users(username)
        )
    ''')



    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traynotify_executables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            source TEXT,
            exe_name TEXT,
            extension_type TEXT,
            suspicious INTEGER,
            key_path TEXT,
            timestamp TEXT,
            FOREIGN KEY(user) REFERENCES users(username)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traynotify_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            value_name TEXT,
            data TEXT,
            key_path TEXT,
            timestamp TEXT,
            FOREIGN KEY(user) REFERENCES users(username)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS muicache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            value_name TEXT,
            value_data TEXT,
            key_path TEXT,
            timestamp TEXT,
            FOREIGN KEY(user) REFERENCES users(username)
        )
    ''')

    conn.commit()
    return conn

def _to_text(raw):
    if isinstance(raw, (bytes, bytearray)):
        for enc in ("utf-16le", "utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                pass
        return raw.hex()  # último recurso
    return str(raw)

def _limpiar_key_path_usrclass(path):
    # Reemplaza el SID_Classes por UsrClass.dat para que sea más legible en informes
    return re.sub(r"S-1-5-21-\d+-\d+-\d+-\d+_Classes", "UsrClass.dat", path)

def extraer_mui_cache_usrclass(reg, user, conn):
    cursor = conn.cursor()
    candidates = [
        r"Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
    ]
    encontrados = 0

    for muipath in candidates:
        try:
            key = reg.open(muipath)
        except Registry.RegistryKeyNotFoundException:
            continue

        encontrados += 1
        key_path = _limpiar_key_path_usrclass(key.path())
        ts = key.timestamp().isoformat()

        for val in key.values():
            name = val.name()
            if name.lower() == "langid":
                continue

            data = _to_text(val.value())
            try:
                cursor.execute('''
                    INSERT INTO muicache (user, value_name, value_data, key_path, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user, name, data, key_path, ts))
            except Exception as e:
                # No frenar por una fila problemática
                print(f"[!] MUICache: error insertando {name!r}: {e}")

    if not encontrados:
        print("[i] MUICache: no se encontró la clave en este USRCLASS.DAT")


def extraer_shellbags(reg, user, conn):
    cursor = conn.cursor()
    try:
        base_key = reg.open("Local Settings\\Software\\Microsoft\\Windows\\Shell\\BagMRU")
        procesar_bagmru(base_key, "Root", user, cursor)
    except Registry.RegistryKeyNotFoundException:
        print(f"[!] ShellBagMRU no encontrado para {user}")




def extraer_nombre_shell_item(data):
    import re
    try:
        # Buscar cadenas UTF-16LE legibles de al menos 3 caracteres
        matches = re.findall(b'(?:[\x20-\x7e]\x00){3,}', data)
        cadenas = []
        for m in matches:
            texto = m.decode('utf-16le').strip('\x00')
            if texto and not texto.startswith("::{"):  # evitar GUIDs
                cadenas.append(texto)
        if cadenas:
            # Devuelve todas concatenadas o solo la primera
            return " / ".join(cadenas)
    except:
        pass
    return None



def limpiar_key_path_shellbags_usrclass(path):
    import re
    # Sustituir cualquier SID + "_Classes" por "UsrClass.dat"
    return re.sub(
        r"S-1-5-21-\d+-\d+-\d+-\d+_Classes",
        "UsrClass.dat",
        path
    )

def procesar_bagmru(key, current_path, user, cursor):
    for value in key.values():
        if value.name() in ("NodeSlot", "MRUListEx"):
            continue
        try:
            nombre_real = extraer_nombre_shell_item(value.value())
            if not nombre_real:
                continue
            
            key_path = limpiar_key_path_shellbags_usrclass(key.path())

            cursor.execute('''
                INSERT INTO shellbags (user, path, key_path, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user, nombre_real, key_path, key.timestamp().isoformat()))
        except Exception:
            continue

    for subkey in key.subkeys():
        procesar_bagmru(subkey, f"{current_path}\\{subkey.name()}", user, cursor)





def extraer_artifactos_binarios(data, extensiones_validas=None):
    extensiones_validas = extensiones_validas or [".exe", ".dll", ".scr", ".bat", ".cmd", ".pif", ".cpl", ".lnk"]
    resultados = set()

    # Buscar strings tipo UTF-16-LE
    matches = re.findall(rb'([\x20-\x7e]\x00){3,}', data)
    for match in matches:
        try:
            s = match.decode('utf-16-le', errors='ignore').strip().lower()
            for ext in extensiones_validas:
                if ext in s:
                    # Recorta justo hasta la extensión
                    corte = s.find(ext) + len(ext)
                    resultados.add((s[:corte], ext))
                    break
        except:
            continue
    return list(resultados)

def es_sospechoso(path: str, ext: str) -> int:
    path = path.lower()
    if any(p in path for p in ['\\temp', '\\tmp', '\\appdata', '\\local settings', '\\recycler']):
        return 1
    if any(p in path for p in ['\\desktop', '\\downloads', '\\documents']):
        return 1
    if path.startswith('\\\\'):  # ruta de red
        return 1
    if ext in ['.scr', '.pif', '.bat', '.cmd', '.js', '.vbs']:
        return 1
    return 0



def extraer_traynotify(reg, user, conn):
    cursor = conn.cursor()
    try:
        tray_key = reg.open("Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify")
        timestamp = tray_key.timestamp().isoformat()
        key_path = tray_key.path()

        for val in tray_key.values():
            name = val.name()
            try:
                data = val.value()
            except Exception:
                continue

            if name in ["IconStreams", "PastIconsStream"] and isinstance(data, bytes):
                artefactos = extraer_artifactos_binarios(data)
                for path, ext in artefactos:
                    sospechoso = es_sospechoso(path, ext)
                    cursor.execute('''
                        INSERT INTO traynotify_executables (user, source, exe_name, extension_type, suspicious, key_path, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (user, name, path, ext, sospechoso, key_path, timestamp))


            elif name in ["UserStartTime", "LastAdvertisement"]:
                cursor.execute('''
                    INSERT INTO traynotify_metadata (user, value_name, data, key_path, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user, name, str(data), key_path, timestamp))

            elif name == "PromotedIconCache":
                hex_dump = data.hex() if isinstance(data, bytes) else repr(data)
                cursor.execute('''
                    INSERT INTO traynotify_metadata (user, value_name, data, key_path, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user, name, hex_dump[:5000], key_path, timestamp))

        conn.commit()

    except Registry.RegistryKeyNotFoundException:
        print(f"[!] TrayNotify no encontrado para {user}")
    except Exception as e:
        print(f"[!] Error en TrayNotify ({user}): {e}")




def extraer_usrclass(dat_path, db_path):
    reg = Registry.Registry(dat_path)
    conn = crear_base_datos(db_path)

    user_name = os.path.basename(dat_path).replace("_USRCLASS.DAT", "")


    extraer_shellbags(reg, user_name, conn)
    extraer_traynotify(reg, user_name, conn)
    extraer_mui_cache_usrclass(reg, user_name, conn)
    
    conn.commit()
    conn.close()





