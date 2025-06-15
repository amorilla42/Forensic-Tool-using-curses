


import os
from pathlib import Path
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