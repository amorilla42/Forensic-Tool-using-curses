import sqlite3
from Registry import Registry
from datetime import datetime, timezone

from curses_ui.awesome_layout import AwesomeLayout


def extraer_system(db_path, hive_path):

# ---- funciones de normalización y sospecha de servicios ----
    def _norm(p):
        if not p:
            return ""
        s = str(p).strip().strip('"').replace("/", "\\").lower()
        if s.startswith("\\??\\") or s.startswith("\\\\?\\"):
            s = s[4:]
        s = s.replace("%systemroot%", "\\windows")
        s = s.replace("\\systemroot\\", "\\windows\\")
        s = s.replace("%windir%", "\\windows")
        s = s.replace("%systemdrive%", "c:")
        while "\\\\" in s:
            s = s.replace("\\\\", "\\")
        return s

    def _extract_exe(img):
        if not img:
            return ""
        s = str(img).strip()
        if s.startswith('"'):
            j = s.find('"', 1)
            exe = s[1:j] if j > 1 else s.strip('"')
        else:
            exe = s.split()[0]
        return _norm(exe)

    def _is_interpreter_path(snorm):
        names = ["\\cmd.exe","\\powershell.exe","\\wscript.exe","\\cscript.exe",
                "\\rundll32.exe","\\mshta.exe","\\regsvr32.exe"]
        return any(n in snorm for n in names)

    def _is_kernel_or_fs(stype):
        try:
            v = int(stype)
        except Exception:
            return False
        return bool(v & 0x00000001) or bool(v & 0x00000002)  # Kernel / FS

    def _suspicious_reason(image_exe_norm, service_type, servicedll_norm):
        # 1) Ejecutable
        if image_exe_norm:
            if image_exe_norm.startswith("\\\\"):
                return "Ruta UNC (red) en ImagePath"
            bad_dirs = ["\\users\\","\\appdata\\","\\local settings\\","\\temp\\","\\tmp\\","\\programdata\\"]
            if any(b in image_exe_norm for b in bad_dirs):
                return "ImagePath en ubicaciones de usuario/AppData/Temp/ProgramData"
            if _is_interpreter_path(image_exe_norm):
                return "ImagePath usa intérprete/lanzador (cmd/powershell/wscript/…)"
            if _is_kernel_or_fs(service_type) and "system32\\drivers\\" not in image_exe_norm:
                return "Driver fuera de system32\\drivers\\"

        # 2) ServiceDll
        if servicedll_norm:
            if servicedll_norm.startswith("\\\\"):
                return "ServiceDll con ruta UNC (red)"
            bad_dirs = ["\\users\\","\\appdata\\","\\local settings\\","\\temp\\","\\tmp\\","\\programdata\\"]
            if any(b in servicedll_norm for b in bad_dirs):
                return "ServiceDll en ubicaciones de usuario/AppData/Temp/ProgramData"

        return None
# ---- fin funciones de normalización y sospecha de servicios ----



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
                image_exe_path TEXT,         -- ejecutable sin argumentos
                normalized_image_path TEXT,  -- ejecutable normalizado (minúsculas, variables env resueltas, etc.)
                servicedll TEXT,             -- Parameters\ServiceDll si existe
                object_name TEXT,            -- cuenta con la que corre el servicio
                description TEXT,            -- descripción del servicio
                is_svchost INTEGER,          -- 1 si image_exe_path termina en \svchost.exe
                suspicious INTEGER,          -- 1 si marcamos sospechoso
                suspicious_reason TEXT,      -- motivo de sospecha

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
        cursor.execute("DELETE FROM system_info WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM system_services WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM usb_devices WHERE entry_id = ?", (entry_id,))
        cursor.execute("DELETE FROM power_schemes WHERE entry_id = ?", (entry_id,))



        # Insertar datos
        cursor.execute("INSERT INTO system_info (entry_id, last_boot_time) VALUES (?, ?);", (entry_id, last_boot_time))
        
        try:
            services_key = reg.open(f"{current_control_set}\\Services")
            for service in services_key.subkeys():
                name         = service.name()
                start_type   = get_value_safe(service, "Start")
                service_type = get_value_safe(service, "Type")
                image_path   = get_value_safe(service, "ImagePath")
                display_name = get_value_safe(service, "DisplayName")
                object_name  = get_value_safe(service, "ObjectName")
                description  = get_value_safe(service, "Description")

                # Parameters\ServiceDll (si existe)
                try:
                    params = service.subkey("Parameters")
                    servicedll = get_value_safe(params, "ServiceDll")
                except Exception:
                    servicedll = None

                # Normalizaciones y flags
                image_exe  = _extract_exe(image_path)
                image_norm = _norm(image_exe)
                dll_norm   = _norm(servicedll) if servicedll else None
                is_svchost = 1 if image_norm.endswith("\\svchost.exe") else 0

                reason     = _suspicious_reason(image_norm, service_type, dll_norm)
                suspicious = 1 if reason else 0

                cursor.execute("""
                    INSERT INTO system_services
                        (entry_id, service_name, start_type, service_type, image_path, display_name,
                        image_exe_path, normalized_image_path, servicedll, object_name, description,
                        is_svchost, suspicious, suspicious_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry_id, name, start_type, service_type, image_path, display_name,
                    image_exe, image_norm, servicedll, object_name, description,
                    is_svchost, suspicious, reason
                ))
        except Registry.RegistryKeyNotFoundException:
            pass
        except Exception as e:
            print(f"[!] Error extrayendo Servicios: {e}")



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

    

