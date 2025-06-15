import sqlite3
from Registry import Registry
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.sam_info_view import SamInfoViewer
from forensic_core.artifacts.registry.user_extractor import buscar_usuario_por_rid, extraer_usuarios



def parse_f_structure(f_value):
    import datetime

    def filetime_to_dt(ft_bytes):
        try:
            if len(ft_bytes) != 8:
                return None
            ft = int.from_bytes(ft_bytes, byteorder='little')
            if ft == 0:
                return None
            us = ft / 10
            dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=us)
            return dt.isoformat()
        except Exception as e:
            print(f"[!] Fecha inválida: {e}")
            return None


    last_login_time = filetime_to_dt(f_value[0x08:0x10])
    login_count = int.from_bytes(f_value[0x10:0x12], "little")
    account_flags = int.from_bytes(f_value[0x1C:0x20], "little")
    

    return  last_login_time, login_count, account_flags

def interpretar_flags(flags):
    return {
        "Account Disabled": bool(flags & 0x0002),
        "Password Never Expires": bool(flags & 0x0010),
        "Normal User Account": bool(flags & 0x1000),
        "Admin Account": bool(flags & 0x0200),
    }


def extraer_usuarios_sam(sam_hive_path, system_hive_path, db_path):
    try:
        reg = Registry.Registry(sam_hive_path)
        
        try:
            users_key = reg.open("SAM\\Domains\\Account\\Users")
        except Registry.RegistryKeyNotFoundException:
            print("No se pudo encontrar la clave de usuarios en el SAM.")
            return

        # Construir diccionario RID -> username
        rid_to_username = {}
        try:
            names_key = reg.open("SAM\\Domains\\Account\\Users\\Names")
            for name_subkey in names_key.subkeys():
                try:
                    rid = name_subkey.values()[0].value_type()
                    rid_to_username[rid] = name_subkey.name()
                except Exception as e:
                    continue
        except Exception as e:
            print(f"No se pudo procesar Users\\Names: {e}")


        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                rid INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                last_login TEXT,
                login_count INTEGER,
                flags INTEGER,
                account_disabled INTEGER,
                password_never_expires INTEGER,
                normal_user INTEGER,
                admin_user INTEGER,
                lm_hash TEXT,
                nt_hash TEXT,
                password_hint TEXT,
                cleartext_password TEXT
            )
        """)
        cursor.execute("DELETE FROM users")  # Limpiar tabla antes de insertar nuevos datos
        conn.commit()

        userinfo = extraer_usuarios(system_hive_path, sam_hive_path)

        for user_subkey in users_key.subkeys():
            name = user_subkey.name()
            try:
                rid = int(name, 16)
            except ValueError:
                continue
            try:
                username = rid_to_username.get(rid, "")
                v = user_subkey.value("V").value()
                f = user_subkey.value("F").value()

                last_login, login_count, flags = parse_f_structure(f)
                login_count = int.from_bytes(f[0x10:0x12], "little")

                flag_info = interpretar_flags(flags)

                user = buscar_usuario_por_rid(userinfo, rid)

                lm_hash = user['lm_hash']
                nt_hash = user['nt_hash']
                

                try:
                    hint_value = user_subkey.value("UserPasswordHint").value()
                    password_hint = hint_value.decode("utf-16le", errors="ignore") if isinstance(hint_value, bytes) else str(hint_value)
                except Exception:
                    password_hint = None

                cursor.execute("""
                    INSERT OR REPLACE INTO users (
                        rid, username, last_login, login_count,
                        flags, account_disabled, password_never_expires,
                        normal_user, admin_user,
                        lm_hash, nt_hash, password_hint, cleartext_password
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
                """, (  rid, username, last_login, login_count,
                        flags,
                        int(flag_info["Account Disabled"]),
                        int(flag_info["Password Never Expires"]),
                        int(flag_info["Normal User Account"]),
                        int(flag_info["Admin Account"]),
                        lm_hash, nt_hash, password_hint, None
                    ))


            except Exception as e:
                print(f"Error procesando usuario RID {rid}: {e}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al extraer usuarios del SAM: {e}")


def visualizar_usuarios(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        columnas = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        lista_usuarios = [dict(zip(columnas, fila)) for fila in rows]


        layout = AwesomeLayout()
        layout.render()
        layout.change_header("Usuarios extraídos del SAM")
        layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver detalles del usuario, c: Crackear contraseña")
        panel = SamInfoViewer(layout.body_win, lista_usuarios)
        panel.render()
        layout.body_win.keypad(True)
        while True:
            panel.render()
            key = layout.body_win.getch()
            if key  == 27:  # ESC
                break
            if key == ord('c'):
                layout.change_header("Crackeando contraseña...")
            panel.handle_input(key)
            if key ==ord('c'):
                layout.change_header("Usuarios extraídos del SAM")
    except Exception as e:
        print(f"Error al visualizar usuarios: {e}")
    


def extraer_sam(db_path, sam_hive_path, system_hive_path):
    extraer_usuarios_sam(sam_hive_path, system_hive_path, db_path)
    #visualizar_usuarios(db_path)

    
