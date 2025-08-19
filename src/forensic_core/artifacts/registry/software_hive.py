import os
import sqlite3
from Registry import Registry
from datetime import datetime


def _to_text_any(v):
    if isinstance(v, (bytes, bytearray)):
        for enc in ("utf-16le", "utf-8", "latin-1"):
            try:
                return v.decode(enc)
            except Exception:
                pass
        return v.hex()
    return str(v)

def _normalize_path(p):
    if p is None:
        return None
    p = str(p).strip()
    if len(p) > 1 and p[0] == p[-1] == '"':
        p = p[1:-1]              # quitar comillas envolventes
    if p in ("", "1"):
        return None
    return p




def extraer_software(software_path, db_path):
    reg = Registry.Registry(software_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    # Crear tabla de información del sistema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_info2 (
        product_name TEXT,
        product_id TEXT,
        install_date TEXT,
        registered_owner TEXT,
        computer_name TEXT
    );
    """)

    # Crear tabla de programas instalados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS installed_programs (
        name TEXT,
        version TEXT,
        publisher TEXT,
        install_date TEXT
    );
    """)

    # Crear tabla de entradas de inicio automático
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS startup_entries (
        name TEXT,
        command TEXT
    );
    """)


    # Tabla para Active Setup Installed Components
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS installed_components (
        component_id TEXT,
        stub_path TEXT,
        version TEXT, 
        is_installed TEXT,
        component_name TEXT
    );
    """)

    # Tabla para App Paths
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_paths (
        executable TEXT,
        path TEXT
    );
    """)

    # (opcional) Metadatos de App Paths: todos los valores del subkey
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_paths_meta (
        executable TEXT,
        value_name TEXT,
        value_data TEXT,
        key_path TEXT,
        timestamp TEXT
    );
    """)

    # Tabla para grupos de servicios en svchost
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS svchost_groups (
        group_name TEXT,
        services TEXT
    );
    """)





    conn.commit()

    # Información del sistema
    try:
        cv = reg.open("Microsoft\\Windows NT\\CurrentVersion")
        product_name = cv.value("ProductName").value()
        product_id = cv.value("ProductId").value()
        install_date = datetime.utcfromtimestamp(cv.value("InstallDate").value()).isoformat()
        owner = cv.value("RegisteredOwner").value()
        try:
            computer_name = reg.open("Microsoft\\Windows NT\\CurrentVersion\\Winlogon").value("DefaultDomainName").value()
        except:
            computer_name = reg.open("Microsoft\\Windows NT\\CurrentVersion\\Winlogon").value("DefaultUserName").value()
        cursor.execute("INSERT INTO system_info2 VALUES (?, ?, ?, ?, ?)",
                       (product_name, product_id, install_date, owner, computer_name))
    except Exception as e:
        print("[!] Error extrayendo system_info2:", e)

    # Programas instalados
    try:
        uninstall = reg.open("Microsoft\\Windows\\CurrentVersion\\Uninstall")
        for subkey in uninstall.subkeys():
            try:
                name = None
                version = None
                publisher = None
                install_date = None

                for val in subkey.values():
                    if val.name() == "DisplayName":
                        name = val.value()
                    elif val.name() == "DisplayVersion":
                        version = val.value()
                    elif val.name() == "Publisher":
                        publisher = val.value()
                    elif val.name() == "InstallDate":
                        install_date = val.value()

                if name:
                    cursor.execute("INSERT INTO installed_programs VALUES (?, ?, ?, ?)",
                                (name, version, publisher, install_date))
            except Exception as e:
                print(f"[!] Error procesando subkey '{subkey.name()}': {e}")
    except Exception as e:
        print("[!] Error accediendo a Uninstall:", e)

    # Programas en inicio automático
    try:
        run_key = reg.open("Microsoft\\Windows\\CurrentVersion\\Run")
        for v in run_key.values():
            value = v.value()
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            cursor.execute("INSERT INTO startup_entries VALUES (?, ?)", (v.name(), value))
    except Exception as e:
        print("[!] Error extrayendo entradas de inicio:", e)



    # Installed Components (Active Setup)
    try:
        components = reg.open("Microsoft\\Active Setup\\Installed Components")
        for sub in components.subkeys():
            comp_id = sub.name()
            stub_path = None
            version = None
            is_installed = None
            component_name = None

            for val in sub.values():
                if val.name() == "StubPath":
                    stub_path = val.value()
                elif val.name() == "Version":
                    version = val.value()
                elif val.name() == "IsInstalled":
                    is_installed = str(val.value())  # puede ser DWORD
                elif val.name() == "ComponentID":
                    component_name = val.value()

            cursor.execute("""
                INSERT INTO installed_components 
                (component_id, stub_path, version, is_installed, component_name)
                VALUES (?, ?, ?, ?, ?)
            """, (comp_id, stub_path, version, is_installed, component_name))
    except Exception as e:
        print("[!] Error extrayendo Installed Components:", e)



    # App Paths (HKLM). Incluye Wow6432Node si existe.
    try:
        for root in [
            r"Microsoft\Windows\CurrentVersion\App Paths",
            r"Wow6432Node\Microsoft\Windows\CurrentVersion\App Paths",
        ]:
            try:
                app_paths_root = reg.open(root)
            except Registry.RegistryKeyNotFoundException:
                continue

            for sub in app_paths_root.subkeys():
                exe = sub.name()
                key_path = sub.path()
                ts = sub.timestamp().isoformat()

                # 1) (Default)
                ruta = None
                try:
                    ruta = _normalize_path(_to_text_any(sub.value("").value()))
                except Exception:
                    ruta = None

                # 2) Fallback: "Path" + exe
                if not ruta:
                    try:
                        base_dir = _normalize_path(_to_text_any(sub.value("Path").value()))
                        if base_dir:
                            ruta = os.path.join(base_dir, exe)
                    except Exception:
                        pass

                # 3) Guarda fila principal (aunque ruta sea None)
                try:
                    cursor.execute("INSERT INTO app_paths (executable, path) VALUES (?, ?)", (exe, ruta))
                except Exception:
                    pass

                # 4) guardar TODOS los valores como metadatos
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_paths_meta'")
                    if cursor.fetchone():
                        for v in sub.values():
                            vname = v.name() if v.name() else "(Default)"
                            vdata = _to_text_any(v.value())
                            cursor.execute("""
                                INSERT INTO app_paths_meta (executable, value_name, value_data, key_path, timestamp)
                                VALUES (?, ?, ?, ?, ?)
                            """, (exe, vname, vdata, key_path, ts))
                except Exception:
                    pass
    except Exception as e:
        print("[!] Error extrayendo App Paths:", e)


    # SvcHost groups
    try:
        svchost = reg.open("Microsoft\\Windows NT\\CurrentVersion\\SvcHost")
        for v in svchost.values():
            group_name = v.name()
            services = ", ".join(v.value()) if isinstance(v.value(), list) else str(v.value())
            cursor.execute("INSERT INTO svchost_groups VALUES (?, ?)", (group_name, services))
    except Exception as e:
        print("[!] Error extrayendo SvcHost groups:", e)

    conn.commit()
    conn.close()
  