import curses
import os
import re
import sqlite3
import string
from Registry import Registry
from base64 import b64decode
from datetime import datetime, timedelta

from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.usernt_data_view import UserntDataViewer

# ROT13 decoder
def rot13(s):
    return s.translate(str.maketrans(
        "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz",
        "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm"))

def extract_userassist_timestamp(data: bytes) -> str | None:
    """
    Intenta extraer un FILETIME válido de los bytes del valor UserAssist.
    Prioriza data[8:16], pero también prueba data[-12:-4] si el primero es inválido.
    """
    if len(data) >= 16:
        ts_main = int.from_bytes(data[8:16], 'little')
        ts_str = filetime_to_dt(ts_main)
        if ts_str:
            return ts_str
    if len(data) >= 12:
        ts_fallback = int.from_bytes(data[-12:-4], 'little')
        ts_str = filetime_to_dt(ts_fallback)
        if ts_str:
            return ts_str
    return None

def filetime_to_dt(filetime: int) -> str | None:
    try:
        if filetime == 0:
            return None
        dt = datetime(1601, 1, 1) + timedelta(microseconds=filetime // 10)
        if not (2000 <= dt.year <= 2100):
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def extraer_nombre_archivo_de_binario(data: bytes, min_len=4) -> str | None:
    """
    Extrae un nombre de archivo válido desde un binario, o devuelve None si no se detecta nada razonable.
    """
    # Extraer ASCII legibles
    ascii_texts = re.findall(rb'[' + re.escape(string.printable.encode()) + rb']{%d,}' % min_len, data)

    # Extraer UTF-16LE legibles
    utf16_texts = re.findall((rb'(?:[' + re.escape(string.printable.encode()) + rb']\x00){%d,}' % min_len), data)

    posibles = []

    for b in ascii_texts:
        posibles.append(b.decode('ascii', errors='ignore'))

    for b in utf16_texts:
        try:
            posibles.append(b.decode('utf-16-le', errors='ignore'))
        except:
            continue

    # Buscar el primer string que parezca archivo (con extensión conocida)
    for s in sorted(posibles, key=len, reverse=True):
        if re.search(r'\.[a-zA-Z0-9]{2,4}$', s):
            return s.strip()

    return None




# Extraer todos los artefactos relevantes de NTUSER.DAT
def extraer_ntuser_artefactos(ntuser_path, db_path):
    username = os.path.basename(ntuser_path).replace("_NTUSER.DAT", "")
    reg = Registry.Registry(ntuser_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mru_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            mru_type TEXT,
            extension TEXT,
            file_name TEXT,
            key_path TEXT,
            timestamp TEXT,
            FOREIGN KEY(user) REFERENCES users(username)
        )
    ''')


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS userassist (
        guid TEXT,
        name TEXT,
        run_count INTEGER,
        last_run_time TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recent_docs (
        extension TEXT,
        document_name TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS run_mru (
        order_key TEXT,
        command TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mountpoints2 (
        key_name TEXT,
        volume_label TEXT,
        data TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS open_save_mru (
        extension TEXT,
        entry_name TEXT,
        path TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS muicache (
        entry_name TEXT,
        description TEXT,
        username TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    conn.commit()


    # si el usuario no existe, error
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        print(f"[!] Usuario {username} no encontrado en la base de datos.")
        return
    
    # USERASSIST
    try:
        userassist_root = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist")
        for guid_key in userassist_root.subkeys():
            if guid_key.name() == "Settings":
                continue
            for val in guid_key.subkey("Count").values():
                name = rot13(val.name())
                data = val.value()
                if name.startswith("Microsoft.Autogenerated") or name.strip() == "":
                    continue
                run_count = 0
                timestamp = None

                if len(data) >= 8:
                    run_count = int.from_bytes(data[4:8], byteorder='little')
                
                timestamp = extract_userassist_timestamp(data)

                cursor.execute("INSERT INTO userassist VALUES (?, ?, ?, ?, ?)",
                               (guid_key.name(), name, run_count, timestamp, username))
    except Exception as e:
        print(f"[!] Error extrayendo UserAssist: {e}")

    # RECENT DOCS
    try:
        recent = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RecentDocs")
        for sub in recent.subkeys():
            ext = sub.name()
            for val in sub.values():
                if val.name() != "MRUList":
                    doc = val.value()
                    if isinstance(doc, bytes):
                        try:
                            doc = doc.decode("utf-16le").split('\x00')[0]
                        except:
                            doc = None
                    cursor.execute("INSERT INTO recent_docs VALUES (?, ?, ?)", (ext, doc, username))
    except Exception as e:
        print(f"[!] Error extrayendo RecentDocs: {e}")

    # RUNMRU
    try:
        runmru = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU")
        for val in runmru.values():
            if val.name() != "MRUList":
                cursor.execute("INSERT INTO run_mru VALUES (?, ?, ?)", (val.name(), val.value(), username))
    except Exception as e:
        print(f"[!] Error extrayendo RunMRU: {e}")

    # MOUNTPOINTS2
    try:
        mp2 = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\MountPoints2")
        for sub in mp2.subkeys():
            vol = sub.name()
            label, data = None, None
            for val in sub.values():
                if val.name().lower() == "_label":
                    label = val.value()
                elif val.name() == "_Data":
                    data = val.value()
            cursor.execute("INSERT INTO mountpoints2 VALUES (?, ?, ?, ?)", (vol, label, data, username))
    except Exception as e:
        print(f"[!] Error extrayendo MountPoints2: {e}")


    # LASTVISITEDMRU 
    try:
        last_visited = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\LastVisitedMRU")
        for val in last_visited.values():
            if val.name() != "MRUList":
                try:
                    entry_name = val.name()
                    path = val.value()
                    if isinstance(path, bytes):
                        path = path.decode("utf-16le", errors='ignore').split('\x00')[0]
                    cursor.execute("INSERT INTO open_save_mru VALUES (?, ?, ?, ?)",
                                ("LastVisitedMRU", entry_name, path, username))
                except Exception:
                    continue
    except Exception as e:
        print(f"[!] Error extrayendo LastVisitedMRU: {e}")


    # MUICACHE
    try:
        muicache_path = "Software\\Microsoft\\Windows\\ShellNoRoam\\MUICache"
        muicache = reg.open(muicache_path)
        for val in muicache.values():
            cursor.execute("INSERT INTO muicache VALUES (?, ?, ?)", (val.name(), val.value(), username))
    except Exception as e:
        print(f"[!] Error extrayendo MUICache: {e}")

    # OpenSavePidlMRU y LastVisitedPidlMRU
    try:
        comdlg_key = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32")
        for subkey_name in ["OpenSavePidlMRU", "LastVisitedPidlMRU"]:
            try:
                subkey = comdlg_key.subkey(subkey_name)
                for sk in subkey.subkeys():
                    ext = sk.name()
                    for val in sk.values():
                        if not val.name().startswith("MRUList"):
                            try:
                                raw_value = val.value()
                                if isinstance(raw_value, bytes):
                                    filename = extraer_nombre_archivo_de_binario(raw_value)
                                else:
                                    filename = str(raw_value)
                                cursor.execute('''
                                    INSERT INTO mru_entries (user, mru_type, extension, file_name, key_path, timestamp)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    username,
                                    subkey_name,
                                    ext,
                                    filename,
                                    sk.path(),
                                    sk.timestamp().isoformat()
                                ))
                            except Exception:
                                continue
            except Registry.RegistryKeyNotFoundException:
                continue
    except Registry.RegistryKeyNotFoundException:
        print(f"[!] MRU no encontrado para {username}")

    conn.commit()
    conn.close()
    print(f"[+] Extracción completada para {username}")

def visualizar_resumen_usuarios(db_path, dir_exportar):

    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Informacion general de los usuarios disponibles")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver resumen de usuario")
    view = UserntDataViewer(layout.body_win, db_path, dir_exportar, layout)
    view.render()
    view.win.keypad(True)
    while True:
        view.render()
        key = layout.win.getch()
        if key in [27, ord('q')]:
            layout.clear()
            
            break
        view.handle_input(key)
