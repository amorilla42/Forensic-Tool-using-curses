import pytsk3 # type: ignore
import pyewf

from curses_ui.select_partition import select_partition


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

def digestE01(e01_path, stdscr):
    
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



