import os
import pytsk3
from .export_eml import export_eml
from forensic_core.e01_reader import open_e01_image

BASE_DIR_EXPORT = "../exported_files"

def exportar_archivo(ewf_path, partition_offset, path):

    img = open_e01_image(ewf_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset)
    file_entry = fs.open(path)

    size = file_entry.info.meta.size
    offset = 0
    chunk_size = 1024 * 1024  # 1 MB

    output_path = os.path.join(
        BASE_DIR_EXPORT,
        file_entry.info.name.name.decode("utf-8", errors="ignore")
    )
    os.makedirs(BASE_DIR_EXPORT, exist_ok=True)

    if ".eml" in file_entry.info.name.name.decode("utf-8", errors="ignore"):
        export_eml(file_entry=file_entry, size=size, offset=offset, chunk_size=chunk_size)
    else:
        with open(output_path, "wb") as f:
            while offset < size:
                data = file_entry.read_random(offset, min(chunk_size, size - offset))
                if not data:
                    break
                f.write(data)
                offset += len(data)
