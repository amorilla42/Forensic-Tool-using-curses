from Registry import Registry
import os
import pytsk3
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_menu2 import AwesomeMenu
from curses_ui.registry_viewer import RegistryViewerPanel
from forensic_core.artifacts.registry.sam_hive import extraer_sam
from forensic_core.artifacts.registry.software_hive import extraer_software
from forensic_core.artifacts.registry.system_hive import extraer_system
from forensic_core.artifacts.registry.usernt_data_hive import extraer_ntuser_artefactos, visualizar_resumen_usuarios
from forensic_core.artifacts.registry.usrclass_shellbags_hive import extraer_usrclass
from forensic_core.e01_reader import open_e01_image
import sqlite3
from pathlib import Path




#exportar todos los registros en temp
BASE_DIR_EXPORT_TEMP = "temp"
BASE_DIR_EXPORT = "exported_files"

'''
System32/config/SYSTEM	                    SYSTEM	        Información del arranque, controladores
System32/config/SOFTWARE	                SOFTWARE	    Software instalado y configuración general
System32/config/SAM	                        SAM	            Usuarios locales y contraseñas encriptadas    
Users/usuario/NTUSER.DAT	                NTUSER.DAT	    Configuración de usuario
Users/usuario/AppData/.../UsrClass.dat	    UsrClass.dat	Extensión de configuraciones de usuario
'''
# Rutas relativas y nombre de hive esperado
HIVES_SISTEMA = {
    "SYSTEM": "Windows/System32/config/system",
    "SOFTWARE": "Windows/System32/config/SOFTWARE",
    "SAM": "Windows/System32/config/SAM",
    "SECURITY": "Windows/System32/config/SECURITY",

}

# Hive de usuario se busca por nombre específico en ruta que contenga "Users"
HIVES_USUARIO = ["NTUSER.DAT", "UsrClass.dat"]


def exportar_hives_sistema(db_path, caso_dir):
    # Cargar la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for hive_name, hive_path in HIVES_SISTEMA.items():
        cursor.execute("SELECT * FROM filesystem_entry WHERE type !='dir' AND full_path LIKE ?", ('%' + hive_path,))
        results = cursor.fetchall()
        if not results:
            continue#TODO: LA BASE DE DATOS LAS PARTICIONES ESTAN CON ID 1 MENOS DE LO QUE DEBERIA
        partition_offset_sectors = cursor.execute(
            "SELECT partition_offset from partition_info WHERE partition_id = ?", (results[0][1]+1,)
        ).fetchone()[0]
        path = cursor.execute("SELECT e01_path FROM case_info").fetchall()
        exportar_registro(
            caso_dir= caso_dir,
            ewf_path=path[0][0],
            partition_offset=partition_offset_sectors,
            path=results[0][2]
        )
    
    conn.close()

def exportar_hives_usuario(db_path, caso_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for hive_name in HIVES_USUARIO:
        cursor.execute("SELECT * FROM filesystem_entry WHERE type !='dir' AND full_path LIKE ?", ('%' + hive_name,))
        results = cursor.fetchall()
        if not results:
            continue
        partition_offset_sectors = cursor.execute(
            "SELECT partition_offset from partition_info WHERE partition_id = ?", (results[0][1]+1,)
        ).fetchone()[0]
        path = cursor.execute("SELECT e01_path FROM case_info").fetchall()
        exportar_reg_usuario(
            caso_dir= caso_dir,
            ewf_path=path[0][0],
            partition_offset=partition_offset_sectors,
            paths=[result[2] for result in results]
        )
    conn.close()

def generar_nombre_export_ntuser(ruta_completa):
    """
    Dada una ruta como '/Users/Jimmy Wilson/NTUSER.DAT', devuelve 'Jimmy Wilson_NTUSER.DAT'
    """
    ruta_normalizada = ruta_completa.replace("\\", "/").strip("/")
    partes = ruta_normalizada.split("/")

    if len(partes) >= 2 and partes[-1].lower() == "ntuser.dat":
        usuario = partes[-2].strip()
        if not usuario:
            usuario = "desconocido"
        return f"{usuario}_NTUSER.DAT"
    elif len(partes) >= 2 and partes[-1].lower() == "usrclass.dat":
        usuario = partes[1].strip()
        return f"{usuario}_USRCLASS.DAT"
    else:
        return partes[-1].upper()

def exportar_reg_usuario(caso_dir, ewf_path, partition_offset, paths):
    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)

    for path in paths:
        file_entry = fs.open(path)
        size = file_entry.info.meta.size
        offset = 0
        chunk_size = 1024 * 1024  # 1 MB
        output_path = os.path.join(
            caso_dir,
            BASE_DIR_EXPORT_TEMP,
            generar_nombre_export_ntuser(path)
        )
        os.makedirs(os.path.join(caso_dir, BASE_DIR_EXPORT_TEMP), exist_ok=True)
        if os.path.exists(output_path):
            continue
        with open(output_path, "wb") as f:
            while offset < size:
                data = file_entry.read_random(offset, min(chunk_size, size - offset))
                if not data:
                    break
                f.write(data)
                offset += len(data)



def exportar_registro(caso_dir, ewf_path, partition_offset, path):

    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)
    file_entry = fs.open(path)

    size = file_entry.info.meta.size
    offset = 0
    chunk_size = 1024 * 1024  # 1 MB

    output_path = os.path.join(
        caso_dir,
        BASE_DIR_EXPORT_TEMP,
        file_entry.info.name.name.decode("utf-8", errors="ignore").upper()
    )
    os.makedirs(os.path.join(caso_dir,BASE_DIR_EXPORT_TEMP), exist_ok=True)

    if os.path.exists(output_path):
        return
    with open(output_path, "wb") as f:
        while offset < size:
            data = file_entry.read_random(offset, min(chunk_size, size - offset))
            if not data:
                break
            f.write(data)
            offset += len(data)


def obtener_archivos_en_directorio(path):
    return [str(archivo) for archivo in Path(path).iterdir() if archivo.is_file()]

def visualizar_hive(export_path, archivo):
    
    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Registros del Sistema. Leyenda: [+] Subclave, [v] Valor")
    layout.change_footer("ENTER: Acceder a subclaves/Mostrar valores basicos, ↑/↓: Navegar, ← : Anterior subclave, ESC: Salir,  i: Mostrar informacion avanzada, b: Buscar, e: Exportar")
    panel = RegistryViewerPanel(layout.body_win, archivo, export_path, layout)
    panel.render()
    layout.body_win.keypad(True)
    while True:
        panel.render()
        key = layout.body_win.getch()
        if key  == 27:  # ESC
            break
        panel.handle_input(key)


def seleccionar_visualizar_registros(layout, archivos, dir_exportar):
    while True:
        layout.render()
        layout.change_header("Visualizador de Registros del Sistema")
        layout.change_footer("Presiona ESC para salir")

        menu = AwesomeMenu(title="Seleccione el archivo de registro", options=archivos, win=layout.body_win)
        selected_option = menu.render()
        if selected_option is None:
            layout.body_win.clear()
            layout.body_win.refresh()
            return "exit"
        visualizar_hive(dir_exportar, archivos[selected_option])

    

def analizar_hive(layout, archivo, db_path, dir_temp):
    #system path
    if os.path.isfile(os.path.join(dir_temp, "SYSTEM")):
        systempath = os.path.join(dir_temp, "SYSTEM")
    else:
        systempath = ""
    layout.body_win.refresh()

    if archivo.endswith("SYSTEM") or archivo.endswith("system"):
        extraer_system(db_path, archivo) 
        pass
    elif archivo.endswith("SOFTWARE"):
        extraer_software(archivo, db_path)
    elif archivo.endswith("SAM"):
        if not systempath:
            layout.body_win.addstr(1, 0, "No se encontró el archivo SYSTEM necesario para analizar SAM.")
            layout.body_win.refresh()
            layout.body_win.getch()
            return
        extraer_sam(sam_hive_path = archivo, system_hive_path = systempath, db_path = db_path)
        pass
    elif archivo.endswith("NTUSER.DAT"):
        extraer_ntuser_artefactos(archivo, db_path)
        pass
    elif archivo.endswith("USRCLASS.DAT"):
        extraer_usrclass(archivo, db_path, "Jimmy Wilson")
        pass
    elif archivo.endswith(".hive"):
        pass

def seleccionar_analizar_registros(layout, archivos, db_path, dir_temp, dir_exportar):
        visualizar_resumen_usuarios(db_path, dir_exportar)
        while True:
            layout.render()
            layout.change_header("Analizador de Registros del Sistema")
            layout.change_footer("Presiona ESC para salir")

            menu = AwesomeMenu(title="Seleccione el archivo de registro", options=archivos, win=layout.body_win)
            selected_option = menu.render()
            if selected_option is None:
                layout.body_win.clear()
                layout.body_win.refresh()
                return "exit"
            analizar_hive(layout, archivos[selected_option], db_path, dir_temp)

           
    



def registry_analyzer(db_path, caso_dir):
    dir_temp = os.path.join(caso_dir, BASE_DIR_EXPORT_TEMP)
    dir_exportar = os.path.join(caso_dir, BASE_DIR_EXPORT)
    layout = AwesomeLayout()
    while True:
        layout.render()
        layout.change_header("Analizador de Registros del Sistema")
        layout.change_footer("Presiona ESC para salir")

        archivos = obtener_archivos_en_directorio(dir_temp)
        if not archivos:
            layout.body_win.addstr(1, 0, "No se encontraron registros del sistema.")
            layout.body_win.refresh()
            layout.body_win.getch()
            break
        res = seleccionar_visualizar_registros(layout, archivos, dir_exportar)

        if res == "exit":
            break