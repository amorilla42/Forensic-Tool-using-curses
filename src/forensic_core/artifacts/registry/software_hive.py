import os
import sqlite3
from Registry import Registry
from datetime import datetime

def extraer_software(software_path, db_path):
    reg = Registry.Registry(software_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Eliminar todas las tablas existentes
    cursor.execute("DROP TABLE IF EXISTS system_info2;")
    cursor.execute("DROP TABLE IF EXISTS installed_programs;")
    cursor.execute("DROP TABLE IF EXISTS startup_entries;")
    cursor.execute("DROP TABLE IF EXISTS run_once_entries;")
    cursor.execute("DROP TABLE IF EXISTS installed_components;")
    cursor.execute("DROP TABLE IF EXISTS app_paths;")
    cursor.execute("DROP TABLE IF EXISTS svchost_groups;")

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


    # Tabla para RunOnce
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS run_once_entries (
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

    # Tabla para grupos de servicios en svchost
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS svchost_groups (
        group_name TEXT,
        services TEXT
    );
    """)

    # Borrar todo el contenido de las tablas
    cursor.execute("DELETE FROM system_info2;")
    cursor.execute("DELETE FROM installed_programs;")
    cursor.execute("DELETE FROM startup_entries;")
    cursor.execute("DELETE FROM run_once_entries;")
    cursor.execute("DELETE FROM installed_components;")
    cursor.execute("DELETE FROM app_paths;")
    cursor.execute("DELETE FROM svchost_groups;")




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

    # RunOnce entries
    try:
        run_once = reg.open("Microsoft\\Windows\\CurrentVersion\\RunOnce")
        for v in run_once.values():
            cursor.execute("INSERT INTO run_once_entries VALUES (?, ?)", (v.name(), v.value()))
    except Exception as e:
        print("[!] Error extrayendo RunOnce:", e)

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



    # App Paths
    try:
        app_paths = reg.open("Microsoft\\Windows\\CurrentVersion\\App Paths")
        for sub in app_paths.subkeys():
            exe = sub.name()
            path = sub.values()[0].value()
            if isinstance(path,str) and len(path)>1 and (path.startswith('"') and path.endswith('"')):
                path = path[1:-1]
            if (isinstance(path, int) and path == 1) or (isinstance(path, str) and path == "1" or path == ""):
                path = None
            cursor.execute("INSERT INTO app_paths VALUES (?, ?)", (exe, path))
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
  