
"""
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
"""

import os
import json
import hashlib
from email import policy
from email.parser import BytesParser

def _safe_name(name: str, default="unnamed"):
    if not name:
        return default
    name = name.replace("\\", "_").replace("/", "_")
    forbidden = '<>:"|?*'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name.strip() or default

def _unique_path(base_dir: str, filename: str):
    filename = _safe_name(filename)
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        return path
    name, ext = os.path.splitext(filename)
    i = 1
    while True:
        cand = os.path.join(base_dir, f"{name}_{i}{ext}")
        if not os.path.exists(cand):
            return cand
        i += 1

def _extract_best_text(m):
    if m.get_content_type() == "text/plain":
        return m.get_content()
    for part in m.walk():
        if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
            try:
                return part.get_content()
            except Exception:
                payload = part.get_payload(decode=True)
                try:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace") if payload else None
                except Exception:
                    return None
    return None

def _extract_best_html(m):
    if m.get_content_type() == "text/html":
        return m.get_content()
    for part in m.walk():
        if part.get_content_type() == "text/html" and part.get_content_disposition() != "attachment":
            try:
                return part.get_content()
            except Exception:
                payload = part.get_payload(decode=True)
                try:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace") if payload else None
                except Exception:
                    return None
    return None

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def export_eml(case_dir, file_entry, size, offset, chunk_size):
    """
    Exporta un archivo .eml con metadatos forenses:
      - Crea carpeta: <case_dir>/<nombre.eml>/
      - Guarda 'original.eml'
      - Extrae adjuntos
      - Genera 'headers_body.txt', 'body.txt', 'body.html'
      - Genera 'headers.json'
      - Genera 'hashes.json' con SHA256 de cada artefacto
    """
    nombre_eml = file_entry.info.name.name.decode("utf-8", errors="ignore")
    carpeta_destino = os.path.join(case_dir, _safe_name(nombre_eml))
    os.makedirs(carpeta_destino, exist_ok=True)

    # 1) Guardar copia íntegra
    eml_path = os.path.join(carpeta_destino, "original.eml")
    with open(eml_path, "wb") as f:
        cur = offset
        while cur < size:
            data = file_entry.read_random(cur, min(chunk_size, size - cur))
            if not data:
                break
            f.write(data)
            cur += len(data)

    # 2) Parsear mensaje
    with open(eml_path, "rb") as f:
        contenido = f.read()
    mensaje = BytesParser(policy=policy.default).parsebytes(contenido)

    # 3) Extraer partes
    text_plain = _extract_best_text(mensaje)
    html_body = _extract_best_html(mensaje)

    if text_plain:
        with open(os.path.join(carpeta_destino, "body.txt"), "w", encoding="utf-8", errors="replace") as bf:
            bf.write(text_plain)

    if html_body:
        with open(os.path.join(carpeta_destino, "body.html"), "w", encoding="utf-8", errors="replace") as hf:
            hf.write(html_body)

    # 4) Extraer adjuntos
    adjuntos = []
    for parte in mensaje.walk():
        if parte.get_content_disposition() == 'attachment':
            nombre_archivo = parte.get_filename()
            if not nombre_archivo:
                ext = ""
                ctype = parte.get_content_type()
                if ctype and "/" in ctype:
                    ext = "." + ctype.split("/", 1)[1].split(";")[0].strip()
                nombre_archivo = f"attachment{ext}"
            payload = parte.get_payload(decode=True)
            if isinstance(payload, str):
                payload = payload.encode(errors="ignore")
            if payload:
                ruta_salida = _unique_path(carpeta_destino, nombre_archivo)
                with open(ruta_salida, 'wb') as adjunto:
                    adjunto.write(payload)
                adjuntos.append(os.path.basename(ruta_salida))

    # 5) Guardar headers legibles
    headers = {
        "From": mensaje.get("From", ""),
        "To": mensaje.get("To", ""),
        "Cc": mensaje.get("Cc", ""),
        "Bcc": mensaje.get("Bcc", ""),
        "Subject": mensaje.get("Subject", ""),
        "Date": mensaje.get("Date", ""),
        "Message-ID": mensaje.get("Message-ID", "")
    }

    resumen_path = os.path.join(carpeta_destino, "headers_body.txt")
    with open(resumen_path, "w", encoding="utf-8", errors="replace") as rf:
        rf.write("=== HEADERS ===\n")
        for k, v in headers.items():
            rf.write(f"{k}: {v}\n")
        rf.write("\n=== BODY (text/plain) ===\n")
        rf.write(text_plain or "(no text/plain)\n")
        if html_body:
            rf.write("\n=== NOTE ===\nEste mensaje tiene parte HTML. Revisa 'body.html'.\n")

    # 6) Guardar headers.json
    with open(os.path.join(carpeta_destino, "headers.json"), "w", encoding="utf-8") as jf:
        json.dump(headers, jf, indent=2, ensure_ascii=False)

    # 7) Hashes SHA256
    hashes = {"original.eml": _sha256(eml_path)}
    for fname in adjuntos:
        ruta = os.path.join(carpeta_destino, fname)
        hashes[fname] = _sha256(ruta)
    with open(os.path.join(carpeta_destino, "hashes.json"), "w", encoding="utf-8") as hf:
        json.dump(hashes, hf, indent=2, ensure_ascii=False)
