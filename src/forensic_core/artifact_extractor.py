

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
import re
import tempfile
import shutil





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
    exportar_historial_firefox(db_path=db_path, caso_dir=caso_dir)


def exportar_file(ewf_path, partition_offset, path, dir_interesantes):
    from forensic_core.e01_reader import open_e01_image
    from forensic_core.export_eml import export_eml

    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)
    file_entry = fs.open(path)

    nombre = file_entry.info.name.name.decode("utf-8", errors="ignore")
    nombre_lc = nombre.lower()

    size = file_entry.info.meta.size
    offset = 0
    chunk_size = 1024 * 1024

    # Si es .eml: idempotencia por carpeta <dir_interesantes>/<nombre.eml>/
    if nombre_lc.endswith(".eml"):
        carpeta_destino = os.path.join(dir_interesantes, nombre)
        if os.path.exists(carpeta_destino):
            return
        export_eml(case_dir=dir_interesantes,
                   file_entry=file_entry,
                   size=size,
                   offset=offset,
                   chunk_size=chunk_size)
        return

    # Resto: idempotencia por fichero plano
    output_path = os.path.join(dir_interesantes, nombre)
    if os.path.exists(output_path):
        return

    with open(output_path, "wb") as f:
        cur = offset
        while cur < size:
            data = file_entry.read_random(cur, min(chunk_size, size - cur))
            if not data:
                break
            f.write(data)
            cur += len(data)



def exportar_archivos_interesantes(db_path, caso_dir):
    dir_interesantes = os.path.join(caso_dir, "archivos_interesantes")
    os.makedirs(dir_interesantes, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT entry_id, partition_id, full_path, LOWER(extension) AS ext
        FROM filesystem_entry
        WHERE ext IN ('.pdf', '.doc', '.txt', '.snt', '.pst', '.ost', '.zip', '.rar', '.7z', '.eml')
        ORDER BY entry_id
    """)
    results = cur.fetchall()
    if not results:
        conn.close()
        return

    row_e01 = cur.execute("SELECT e01_path FROM case_info LIMIT 1").fetchone()
    if not row_e01:
        conn.close()
        raise RuntimeError("No se encontró e01_path en case_info.")
    e01_path = row_e01[0]

    # Cache de offsets por partition_id
    offsets = {}

    for _entry_id, partition_id, tsk_path, _ext in results:
        if partition_id not in offsets:
            row_off = cur.execute(
                "SELECT partition_offset FROM partition_info WHERE partition_id = ?",
                (partition_id + 1,)
            ).fetchone()
            if not row_off:
                # Si no hay offset, continuar con el siguiente
                continue
            offsets[partition_id] = row_off[0]

        partition_offset_sectors = offsets[partition_id]

        exportar_file(
            ewf_path=e01_path,
            partition_offset=partition_offset_sectors,
            path=tsk_path,
            dir_interesantes=dir_interesantes
        )

    conn.close()

    escanear_y_procesar_archivos_borrados(dir_interesantes, dir_interesantes)



def exportar_historial_firefox(db_path, caso_dir):
    from forensic_core.export_file import exportar_archivo
    """
    Busca en la tabla filesystem_entry todas las rutas que sean places.sqlite
    ubicadas en perfiles de Firefox, las exporta y vuelca (url, title, visit_count, last_visit_date)
    de moz_places a la tabla firefox_history.
    Devuelve el número total de filas insertadas.
    """
    # Carpeta destino organizada por navegador/usuario/perfil
    dir_firefox = os.path.join(caso_dir, "browsers", "firefox")
    os.makedirs(dir_firefox, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()


    cur.execute("""
        CREATE TABLE IF NOT EXISTS firefox_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            profile_path TEXT,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            last_visit_date INTEGER,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)
    conn.commit()

    cur.execute("""
        SELECT entry_id, partition_id, full_path
        FROM filesystem_entry
        WHERE LOWER(full_path) LIKE '%places.sqlite'
    """)
    results = cur.fetchall()
    if not results:
        conn.close()
        return 0


    e01_row = cur.execute("SELECT e01_path FROM case_info LIMIT 1").fetchone()
    if not e01_row:
        conn.close()
        return 0
    e01_path = e01_row[0]

    total_insertadas = 0

    for _fid, partition_id, tsk_path in results:

        partition_offset_sectors = cur.execute(
            "SELECT partition_offset FROM partition_info WHERE partition_id = ?",
            (partition_id + 1,)
        ).fetchone()
        if not partition_offset_sectors:
            continue
        partition_offset_sectors = partition_offset_sectors[0]

        # Extrae el nombre de usuario y perfil desde el path
        username = _extraer_username_desde_path(tsk_path)
        profile = _extraer_profile_desde_path(tsk_path)

        
        exportar_archivo(
            case_dir=caso_dir,
            ewf_path=e01_path,
            partition_offset=partition_offset_sectors,
            path=tsk_path
        )



        default_export = os.path.join(caso_dir, "exported_files", "places.sqlite")
        target_dir = os.path.join(dir_firefox, username, profile)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, "places.sqlite")


        if os.path.exists(target_path):
            base, ext = os.path.splitext(target_path)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            target_path = f"{base}_{i}{ext}"


        if os.path.exists(default_export):
            shutil.move(default_export, target_path)
        elif os.path.exists(os.path.join(caso_dir, "exported_files", os.path.basename(tsk_path))):
            shutil.move(os.path.join(caso_dir, "exported_files", os.path.basename(tsk_path)), target_path)
        else:
            continue


        filas = _leer_moz_places(target_path)


        dcur = conn.cursor()
        for url, title, visit_count, last_visit_date in filas:
            dcur.execute("""
                INSERT INTO firefox_history (username, profile_path, url, title, visit_count, last_visit_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, os.path.dirname(tsk_path), url, title, int(visit_count or 0), last_visit_date))
            total_insertadas += 1
        conn.commit()

    conn.close()
    return total_insertadas




def _leer_moz_places(places_local_path):
    """
    Devuelve lista de tuplas (url, title, visit_count, last_visit_date) desde moz_places.
    last_visit_date queda tal cual (PRTime en microsegundos).
    """
    filas = []
    tmp_fd, tmp_copy = tempfile.mkstemp(suffix=".sqlite")
    os.close(tmp_fd)
    try:
        shutil.copy2(places_local_path, tmp_copy)
        src = sqlite3.connect(tmp_copy)
        try:
            src.row_factory = sqlite3.Row
            c = src.cursor()
            c.execute("""
                SELECT url, title, visit_count, last_visit_date
                FROM moz_places
                WHERE url IS NOT NULL
            """)
            for r in c.fetchall():
                filas.append((r["url"], r["title"], r["visit_count"], r["last_visit_date"]))
        finally:
            src.close()
    except Exception:
        pass
    finally:
        try:
            os.remove(tmp_copy)
        except Exception:
            pass
    return filas

def _extraer_username_desde_path(path):
    m = re.search(r"[/\\](?i:users)[/\\]([^/\\]+)[/\\]", path)
    return m.group(1) if m else "desconocido"

def _extraer_profile_desde_path(path):
    m = re.search(r"[/\\](?i:profiles)[/\\]([^/\\]+)", path)
    return m.group(1) if m else "default"

       
        
        
