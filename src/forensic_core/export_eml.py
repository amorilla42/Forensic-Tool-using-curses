import os
from email import policy
from email.parser import BytesParser


BASE_DIR_EXPORT = "exported_files"

def export_eml(case_dir, file_entry, size, offset, chunk_size):
    nombre_base = file_entry.info.name.name.decode("utf-8", errors="ignore")
    carpeta_destino = os.path.join(case_dir, BASE_DIR_EXPORT, nombre_base)
    os.makedirs(carpeta_destino, exist_ok=True)

    output_path = os.path.join(carpeta_destino, nombre_base)
    # Copiar el .eml completo dentro de la carpeta
    with open(output_path, "wb") as f:
        while offset < size:
            data = file_entry.read_random(offset, min(chunk_size, size - offset))
            if not data:
                break
            f.write(data)
            offset += len(data)
    
    with open(output_path, "rb") as f:
        contenido = f.read()
    # Parsear el mensaje
    mensaje = BytesParser(policy=policy.default).parsebytes(contenido)

    for parte in mensaje.walk():
        if parte.get_content_disposition() == 'attachment':
            nombre_archivo = parte.get_filename()
            if nombre_archivo:
                ruta_salida = os.path.join(carpeta_destino, nombre_archivo)
                payload = parte.get_payload(decode=True)
                if isinstance(payload, str):
                    payload = payload.encode(errors="ignore")
                with open(ruta_salida, 'wb') as adjunto:
                    adjunto.write(payload)
