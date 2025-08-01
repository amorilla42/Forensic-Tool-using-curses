import os
import struct
from glob import glob

def filetime_to_str(ft):
    import datetime
    unix_time = (ft - 116444736000000000) // 10000000
    return str(datetime.datetime.fromtimestamp(unix_time, datetime.timezone.utc))

def procesar_par(i_path, r_path, salida_dir):
    with open(i_path, "rb") as f:
        data = f.read()

    header = struct.unpack("<Q", data[0:8])[0]
    if header != 1:
        return 

    original_size = struct.unpack("<Q", data[8:16])[0]
    deletion_time = struct.unpack("<Q", data[16:24])[0]
    original_path = data[24:].decode("utf-16le").rstrip("\x00")
    original_filename = os.path.basename(original_path)
    salida_path = os.path.join(salida_dir, original_filename)

    # Evitar sobrescribir archivos ya restaurados
    if os.path.exists(salida_path):
        base, ext = os.path.splitext(original_filename)
        salida_path = os.path.join(salida_dir, f"{base}_recuperado{ext}")

    with open(r_path, "rb") as rf, open(salida_path, "wb") as wf:
        wf.write(rf.read())

    metadata_path = salida_path + ".meta.txt"
    with open(metadata_path, "w", encoding="utf-8") as meta_f:
        meta_f.write(f"Ruta original: {original_path}\n")
        meta_f.write(f"Peso del archivo original: {original_size} bytes\n")
        meta_f.write(f"Timestamp eliminacion (FILETIME): {deletion_time}\n")
        meta_f.write(f"Timestamp eliminacion (UTC): {filetime_to_str(deletion_time)}\n")


def escanear_y_procesar_archivos_borrados(carpeta_entrada, carpeta_salida):
    os.makedirs(carpeta_salida, exist_ok=True)

    archivos_I = {os.path.basename(f)[2:]: f for f in glob(os.path.join(carpeta_entrada, "$I*"))}
    archivos_R = {os.path.basename(f)[2:]: f for f in glob(os.path.join(carpeta_entrada, "$R*"))}

    claves_comunes = set(archivos_I.keys()) & set(archivos_R.keys())

    if not claves_comunes:
        return

    for clave in claves_comunes:
        i_path = archivos_I[clave]
        r_path = archivos_R[clave]
        procesar_par(i_path, r_path, carpeta_salida)
