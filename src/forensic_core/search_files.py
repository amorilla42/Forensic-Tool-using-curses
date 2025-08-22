import sqlite3
import os
from curses_ui.search_files_menu import SearchFilesMenu
from forensic_core.e01_reader import open_e01_image
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_input import AwesomeInput
from curses_ui.awesome_menu2 import AwesomeMenu
from curses_ui.file_viewer_panel import FileViewerPanel
import pytsk3
import pyewf
import curses
import textwrap
import requests
from forensic_core.export_file import exportar_archivo
from dotenv import load_dotenv, find_dotenv


def _popup_scroll(win, title, body):
    max_y, max_x = win.getmaxyx()
    pop = curses.newwin(max_y, max_x, 3, 0)
    pop.keypad(True)
    lines = body.splitlines() if body else ["(sin datos)"]
    off = 0
    vis = max_y - 2
    while True:
        pop.clear()
        pop.box()
        pop.addstr(0, max(2, (max_x - len(title) - 2) // 2), f" {title} ", curses.A_BOLD)
        for i, line in enumerate(lines[off:off+vis]):
            pop.addstr(1 + i, 2, line[:max_x-4])
        footer = " ↑/↓: scroll   q/ESC: salir "
        pop.addstr(max_y - 1, max(2, (max_x - len(footer)) // 2), footer, curses.A_DIM)
        pop.refresh()
        k = pop.getch()
        if k in (27, ord('q')):
            win.clear()
            win.refresh()
            break
        elif k == curses.KEY_UP and off > 0:
            off -= 1
        elif k == curses.KEY_DOWN and off + vis < len(lines):
            off += 1

def _fmt_ts(ts):
    from datetime import datetime
    try:
        return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return "N/A"

def vt_query_and_format(sha256, api_key):
    if not sha256 or not str(sha256).strip():
        return "No se puede consultar: SHA-256 no disponible."
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/files/{sha256}",
            headers={"accept": "application/json", "x-apikey": api_key},
            timeout=20
        )
    except Exception as e:
        return f"Error de red consultando VirusTotal:\n{e}"

    if r.status_code == 404:
        return f"VirusTotal: archivo {sha256} no encontrado (404)."
    if r.status_code in (401, 403):
        return f"Error {r.status_code} de autorización en VirusTotal. Revisa APIVIRUSTOTAL."
    if r.status_code == 429:
        return "VirusTotal: límite de cuota alcanzado (429). Intenta más tarde."
    if r.status_code != 200:
        txt = r.text[:400].replace("\n", " ")
        return f"HTTP {r.status_code} desde VirusTotal:\n{txt}"

    try:
        data = r.json()
    except Exception:
        return "Respuesta de VirusTotal no es JSON válido."

    attrs = data.get("data", {}).get("attributes", {}) or {}
    stats = attrs.get("last_analysis_stats", {}) or {}

    lines = []
    lines.append(f"SHA-256: {sha256}")
    lines.append(
        f"Detecciones: {stats.get('malicious',0)} malic. | "
        f"{stats.get('suspicious',0)} sosp. | "
        f"{stats.get('undetected',0)} no det. | "
        f"{stats.get('harmless',0)} benignos"
    )
    if 'reputation' in attrs:
        lines.append(f"Reputación: {attrs['reputation']}")
    if 'type_description' in attrs:
        lines.append(f"Tipo: {attrs['type_description']}")
    if 'size' in attrs:
        lines.append(f"Tamaño (VT): {attrs['size']} bytes")

    fs = _fmt_ts(attrs.get("first_submission_date"))
    ls = _fmt_ts(attrs.get("last_submission_date"))
    lines.append(f"Primera subida: {fs} | Última: {ls}")

    results = attrs.get("last_analysis_results", {}) or {}
    mal = [(e, v.get("result","")) for e, v in results.items() if v.get("category") == "malicious"]
    if mal:
        lines.append("")
        lines.append("Motores que detectan (top 10):")
        for eng, verdict in mal[:10]:
            lines.append(f"  - {eng}: {verdict}")
        if len(mal) > 10:
            lines.append(f"  ... y {len(mal)-10} más")

    # URL del informe web de VirusTotal
    lines.append("")
    lines.append(f"Informe web: https://www.virustotal.com/gui/file/{sha256}")

    return "\n".join(lines)


def show_virustotal_popup(win, sha256):
    load_dotenv(find_dotenv())
    api_key = os.getenv("APIVIRUSTOTAL")
    if not api_key:
        _popup_scroll(win, "VirusTotal", "No hay API key (APIVIRUSTOTAL) configurada.")
        return
    body = vt_query_and_format(sha256.strip(), api_key)
    _popup_scroll(win, "VirusTotal (hash)", body)
    win.refresh()



def search_files(db_path, case_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Introduce el parametro de busqueda")
    layout.change_footer("Presiona ENTER para buscar, ESC para salir")

    query = AwesomeInput(layout.body_win).render()

    if query is None:
        layout.clear()
        return

    cursor.execute("SELECT * FROM filesystem_entry WHERE type !='dir' AND full_path LIKE ?", ('%' + query + '%',))
    results = cursor.fetchall()
    conn.close()
    if not results:
        print("No se encontraron resultados.")
        return
    layout.change_header(f"Busqueda: {query}")
    layout.change_footer("Presiona ENTER para seleccionar, ESC para salir")


    menu = SearchFilesMenu(
        title="Resultados de la busqueda, presiona ENTER para seleccionar, ESC para salir",
        options=[f"{result[3]} ({result[6]} bytes)" for result in results],
        info=[result[2] for result in results],
        win=layout.body_win)
    selected = menu.render()
    
    while selected is not None:
        selected_file = results[selected]
        layout.change_header(f"Seleccionaste: {selected_file[3]}")
        layout.change_footer("TAB: alternar entre ventanas| ↑/↓ ←/→: desplazamiento de texto| ENTER: exportar archivo| v: Analizar VirusTotal| ESC: Salir")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        #LA BASE DE DATOS LAS PARTICIONES ESTAN CON ID 1 MENOS
        cursor.execute("SELECT block_size FROM partition_info WHERE partition_id = ?", (selected_file[1]+1,))
        block_size = cursor.fetchone()[0]

        partition_offset_sectors = cursor.execute(
            "SELECT partition_offset from partition_info WHERE partition_id = ?", (selected_file[1]+1,)
        ).fetchone()[0]
        
        partition_offset_bytes = partition_offset_sectors


        cursor.execute("SELECT e01_path FROM case_info")
        path = cursor.fetchall()

        sha_row = cursor.execute(
            "SELECT sha256, size FROM filesystem_entry WHERE entry_id = ?",
            (selected_file[0],)
        ).fetchone()
        sha256_db = sha_row[0] if sha_row else None
        size_db   = sha_row[1] if sha_row else None

        conn.close()

        metadata2, content_lines2 = get_info_file2(
            ewf_path=path[0][0],
            partition_offset=partition_offset_bytes,
            path=selected_file[2],
            layout=layout
        )

        if sha256_db and str(sha256_db).strip():
            metadata2["SHA-256"] = str(sha256_db).strip()
        else:
            if (size_db == 0) or (size_db is None and selected_file[6] == 0):
                metadata2["SHA-256"] = "— (no calculado: tamaño 0 bytes)"
            else:
                metadata2["SHA-256"] = "— (no disponible)"

        def _do_vt():
            sha = None
            # prioriza el de BD si existe
            if sha256_db and str(sha256_db).strip():
                sha = str(sha256_db).strip()
            else:
                s = str(metadata2.get("SHA-256",""))
                if s and not s.startswith("—"):
                    sha = s.strip()
            if not sha:
                _popup_scroll(layout.body_win, "VirusTotal", "No se puede consultar: SHA-256 no disponible (posible tamaño 0 bytes).")
                return
            show_virustotal_popup(layout.body_win, sha)


        extraer = FileViewerPanel(metadata2, content_lines2, layout.body_win, on_key_v=_do_vt).render()
        if extraer:
            exportar_archivo(
                case_dir=case_dir,
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
    


def format_timestamp(ts):
    from datetime import datetime
    try:
        if ts == 0:
            return "N/A"
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError, TypeError):
        return "Inválido"

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
        "Creacion": format_timestamp(meta.crtime),
        "Modificacion": format_timestamp(meta.mtime),
        "Acceso": format_timestamp(meta.atime),
        "Cambio": format_timestamp(meta.ctime),
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


def get_info_file2(ewf_path, partition_offset, path, layout):
    img = open_e01_image(ewf_path)
    file_obj, content = extract_file_info2(img, partition_offset, path, layout)
    
    if file_obj is None:
        layout.change_footer("No se pudo abrir el archivo.")
        return {}, []
    if content is None:
        layout.change_footer("No se pudo leer el contenido del archivo.")
        return {}, []
    metadata = get_file_metadata(file_obj)
    content_lines = prepare_content_lines(content)
    return metadata, content_lines