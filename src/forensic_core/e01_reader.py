from datetime import datetime, timezone
import hashlib
import logging
import os
import sqlite3
import pytsk3 # type: ignore
import pyewf


from curses_ui.select_partition import select_partition
from database.create_database import crear_base_de_datos, insertar_file_hash, insertar_filesystem_entry, insertar_timeline_event, insertar_partition_info, insertar_case_info


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

def abrir_fs_con_particion(img, partition_offset):
    try:
        # Cargar el sistema de archivos de la partición
        fs_info = pytsk3.FS_Info(img, offset=partition_offset)
        return fs_info
    except Exception as e:
        return None

def get_fs_type_name(ftype):
    fs_types = {
        pytsk3.TSK_FS_TYPE_NTFS: "NTFS",
        pytsk3.TSK_FS_TYPE_FAT12: "FAT12",
        pytsk3.TSK_FS_TYPE_FAT16: "FAT16",
        pytsk3.TSK_FS_TYPE_FAT32: "FAT32",
        pytsk3.TSK_FS_TYPE_EXT2: "EXT2/3/4",
        pytsk3.TSK_FS_TYPE_EXT3: "EXT2/3/4",
        pytsk3.TSK_FS_TYPE_EXT4: "EXT2/3/4",
        pytsk3.TSK_FS_TYPE_HFS: "HFS",
        pytsk3.TSK_FS_TYPE_ISO9660: "ISO9660"
    }
    return fs_types.get(ftype, f"Desconocido ({ftype})")

def get_partition_label(fs_info):
    try:
        if hasattr(fs_info, 'info') and hasattr(fs_info.info, 'label'):
            return fs_info.info.label.decode(errors='ignore').strip()
    except:
        pass
    return "Sin etiqueta"

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
            continue

def calcular_hash_E01(ruta_E01, algoritmo="sha256", buffer_size=65536):
    """
    Calcula el hash de un archivo .E01 (EWF).
    
    Args:
        ruta_ewf (str): Ruta al archivo .E01.
        algoritmo (str): "sha256", "md5", "sha1", etc.
        buffer_size (int): Tamaño del buffer de lectura (por defecto 64KB).
    
    Returns:
        str: Hash hexadecimal del archivo.
    """
    # Inicializar el objeto hashlib según el algoritmo
    if algoritmo not in hashlib.algorithms_available:
        raise ValueError(f"Algoritmo no soportado. Usa uno de: {hashlib.algorithms_available}")
    
    hash_obj = hashlib.new(algoritmo)
    
    # Abrir el archivo E01 con pyewf
    ewf_handle = pyewf.handle()
    filenames = pyewf.glob(ruta_E01)
    ewf_handle.open(filenames)
    
    # Leer el contenido en bloques y actualizar el hash
    while True:
        data = ewf_handle.read(buffer_size)
        if not data:
            break
        hash_obj.update(data)
    
    ewf_handle.close()
    
    return hash_obj.hexdigest()


def digestE01(e01_path, stdscr, db_path, case_name):
    


    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    insertar_case_info(cursor, case_name, e01_path, calcular_hash_E01(e01_path,"sha256"))
    conn.commit()

    image = open_e01_image(e01_path)

    volume_info = pytsk3.Volume_Info(image)

    try:
        for i, partition in enumerate(volume_info):
            partition_offset = partition.start * 512
            fs_type = "Unallocated"
            label = ""
            block_size = 0
            block_count = 0
            description = partition.desc.decode(errors='ignore') if partition.desc else ""
            start_offset = partition.start
            lenght = partition.len
            # Solo intentamos analizar si no es espacio no asignado
            if b"Unallocated" not in partition.desc:
                try:
                    fs_info = pytsk3.FS_Info(image, offset=partition_offset)
                    fs_type = get_fs_type_name(fs_info.info.ftype)
                    label = get_partition_label(fs_info)
                    block_size = fs_info.info.block_size
                    block_count = fs_info.info.block_count
                    logging.info(f"Tipo de sistema de archivos: {fs_type}, Etiqueta: {label}, Tamaño de bloque: {block_size}, Conteo de bloques: {block_count}")
                    # Verificar acceso al sistema de archivos
                    try:
                        fs_info.open_dir("/")
                    except:
                        fs_type += " (inaccesible)"
                except Exception as e:
                    fs_type = f"Unknown"
            # Insertar en la base de datos
            insertar_partition_info(
                cursor, case_name, description, start_offset, lenght, partition_offset, fs_type, label,
                block_size, block_count
            )

        conn.commit()
        conn.close()



        # Reabrir la conexión para recorrer archivos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for i, partition in enumerate(volume_info):
            try:
                # Detectar la partición "Basic data partition" (suele ser NTFS o FAT)
                if b"Basic data partition" in partition.desc or b"NTFS" in partition.desc or b"exFAT" in partition.desc:
                    partition_offset = partition.start * 512
                    fs_info = abrir_fs_con_particion(image, partition_offset)
                    if fs_info:
                        recorrer_archivos_recursivo(cursor, fs_info, fs_info.open_dir("/"), "/", partition.addr , case_name)
            except Exception as e:
                continue
        
        conn.commit()
        conn.close()



    except Exception as e:
        stdscr.addstr(0, 0, f"Error procesando imagen: {str(e)}")
        stdscr.refresh()
        stdscr.getch()

    """
    for i, partition in enumerate(volume_info):
        
            offset = partition.start * 512
            fs_info = abrir_fs_con_particion(image, offset,stdscr)
            if fs_info is not None:
                selectedvalid = True
                break
    stdscr.refresh()
    """


"""
def digestE01(e01_path, stdscr, db_path):
    
    image = open_e01_image(e01_path)
    
    volume_info = pytsk3.Volume_Info(image)

    selectedvalid = False
    partitions = []
    partitions_strings = []
  
    for i, partition in enumerate(volume_info):
        partitions.append((i+1, partition))
        partitions_strings.append(f"Partición {i+1}: {partition.desc.decode()}, Offset: {partition.start * 512} bytes, Lenght :({partition.len} bytes)")

    if not partitions:
        stdscr.addstr(0, 0, "No se encontraron particiones válidas.")
        stdscr.refresh()
        stdscr.getch()
    
    while(not selectedvalid and partitions):
        seleccion = select_partition(stdscr, partitions_strings)
        
        for i, partition in enumerate(volume_info):
            if i == seleccion:
                offset = partition.start * 512
                fs_info = abrir_fs_con_particion(image, offset,stdscr)
                if fs_info is not None:
                    selectedvalid = True
                    break
        stdscr.refresh()
    return fs_info, seleccion, offset
"""