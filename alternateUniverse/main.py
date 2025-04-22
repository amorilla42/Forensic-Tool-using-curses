import hashlib
import os
import sqlite3
import pyewf # type: ignore
import pytsk3 # type: ignore
from datetime import datetime , timezone
from createdatabase import crear_base_de_datos, insertar_file_hash, insertar_filesystem_entry, insertar_timeline_event

CASES_DIR = "cases"
CASENAME = "Glask"


def open_e01_image(e01_path):
    filenames = pyewf.glob(e01_path)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)

    class EWFImgInfo(pytsk3.Img_Info):
        def __init__(self, ewf_handle):
            self._ewf_handle = ewf_handle
            super().__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

        def read(self, offset, size):
            self._ewf_handle.seek(offset)
            return self._ewf_handle.read(size)

        def get_size(self):
            return self._ewf_handle.get_media_size()

    return EWFImgInfo(ewf_handle)




def hash_sha256(fileobj):
    sha256 = hashlib.sha256()
    while True:
        data = fileobj.read(4096)
        if not data:
            break
        sha256.update(data)
    return sha256.hexdigest()



def recorrer_archivos_recursivo(cursor, fs_info, dir_obj, parent_path, partition_id, case_id):
    for entry in dir_obj:
        if not entry.info.name.name or entry.info.name.name in [b".", b".."]:
            continue

        try:
            name = entry.info.name.name.decode("utf-8", "ignore")
            full_path = os.path.join(parent_path, name)
            ext = os.path.splitext(name)[1].lower()
            tipo = entry.info.meta.type if entry.info.meta else None
            tipo = "dir" if tipo == pytsk3.TSK_FS_META_TYPE_DIR else "file"
            size = entry.info.meta.size if entry.info.meta else 0
            inode = entry.info.meta.addr if entry.info.meta else None

            def get_ts(attr): return datetime.fromtimestamp(attr, timezone.utc) if attr else None
            
            mtime = get_ts(entry.info.meta.mtime)
            atime = get_ts(entry.info.meta.atime)
            ctime = get_ts(entry.info.meta.ctime)
            crtime = get_ts(entry.info.meta.crtime)

            # Extraer SHA256 si es archivo y no es gigante
            sha256 = None
            if tipo == "file" and size < 10 * 1024 * 1024:
                try:
                    f = entry.read_random(0, size)
                    sha256 = hashlib.sha256(f).hexdigest()
                except Exception:
                    pass

            entry_id = insertar_filesystem_entry(
                cursor, partition_id, full_path, name, ext, tipo, size,
                inode, mtime, atime, ctime, crtime, sha256
            )

            if sha256:
                insertar_file_hash(cursor, entry_id, sha256)

            # Insertar en línea de tiempo
            if crtime:
                insertar_timeline_event(cursor, case_id, "fs", entry_id, f"Archivo: {name}", crtime)

            # Recursividad en carpetas
            if tipo == "dir":
                subdir = entry.as_directory()
                recorrer_archivos_recursivo(cursor, fs_info, subdir, full_path, partition_id, case_id)

        except Exception as e:
            print(f"Error al procesar entrada: {name} {e}")

def abrir_fs_con_particion(img, partition_offset):
    try:
        # Cargar el sistema de archivos de la partición
        fs_info = pytsk3.FS_Info(img, offset=partition_offset)
        print(f"Sistema de archivos cargado en offset: {partition_offset}")
        return fs_info
    except Exception as e:
        print(f"Error al abrir sistema de archivos: {e}")
        return None


def extraer_archivos_de_e01(e01_path, db_path, case_id):
    print("Abriendo imagen...")
    img = open_e01_image(e01_path)

    volume_info = pytsk3.Volume_Info(img)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for i, partition in enumerate(volume_info):
        print(f"Partición {i}: {partition.desc.decode()} (Start: {partition.start}, Length: {partition.len})")

        # Detectar la partición "Basic data partition" (suele ser NTFS o FAT)
        if b"Basic data partition" in partition.desc or b"NTFS" in partition.desc or b"exFAT" in partition.desc:
            partition_offset = partition.start * 512
            print(f"Abriendo sistema de archivos en offset: {partition_offset}")
            fs_info = abrir_fs_con_particion(img, partition_offset)
            
            if fs_info:
                # Llamar a la función que recorre los archivos
                recorrer_archivos_recursivo(cursor, fs_info, fs_info.open_dir("/"), "/", partition.addr , case_id)


    conn.commit()
    conn.close()
    print("✅ Extracción finalizada y guardada en base de datos.")


    


if __name__ == "__main__":
    ##de la manteca del nombre del caso igualarlo a la variable CASENAME
    ## si no es nuevo, abrir la base de datos del caso que te pida

    crear_base_de_datos(f"{CASENAME}.db")
    #extraer_archivos_de_e01("portatil.E01", "alternate_universe.db", 1)
    extraer_archivos_de_e01("portatil.E01", f"{CASENAME}.db", 1)
    #extraer_archivos_de_e01("win10foren.E02", f"{CASENAME}.db", 1)
    #extraer_archivos_de_e01("win10foren.E03", f"{CASENAME}.db", 1)
    #extraer_archivos_de_e01("win10foren.E04", f"{CASENAME}.db", 1)
    


