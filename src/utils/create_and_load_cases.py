import os
import json
import hashlib

CASES_DIR = "cases"

def calcular_sha256(path):
    hash_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def crear_directorio_caso(nombre):
    base_dir = os.path.join(CASES_DIR, nombre)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def guardar_metadata(caso_dir, nombre, e01_path, partition_number, offset):
    metadata = {
        "case_name": nombre,
        "e01_path": e01_path,
        "partition_number": partition_number,
        "partition_offset": offset,
        "sha256": calcular_sha256(e01_path)
    }
    with open(os.path.join(caso_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)


def cargar_metadata(caso_dir):
    metadata_path = os.path.join(caso_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError("No se encontró metadata.json en el directorio del caso.")
    with open(metadata_path, "r") as f:
        return json.load(f)