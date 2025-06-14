import curses
import os
import sqlite3
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

# Convert FILETIME (Windows timestamp) to ISO format
def filetime_to_dt(filetime):
    try:
        return str(datetime(1601, 1, 1) + timedelta(microseconds=filetime // 10))
    except Exception:
        return None

# Extraer todos los artefactos relevantes de NTUSER.DAT
def extraer_ntuser_artefactos(ntuser_path, db_path):
    username = os.path.basename(ntuser_path).replace("_NTUSER.DAT", "")
    reg = Registry.Registry(ntuser_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


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
                run_count = int.from_bytes(data[4:8], byteorder='little', signed=False)
                timestamp_raw = int.from_bytes(data[8:16], byteorder='little', signed=False)
                timestamp = filetime_to_dt(timestamp_raw)
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

    conn.commit()
    conn.close()
    print(f"[+] Extracción completada para {username}")


def visualizar_resumen_usuarios(db_path, dir_exportar):

    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Informacion general de los usuarios disponibles")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver resumen de usuario")
    view = UserntDataViewer(layout.body_win, db_path, dir_exportar)
    view.render()
    view.win.keypad(True)
    while True:
        view.render()
        key = layout.win.getch()
        if key in [27, ord('q')]:
            break
        view.handle_input(key)
