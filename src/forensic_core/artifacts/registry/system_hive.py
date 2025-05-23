import sqlite3
from Registry import Registry
from datetime import datetime, timezone

from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.system_info_view import SystemInfoViewer

def extraer_system(db_path, hive_path):

    def get_value_safe(key, val_name):
        try:
            val = key.value(val_name)
            if val is not None:
                v = val.value()
                if isinstance(v, list):
                    # convierte lista a string separada por "; "
                    return "; ".join(str(x) for x in v)
                return v
        except Exception:
            pass
        return None

    def filetime_bin_to_dt(bin_val):
        import struct
        if isinstance(bin_val, bytes) and len(bin_val) == 8:
            # unpack little endian unsigned long long
            ft, = struct.unpack('<Q', bin_val)
            # convertir FILETIME a timestamp unix
            us = (ft - 116444736000000000) / 10_000_000
            if us < 0:
                return None
            dt = datetime.fromtimestamp(us, tz=timezone.utc)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return None

   
    def get_system_info_data(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Puedes ajustar esto según cómo estés guardando la info
        cursor.execute("SELECT last_boot_time FROM system_info ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        metadata = {"last_boot_time": row[0] if row else "N/A"}

        cursor.execute("SELECT service_name, display_name, image_path, start_type, service_type FROM system_services")
        services = [f"{s[0]} ({s[1]}) - {s[2]} [start={s[3]}, type={s[4]}]" for s in cursor.fetchall()]

        cursor.execute("SELECT device_class, device_id, friendly_name, device_desc FROM usb_devices")
        usb_devices = [f"{d[0]} | {d[1]} | {d[2]} | {d[3]}" for d in cursor.fetchall()]

        cursor.execute("SELECT scheme_name, friendly_name FROM power_schemes")
        power = [f"{p[0]} - {p[1]}" for p in cursor.fetchall()]

        conn.close()
        return metadata, services, usb_devices, power


    try:
        reg = Registry.Registry(hive_path)

        # Obtener número actual de ControlSet
        select_key = reg.open("Select")
        current = select_key.value("Current").value()
        current_control_set = f"ControlSet00{current}"

        # Última hora de arranque del sistema (LastBootTime)
        last_boot_time = None
        try:
            shutdown_key = reg.open(f"{current_control_set}\\Control\\Windows")
            shutdown_val = shutdown_key.value("ShutdownTime").value()
            last_boot_time = filetime_bin_to_dt(shutdown_val)
        except Exception:
            last_boot_time = None

        # Servicios y drivers (HKLM\SYSTEM\ControlSet00X\Services)
        servicios = []
        try:
            services_key = reg.open(f"{current_control_set}\\Services")
            for service in services_key.subkeys():
                name = service.name()
                start_type = get_value_safe(service, "Start")
                image_path = get_value_safe(service, "ImagePath")
                display_name = get_value_safe(service, "DisplayName")
                service_type = get_value_safe(service, "Type")
                servicios.append((name, start_type, service_type, image_path, display_name))
        except Exception:
            pass

        # Dispositivos Plug and Play (HKLM\SYSTEM\ControlSet00X\Enum\USB)
        dispositivos_usb = []
        try:
            enum_usb_key = reg.open(f"{current_control_set}\\Enum\\USB")
            for device_class in enum_usb_key.subkeys():
                for device_id in device_class.subkeys():
                    friendly_name = get_value_safe(device_id, "FriendlyName")
                    device_desc = get_value_safe(device_id, "DeviceDesc")
                    dispositivos_usb.append((device_class.name(), device_id.name(), friendly_name, device_desc))
        except Exception:
            pass

        # Perfiles de energía (HKLM\SYSTEM\ControlSet00X\Control\Power\User\PowerSchemes)
        power_schemes = []
        try:
            power_key = reg.open(f"{current_control_set}\\Control\\Power\\User\\PowerSchemes")
            for scheme in power_key.subkeys():
                scheme_name = scheme.name()
                friendly_name = get_value_safe(scheme, "FriendlyName")
                power_schemes.append((scheme_name, friendly_name))
        except Exception:
            pass

        # Guardar en la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        row = cursor.execute(
            "SELECT entry_id FROM filesystem_entry WHERE type != 'dir' AND full_path LIKE ?", 
            ('%' + 'Windows/System32/config/SYSTEM',)
        ).fetchone()
        if not row:
            conn.close()
            return
        entry_id = row[0]

        # Crear tablas si no existen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                last_boot_time TEXT,
                FOREIGN KEY(entry_id) REFERENCES filesystem_entry(entry_id)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                service_name TEXT,
                start_type INTEGER,
                service_type INTEGER,
                image_path TEXT,
                display_name TEXT,
                FOREIGN KEY(entry_id) REFERENCES filesystem_entry(entry_id)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usb_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                device_class TEXT,
                device_id TEXT,
                friendly_name TEXT,
                device_desc TEXT,
                FOREIGN KEY(entry_id) REFERENCES filesystem_entry(entry_id)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_schemes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                scheme_name TEXT,
                friendly_name TEXT,
                FOREIGN KEY(entry_id) REFERENCES filesystem_entry(entry_id)
            );
        """)

        # Limpiar tablas antes de insertar nuevos datos
        # Eliminar registros antiguos si se quiere reextraer
        cursor.execute("DELETE FROM system_info WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM system_services WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM usb_devices WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM power_schemes WHERE entry_id = ?", (entry_id,))



        # Insertar datos
        cursor.execute("INSERT INTO system_info (entry_id, last_boot_time) VALUES (?, ?);", (entry_id, last_boot_time))
        for s in servicios:
            cursor.execute(
                "INSERT INTO system_services (entry_id, service_name, start_type, service_type, image_path, display_name) VALUES (?, ?, ?, ?, ?, ?);",
                (entry_id, s[0], s[1], s[2], s[3], s[4])
            )
        for d in dispositivos_usb:
            cursor.execute(
                "INSERT INTO usb_devices (entry_id, device_class, device_id, friendly_name, device_desc) VALUES (?, ?, ?, ?, ?);",
                (entry_id, d[0], d[1], d[2], d[3])
            )
        for p in power_schemes:
            cursor.execute(
                "INSERT INTO power_schemes (entry_id, scheme_name, friendly_name) VALUES (?, ?, ?);",
                (entry_id, p[0], p[1])
            )

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"[!] Error al procesar SYSTEM: {e}")

    


    metadata, services, usb_devices, power = get_system_info_data(db_path)
    system_info = {
    "last_boot_time": metadata.get("last_boot_time", "Desconocido"),
    "services": services,
    "usb_devices": usb_devices,
    "power_schemes": power
    }


    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Información del Sistema")
    layout.change_footer("Presiona TAB para alternar entre ventanas, 1-4 elegir ventana, ESC para salir")
    
    SystemInfoViewer(system_info, layout.body_win).render()

