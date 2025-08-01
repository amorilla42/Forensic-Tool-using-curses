

import pytsk3
import os
from pathlib import Path
import sqlite3
from forensic_core.artifacts.deleted_files.extract_info_deleted_files import escanear_y_procesar_archivos_borrados
from forensic_core.artifacts.registry.sam_hive import extraer_sam
from forensic_core.artifacts.registry.software_hive import extraer_software
from forensic_core.artifacts.registry.system_hive import extraer_system
from forensic_core.artifacts.registry.usernt_data_hive import extraer_ntuser_artefactos
from forensic_core.artifacts.registry.usrclass_shellbags_hive import extraer_usrclass


BASE_DIR_EXPORT_TEMP = "temp"
BASE_DIR_EXPORT = "exported_files"

def obtener_archivos_en_directorio(path):
    return [str(archivo) for archivo in Path(path).iterdir() if archivo.is_file()]

def analizar_hives(archivo, db_path):
    if archivo.endswith("SOFTWARE"):
        extraer_software(archivo, db_path)
    elif archivo.endswith("NTUSER.DAT"):
        extraer_ntuser_artefactos(archivo, db_path)
    elif archivo.endswith("USRCLASS.DAT"):
        extraer_usrclass(archivo, db_path)
    elif archivo.endswith(".hive"):
        pass



def extraer_artefactos(db_path, caso_dir):
    from forensic_core.artifacts.registry.registry_analyzer import exportar_hives_sistema, exportar_hives_usuario
    exportar_hives_sistema(db_path, caso_dir)
    exportar_hives_usuario(db_path, caso_dir)
    dir_temp = os.path.join(caso_dir, BASE_DIR_EXPORT_TEMP)
    dir_exportar = os.path.join(caso_dir, BASE_DIR_EXPORT)
    archivos = obtener_archivos_en_directorio(dir_temp)
    
    sysfile = os.path.join(dir_temp, "SYSTEM")
    extraer_system(db_path, sysfile)
    samfile = os.path.join(dir_temp, "SAM")
    extraer_sam(sam_hive_path = samfile, system_hive_path = sysfile, db_path = db_path)
    if not archivos:
        return
    for archivo in archivos:
        analizar_hives(archivo, db_path)
    
    # archivos que pueden tener informacion de usuario
    exportar_archivos_interesantes(db_path, caso_dir)


def exportar_file(ewf_path, partition_offset, path, dir_interesantes):
    from forensic_core.e01_reader import open_e01_image
    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)
    file_entry = fs.open(path)

    size = file_entry.info.meta.size
    offset = 0
    chunk_size = 1024 * 1024  # 1 MB

    output_path = os.path.join(
        dir_interesantes,
        file_entry.info.name.name.decode("utf-8", errors="ignore")
    )

    if os.path.exists(output_path):
        return
    with open(output_path, "wb") as f:
        while offset < size:
            data = file_entry.read_random(offset, min(chunk_size, size - offset))
            if not data:
                break
            f.write(data)
            offset += len(data)



def exportar_archivos_interesantes(db_path, caso_dir):
    dir_interesantes = os.path.join(caso_dir, "archivos_interesantes")
    os.makedirs(dir_interesantes, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM filesystem_entry WHERE extension IN ('.pdf', '.doc', '.txt', '.snt', '.pst', '.ost', '.zip', '.rar', '.7z')")
    results = cursor.fetchall()
    #TODO: LA BASE DE DATOS LAS PARTICIONES ESTAN CON ID 1 MENOS DE LO QUE DEBERIA
    partition_offset_sectors = cursor.execute(
        "SELECT partition_offset from partition_info WHERE partition_id = ?", (results[0][1]+1,)
    ).fetchone()[0]
    path = cursor.execute("SELECT e01_path FROM case_info").fetchall()

    for result in results:
        exportar_file(
                ewf_path=path[0][0],
                partition_offset=partition_offset_sectors,
                path=result[2],
                dir_interesantes = dir_interesantes
            )
    conn.close()

    escanear_y_procesar_archivos_borrados(dir_interesantes, dir_interesantes)


    
        
        
       
        
        
