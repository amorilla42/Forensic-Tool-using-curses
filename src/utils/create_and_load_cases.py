import os
import hashlib

CASES_DIR = "../cases"

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
