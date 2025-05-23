from Registry import Registry
import os
import pytsk3
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.registry_viewer import RegistryViewerPanel
from forensic_core.artifacts.registry.sam_hive import extraer_sam
from forensic_core.artifacts.registry.system_hive import extraer_system
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
System32/config/SECURITY	                SECURITY	    Políticas de seguridad y SIDs
System32/config/DEFAULT	                    DEFAULT	        Perfil por defecto
System32/config/BBI     	                BBI 	        Opcionales, usados por Windows moderno
System32/config/ELAM                        ELAM	        Opcionales, usados por Windows moderno      
Users/usuario/NTUSER.DAT	                NTUSER.DAT	    Configuración de usuario
Users/usuario/AppData/.../UsrClass.dat	    UsrClass.dat	Extensión de configuraciones de usuario
'''
# Rutas relativas y nombre de hive esperado
HIVES_SISTEMA = {
    "SYSTEM": "Windows/System32/config/SYSTEM",
    "SOFTWARE": "Windows/System32/config/SOFTWARE",
    "SAM": "Windows/System32/config/SAM",
    "SECURITY": "Windows/System32/config/SECURITY",
    "DEFAULT": "Windows/System32/config/DEFAULT",
    "BBI": "Windows/System32/config/BBI",
    "ELAM": "Windows/System32/config/ELAM"
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
            continue
        #TODO: LA BASE DE DATOS LAS PARTICIONES ESTAN CON ID 1 MENOS DE LO QUE DEBERIA
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


def exportar_hives(ewf_path, partition_offset):

    exportar_hives_sistema(ewf_path, partition_offset)




def exportar_registro(caso_dir, ewf_path, partition_offset, path):

    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)
    file_entry = fs.open(path)

    size = file_entry.info.meta.size
    offset = 0
    chunk_size = 1024 * 1024  # 1 MB

    output_path = os.path.join(
        caso_dir,
        BASE_DIR_EXPORT,
        file_entry.info.name.name.decode("utf-8", errors="ignore")
    )
    os.makedirs(os.path.join(caso_dir,BASE_DIR_EXPORT), exist_ok=True)

    with open(output_path, "wb") as f:
        while offset < size:
            data = file_entry.read_random(offset, min(chunk_size, size - offset))
            if not data:
                break
            f.write(data)
            offset += len(data)


def obtener_archivos_en_directorio(path):
    return [str(archivo) for archivo in Path(path).iterdir() if archivo.is_file()]

def analizar_hives_sistema(hive_path, export_path, db_path):
    archivos = obtener_archivos_en_directorio(hive_path)
    systempath = os.path.join(hive_path, "SYSTEM")
    
    

    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Registros del Sistema")
    layout.change_footer("Las risas")
    panel = RegistryViewerPanel(layout.body_win, systempath, export_path)
    panel.render()
    layout.body_win.keypad(True)
    while True:
        panel.render()
        key = layout.body_win.getch()
        if key  == ord("q"):
            break
        panel.handle_input(key)
    
    
    for archivo in archivos:
        if archivo.endswith("SYSTEM"):
            extraer_system(db_path, archivo)
            # Aquí puedes agregar la lógica para analizar el archivo .reg
            pass
        elif archivo.endswith("SOFTWARE"):
            # Aquí puedes agregar la lógica para analizar el archivo .reg
            pass
        elif archivo.endswith("SAM"):
            extraer_sam(sam_hive_path = archivo, system_hive_path = systempath, db_path = db_path)
            pass
        elif archivo.endswith("SECURITY"):
            # Aquí puedes agregar la lógica para analizar el archivo .reg
            pass
        elif archivo.endswith("DEFAULT"):
            # Aquí puedes agregar la lógica para analizar el archivo .reg
            pass
        elif archivo.endswith(".hive"):
            # Aquí puedes agregar la lógica para analizar el archivo .reg
            pass



    



def registry_analyzer(db_path, caso_dir):
    exportar_hives_sistema(db_path, caso_dir)
    analizar_hives_sistema(os.path.join(caso_dir, BASE_DIR_EXPORT_TEMP), os.path.join(caso_dir, BASE_DIR_EXPORT) , db_path)