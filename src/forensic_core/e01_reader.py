import logging
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

def abrir_fs_con_particion(img, partition_offset,stdscr):
    try:
        # Cargar el sistema de archivos de la partición
        fs_info = pytsk3.FS_Info(img, offset=partition_offset)
        stdscr.addstr(0, 0, f"Sistema de archivos cargado en offset: {partition_offset}")
        stdscr.refresh()
        return fs_info
    except Exception as e:
        stdscr.addstr(0, 0, f"Error al abrir sistema de archivos: {e}")
        stdscr.refresh()
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

def digestE01(e01_path, stdscr, db_path, case_name):
    
    image = open_e01_image(e01_path)

    volume_info = pytsk3.Volume_Info(image)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    insertar_case_info(cursor, case_name, e01_path, "randomSha256hash")

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
            stdscr.addstr(1,0,f"Partición {i}: {description} (Start: {start_offset}, Length: {lenght})")
            stdscr.refresh()
            stdscr.getch()
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
            logging.info(f"Insertando información de la partición en la base de datos: "
                         f"Descripción: {description}, Inicio: {start_offset}, Longitud: {lenght}, "
                         f"Offset: {partition_offset}, Tipo FS: {fs_type}, Etiqueta: {label}, "
                         f"Tamaño de bloque: {block_size}, Conteo de bloques: {block_count}")
            insertar_partition_info(
                cursor, case_name, description, start_offset, lenght, partition_offset, fs_type, label,
                block_size, block_count
            )

            # Mostrar progreso en pantalla
            progress = f"Procesando partición {i+1}: Offset 0x{partition_offset:08X} - {fs_type}"
            stdscr.addstr(i+1, 0, progress[:stdscr.getmaxyx()[1]-1])
            stdscr.refresh()

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