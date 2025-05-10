import sqlite3
import os
from forensic_core.e01_reader import open_e01_image
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_input import AwesomeInput
from curses_ui.awesome_menu2 import AwesomeMenu
from curses_ui.file_viewer_panel import FileViewerPanel
import pytsk3
import pyewf

from forensic_core.export_file import exportar_archivo



def search_files(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Introduce el parametro de busqueda")
    layout.change_footer("Presiona ENTER para buscar, ESC para salir")

    query = AwesomeInput(layout.body_win).render()
    # TODO: MEJORAR LA BUSQUEDA QUE COMPARE Y HAGA BUSQUEDA EN TODOS LOS CAMPOS DE FILESISTEM_ENTRY
    cursor.execute("SELECT * FROM filesystem_entry WHERE name LIKE ?", ('%' + query + '%',))
    results = cursor.fetchall()
    conn.close()
    if not results:
        print("No se encontraron resultados.")
        return
    layout.change_header(f"Busqueda: {query}")
    layout.change_footer("Presiona ENTER para seleccionar, ESC para salir")
    menu = AwesomeMenu(
        title="Resultados de la busqueda, presiona ENTER para seleccionar, ESC para salir",
        options=[f"Nombre: {result[3]}, Ruta: {result[2]}, Tamaño: {result[6]}" for result in results],
        win=layout.body_win
    )
    selected = menu.render()
    
    while selected is not None:
        selected_file = results[selected]
        layout.change_header(f"Seleccionaste: {selected_file[3]}")
        layout.change_footer("Presiona TAB para alternar entre ventanas, ↑/↓ ←/→  para desplazamiento de texto, ENTER para exportar archivo, ESC para salir")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        
        cursor.execute("SELECT block_size FROM partition_info WHERE partition_id = ?", (selected_file[1]+1,))
        block_size = cursor.fetchone()[0]

        partition_offset_sectors = cursor.execute(
            "SELECT partition_offset from partition_info WHERE partition_id = ?", (selected_file[1]+1,)
        ).fetchone()[0]
        
        partition_offset_bytes = partition_offset_sectors


        cursor.execute("SELECT e01_path FROM case_info")
        path = cursor.fetchall()

        conn.close()

        metadata2, content_lines2 = get_info_file2(
            ewf_path=path[0][0],
            partition_offset=partition_offset_bytes,
            path=selected_file[2],
            layout=layout
        )
        #####
        metadata, content_lines = get_info_file(
            ewf_path=path[0][0],
            partition_offset=partition_offset_bytes,
            inode=selected_file[7],
            layout=layout
        )
        extraer = FileViewerPanel(metadata2, content_lines2, layout.body_win).render()
        if extraer:
            exportar_archivo(
                ewf_path=path[0][0], 
                partition_offset=partition_offset_bytes, 
                path=selected_file[2]
            )
        layout.clear()
        layout.change_header(f"Busqueda: {query}")
        layout.change_footer("Presiona ESC para salir")
        selected = menu.render()
    
    if selected is None:
        layout.clear()
        return
    selected_file = results[selected]
    return selected_file

def extract_file_info(img, partition_offset, inode, layout):
    try:
        fs = pytsk3.FS_Info(img, offset=partition_offset)
        file_obj = fs.open_meta(inode=inode)

        meta = file_obj.info.meta
        if meta is None or meta.size is None:
            raise ValueError("No se puede obtener el contenido del archivo: tamaño no definido.")

        content = b""
        size = meta.size
        if not isinstance(size, int):  # Verificar que size es un entero
            raise ValueError("Tamaño del archivo no es válido.")
        
        if size > 10 * 1024 * 1024:
            raise ValueError("Archivo muy grande para mostrarlo por pantalla.")

        offset = 0
        while offset < size:
            chunk = file_obj.read_random(offset, min(4096, size - offset))
            if not isinstance(chunk, bytes):
                raise ValueError(f"Esperado un objeto 'bytes', pero se encontró {type(chunk)}.")
            if not chunk:
                break
            content += chunk
            offset += len(chunk)

        return file_obj, content

    except Exception as e:
        layout.change_footer(f"Error al extraer el archivo: {str(e)}")
        return None, None

def extract_file_info2(img, partition_offset, path, layout):
    try:
        fs = pytsk3.FS_Info(img, offset=partition_offset)
        file_obj = fs.open(path)
        meta = file_obj.info.meta
        if meta is None or meta.size is None:
            raise ValueError("No se puede obtener el contenido del archivo: tamaño no definido.")
        content = b""
        size = meta.size
        if not isinstance(size, int):  # Verificar que size es un entero
            raise ValueError("Tamaño del archivo no es válido.")
        if size > 10 * 1024 * 1024:
            raise ValueError("Archivo muy grande para mostrarlo por pantalla.")
        offset = 0
        while offset < size:
            chunk = file_obj.read_random(offset, min(4096, size - offset))
            if not isinstance(chunk, bytes):
                raise ValueError(f"Esperado un objeto 'bytes', pero se encontró {type(chunk)}.")
            if not chunk:
                break
            content += chunk
            offset += len(chunk)
        return file_obj, content
    except Exception as e:
        layout.change_footer(f"Error al extraer el archivo: {str(e)}")
        return None, None
    

def get_file_metadata(file_obj):
    meta = file_obj.info.meta
    if file_obj.info.name is not None and file_obj.info.name.name is not None:
        name = file_obj.info.name.name.decode(errors="replace")
    else:
        name = "(sin nombre / archivo huérfano)"
    return {
        "Nombre": name,
        "Inode": meta.addr,
        "Tama\u00f1o": meta.size,
        "Creacion": str(meta.crtime),
        "Modificacion": str(meta.mtime),
        "Acceso": str(meta.atime),
        "Cambio": str(meta.ctime),
        "Modo": hex(meta.mode),
        "UID": meta.uid,
        "GID": meta.gid
    }


def prepare_content_lines(content: bytes) -> list[str]:
    try:
        text = content.decode("utf-8")
        return text.splitlines()
    except UnicodeDecodeError:
        return [content[i:i+16].hex() for i in range(0, len(content), 16)]

def get_info_file(ewf_path, partition_offset, inode, layout):
    img = open_e01_image(ewf_path)
    file_obj, content = extract_file_info(img, partition_offset, inode, layout)

    # Si ocurrió un error, no continuar procesando
    if file_obj is None or content is None:
        return {}, []

    metadata = get_file_metadata(file_obj)
    content_lines = prepare_content_lines(content)
    return metadata, content_lines

def get_info_file2(ewf_path, partition_offset, path, layout):
    img = open_e01_image(ewf_path)
    file_obj, content = extract_file_info2(img, partition_offset, path, layout)
    
    if file_obj is None:
        layout.change_footer("No se pudo abrir el archivo.")
        return {}, []
    #try:
    #    content = file_obj.read_random(0, file_obj.info.meta.size)
    #except Exception as e:
    #    layout.change_footer(f"Error al leer el archivo: {str(e)}")
    #    return {}, []
    if content is None:
        layout.change_footer("No se pudo leer el contenido del archivo.")
        return {}, []
    metadata = get_file_metadata(file_obj)
    content_lines = prepare_content_lines(content)
    return metadata, content_lines