import pytsk3 # type: ignore
import pyewf # type: ignore


class EWFImgInfo(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super().__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()

def choose_partition_and_offset(e01_path):
    filenames = pyewf.glob(e01_path)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)

    img_info = EWFImgInfo(ewf_handle)
    partition_table = pytsk3.Volume_Info(img_info)

    partitions = []
    print("\nSe han detectado las siguientes particiones:")
    for i, partition in enumerate(partition_table):
        if partition.len > 2048 and b"Unallocated" not in partition.desc:
            print(f"{i+1}. {partition.desc.decode(errors='ignore')} - Offset: {partition.start * 512} bytes")
            partitions.append((i+1, partition))

    if not partitions:
        raise RuntimeError("No se encontraron particiones válidas.")

    while True:
        seleccion = input("Selecciona el número de la partición que deseas montar: ")
        if seleccion.isdigit():
            seleccion = int(seleccion)
            for i, part in partitions:
                if i == seleccion:
                    offset = part.start * 512
                    fs = pytsk3.FS_Info(img_info, offset=offset)
                    fs.open_dir("/")  # Verifica que el FS es válido
                    return fs, seleccion, offset
        print("Opción inválida. Intenta de nuevo.")

def open_e01_with_offset(e01_path, offset):
    filenames = pyewf.glob(e01_path)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)

    img_info = EWFImgInfo(ewf_handle)
    fs = pytsk3.FS_Info(img_info, offset=offset)
    fs.open_dir("/")  # Verifica acceso
    return fs

