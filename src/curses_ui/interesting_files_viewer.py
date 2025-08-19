import curses
import os

from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.file_viewer_panel import FileViewerPanel
from forensic_core.artifact_extractor import exportar_archivos_interesantes
from forensic_core.search_files import get_info_file2
from utils.text_sanitizer import TextSanitizer
from .renderizable import Renderizable

def show_scrollable_file_popup(win, content, title=" Contenido del archivo ", footer=" ↑/↓ para desplazarse verticalmente, ←/→ horizontalmente, q o ESC para salir "):
    max_y, max_x = win.getmaxyx()
    popup = curses.newwin(max_y, max_x, 3, 0)
    popup.keypad(True)

    lines = content.split("\n")
    scroll_offset = 0
    horizontal_offset = 0 
    visible_height = max_y - 3
    max_line_length = max(len(TextSanitizer.clean(line)) for line in lines)

    while True:
        popup.clear()
        popup.box()
        popup.addstr(0, max(1, (max_x - len(title)) // 2), title[:max_x - 2])
        popup.addstr(max_y - 1, max(1, (max_x - len(footer)) // 2), footer[:max_x - 2])

        visible_lines = lines[scroll_offset:scroll_offset + visible_height]
        for i, line in enumerate(visible_lines):
            linesafe = TextSanitizer.clean(line)
            visible_width = max_x - 4  # espacio horizontal disponible
            line_segment = linesafe[horizontal_offset:horizontal_offset + visible_width]

            # Indicadores visuales de scroll
            if horizontal_offset > 0:
                line_segment = "←" + line_segment[1:]  # muestra flecha izquierda
            if horizontal_offset + visible_width < len(linesafe):
                line_segment = line_segment[:-1] + "→"  # muestra flecha derecha

            popup.addstr(i + 1, 2, line_segment)

        popup.refresh()
        key = popup.getch()

        if key in [27, ord("q")]:
            break
        elif key == curses.KEY_UP and scroll_offset > 0:
            scroll_offset -= 1
        elif key == curses.KEY_DOWN and scroll_offset + visible_height < len(lines):
            scroll_offset += 1
        elif key == curses.KEY_LEFT and horizontal_offset > 0:
            horizontal_offset -= 4  # cantidad de columnas a desplazar
        elif key == curses.KEY_RIGHT and horizontal_offset + max_x - 4 < max_line_length:
            horizontal_offset += 4


def _mostrar_menu_eml(win, dir_eml: str):
    parts, attachments = _eml_parts(dir_eml)
    opciones = [
        "Ver cabeceras (headers_body.txt)",
        "Ver cuerpo (body.txt)",
        "Ver HTML (body.html)",
        "Listar adjuntos",
        "Ver .eml crudo (original.eml)"
    ]
    sel = 0
    footer = "ENTER: Seleccionar, ↑/↓: Mover, h/b/w/a: headers/body/html/adjuntos, q/ESC: Salir"
    while True:
        win.clear()
        win.box()
        max_y, max_x = win.getmaxyx()
        titulo = f"Email: {os.path.basename(dir_eml)}"
        win.addstr(0, max(1, (max_x - len(titulo)) // 2), titulo[:max_x - 2], curses.A_BOLD)
        win.addstr(max_y - 1, max(1, (max_x - len(footer)) // 2), footer[:max_x - 2])
        for i, opt in enumerate(opciones):
            attr = curses.A_REVERSE if i == sel else curses.A_NORMAL
            win.addstr(3 + i, 6, opt, attr)
        win.refresh()

        key = win.getch()
        if key in [ord('q'), 27]:
            break
        elif key == curses.KEY_UP:
            sel = max(sel - 1, 0)
        elif key == curses.KEY_DOWN:
            sel = min(sel + 1, len(opciones) - 1)
        elif key in [10, 13] or key in [ord('h'), ord('b'), ord('w'), ord('a')]:
            # Atajos:
            if key == ord('h'): sel = 0
            elif key == ord('b'): sel = 1
            elif key == ord('w'): sel = 2
            elif key == ord('a'): sel = 3

            target = None
            if sel == 0:
                # Ver headers_body.txt
                target = parts["headers_body"]
                content = _open_text_file_safepath(target) if os.path.exists(target) else "[No hay headers_body.txt]"
                show_scrollable_file_popup(win, content, "headers_body.txt")
            elif sel == 1:
                # Ver body.txt
                target = parts["body_txt"]
                content = _open_text_file_safepath(target) if os.path.exists(target) else "[No hay body.txt]"
                show_scrollable_file_popup(win, content, "body.txt")
            elif sel == 2:
                # Ver body.html
                target = parts["body_html"]
                content = _open_text_file_safepath(target) if os.path.exists(target) else "[No hay body.html]"
                show_scrollable_file_popup(win, content, "body.html")
            elif sel == 3:
                # Listar adjuntos
                if not attachments:
                    show_scrollable_file_popup(win, "[No hay adjuntos]", "Adjuntos")
                else:
                    _menu_adjuntos(win, attachments)
            elif sel == 4:
                # Ver .eml crudo
                if os.path.exists(parts["original"]):
                    content = _open_text_file_safepath(parts["original"])
                else:
                    content = "[No existe original.eml]"
                show_scrollable_file_popup(win, content, "original.eml")

def _menu_adjuntos(win, attachments):
    sel = 0
    titulo = "Adjuntos"
    footer = "ENTER: Seleccionar, ↑/↓: Mover, q/ESC: Salir"

    while True:
        win.clear()
        win.box()
        max_y, max_x = win.getmaxyx()

        win.addstr(0, max(1, (max_x - len(titulo)) // 2), titulo[:max_x - 2], curses.A_BOLD)
        win.addstr(max_y - 1, max(1, (max_x - len(footer)) // 2), footer[:max_x - 2])

        visible_h = max_y - 4
        start = max(0, min(sel - visible_h + 1, max(0, len(attachments) - visible_h)))
        for i, apath in enumerate(attachments[start:start+visible_h]):
            attr = curses.A_REVERSE if (start + i) == sel else curses.A_NORMAL
            name = apath.replace("\\", "/")
            name = name[name.rfind("/") + 1:]
            win.addstr(3 + i, 6, name[:max_x - 8], attr)
        win.refresh()

        key = win.getch()
        if key in [ord('q'), 27]:
            break
        elif key == curses.KEY_UP:
            sel = max(sel - 1, 0)
        elif key == curses.KEY_DOWN:
            sel = min(sel + 1, len(attachments) - 1)
        elif key in [10, 13]:
            # Abrir adjunto como texto printeable
            content = _open_text_file_safepath(attachments[sel])
            show_scrollable_file_popup(win, content, os.path.basename(attachments[sel]))


class InterestingFilesViewer(Renderizable):
    def __init__(self, win, dir_interesantes, db_path):
        self.win = win
        self.db_path = db_path
        self.dir_interesantes = dir_interesantes
        self.categories = {
            '.pdf': [], '.doc': [], '.txt': [], '.snt': [], '.pst': [],
            '.ost': [], '.zip': [], '.rar': [], '.7z': [], '.eml': [] , 'Papelera restaurada': []
        }
        self.selected_index = 0
        self.current_category = None
        self.scroll_offset = 0
        self._load_files()

    def _load_files(self):
        for root, dirs, files in os.walk(self.dir_interesantes):
            # 1) Primero recoge carpetas .eml
            for d in dirs:
                full = os.path.join(root, d)
                if _is_eml_dir(full):
                    # mostramos la carpeta como "archivo" en la categoría .eml
                    self.categories['.eml'].append(full)

            # 2) Luego ficheros normales
            for f in files:
                path = os.path.join(root, f)
                if ".meta." in f:
                    continue
                if f.startswith("$I") or f.startswith("$R"):
                    continue
                if os.path.exists(path + ".meta.txt"):
                    self.categories['Papelera restaurada'].append(path)
                    continue
                ext = os.path.splitext(f)[1].lower()
                # evitar meter los ficheros internos de una carpeta .eml como elementos sueltos
                if root.lower().endswith(".eml"):
                    continue
                if ext in self.categories:
                    self.categories[ext].append(path)

    def clear(self):
        self.win.clear()

    def render(self):
        self.clear()
        max_y, max_x = self.win.getmaxyx()
        visible_height = max_y - 2

        if self.current_category is None:
            categorias = list(self.categories.keys())
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + visible_height:
                self.scroll_offset = self.selected_index - visible_height + 1

            visible_cats = categorias[self.scroll_offset:self.scroll_offset + visible_height]

            self.win.addstr(0, 3, "Categorías de archivos interesantes (ENTER para ver)", curses.A_BOLD)
            for idx, ext in enumerate(visible_cats):
                attr = curses.A_REVERSE if (self.scroll_offset + idx) == self.selected_index else curses.A_NORMAL
                self.win.addstr(idx + 1, 4, f"{ext} ({len(self.categories[ext])} archivos)", attr)

        else:
            archivos = self.categories[self.current_category]
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + visible_height:
                self.scroll_offset = self.selected_index - visible_height + 1

            visible_archivos = archivos[self.scroll_offset:self.scroll_offset + visible_height]

            self.win.addstr(0, 3, f"Archivos {self.current_category} (q para volver)", curses.A_BOLD)
            for idx, file_path in enumerate(visible_archivos):
                nombre = os.path.basename(file_path)
                attr = curses.A_REVERSE if (self.scroll_offset + idx) == self.selected_index else curses.A_NORMAL
                self.win.addstr(idx + 1, 4, nombre[:max_x - 6], attr)

        self.win.refresh()

    def _rtf_to_plain_text(self, rtf):
        import re
        rtf = re.sub(r'^{\\rtf1.*?\\viewkind\d+\\uc\d+\s?', '', rtf, flags=re.DOTALL)
        rtf = re.sub(r'\\[a-z]+\d*', '', rtf)
        rtf = re.sub(r'{|}|\\', '', rtf)
        rtf = rtf.replace('\r\n', '\n').replace('\r', '\n')
        return rtf.strip()
    
    def _buscar_metadatos_asociados(self, filepath):
        meta_path = filepath + ".meta.txt"
        if os.path.exists(meta_path):
            return meta_path
        return None

    def handle_input(self, key):
        if self.current_category is None:
            total = len(self.categories)
            keys = list(self.categories.keys())

            if key == curses.KEY_DOWN:
                self.selected_index = min(self.selected_index + 1, total - 1)
            elif key == curses.KEY_UP:
                self.selected_index = max(self.selected_index - 1, 0)
            elif key in [10, 13] and self.categories[keys[self.selected_index]]:
                self.current_category = keys[self.selected_index]
                self.selected_index = 0
                self.scroll_offset = 0
        else:
            archivos = self.categories[self.current_category]
            total = len(archivos)

            if key in [ord('i')]:
                if self.current_category != 'Papelera restaurada':
                    filepath = os.path.basename(archivos[self.selected_index])
                    _mostrar_info_extra(filepath, self.db_path)
                return
            if key == curses.KEY_DOWN:
                self.selected_index = min(self.selected_index + 1, total - 1)
            elif key == curses.KEY_UP:
                self.selected_index = max(self.selected_index - 1, 0)
            elif key in [ord('q')]:
                self.current_category = None
                self.selected_index = 0
                self.scroll_offset = 0
            elif key in [10, 13]:
                filepath = archivos[self.selected_index]

                if self.current_category == '.eml' and os.path.isdir(filepath):
                    _mostrar_menu_eml(self.win, filepath)
                    return

                meta_path = self._buscar_metadatos_asociados(filepath)

                if meta_path:
                    opciones = ["Ver contenido del archivo", "Ver metadatos asociados"]
                    seleccion = 0

                    while True:
                        self.win.clear()
                        self.win.box()
                        self.win.addstr(1, 4, f"Archivo: {os.path.basename(filepath)}", curses.A_BOLD)
                        for i, opt in enumerate(opciones):
                            attr = curses.A_REVERSE if i == seleccion else curses.A_NORMAL
                            self.win.addstr(3 + i, 6, opt, attr)
                        self.win.addstr(self.win.getmaxyx()[0] - 2, 4, "ENTER: Seleccionar, ↑/↓: Mover, q o ESC: Cancelar")
                        self.win.refresh()

                        key2 = self.win.getch()
                        if key2 in [ord("q"), 27]:
                            break
                        elif key2 == curses.KEY_UP:
                            seleccion = max(seleccion - 1, 0)
                        elif key2 == curses.KEY_DOWN:
                            seleccion = min(seleccion + 1, len(opciones) - 1)
                        elif key2 in [10, 13]:
                            target_path = filepath if seleccion == 0 else meta_path
                            try:
                                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                                    content = f.read()
                                if target_path.endswith(".snt"):
                                    content = self._rtf_to_plain_text(content)
                                if target_path.endswith(".pdf"):
                                    content = extraer_texto_pdf(target_path)
                            except Exception as e:
                                content = f"[!] Error al abrir el archivo: {e}"

                            show_scrollable_file_popup(self.win, content, os.path.basename(target_path))
                            break

                else:
                    # Caso normal: no hay metadatos, mostrar directamente el archivo
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        if filepath.endswith(".snt"):
                            content = self._rtf_to_plain_text(content)
                        if filepath.endswith(".pdf"):
                            content = extraer_texto_pdf(filepath)
                    except Exception as e:
                        content = f"[!] Error al abrir el archivo: {e}"

                    show_scrollable_file_popup(self.win, content, os.path.basename(filepath))



def _is_eml_dir(path_dir: str) -> bool:
    if not os.path.isdir(path_dir):
        return False
    # una carpeta .eml con original.eml dentro
    if path_dir.lower().endswith(".eml") and os.path.exists(os.path.join(path_dir, "original.eml")):
        return True
    # si tiene headers.json y original.eml, cuenta como eml exportado
    if os.path.exists(os.path.join(path_dir, "original.eml")) and os.path.exists(os.path.join(path_dir, "headers.json")):
        return True
    return False

def _eml_parts(dir_eml: str):
    """
    Devuelve diccionario con rutas de partes estándar y lista de adjuntos.
    """
    parts = {
        "original": os.path.join(dir_eml, "original.eml"),
        "headers_body": os.path.join(dir_eml, "headers_body.txt"),
        "headers_json": os.path.join(dir_eml, "headers.json"),
        "hashes_json": os.path.join(dir_eml, "hashes.json"),
        "body_txt": os.path.join(dir_eml, "body.txt"),
        "body_html": os.path.join(dir_eml, "body.html"),
    }
    # adjuntos: cualquier archivo distinto de los anteriores
    exclude = set(os.path.basename(p) for p in parts.values() if p)
    attachments = []
    for root, _, files in os.walk(dir_eml):
        for f in files:
            if f in exclude:
                continue
            attachments.append(os.path.join(root, f))
    return parts, attachments

def _open_text_file_safepath(pathfile: str) -> str:
    try:
        with open(pathfile, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"[!] Error al abrir {os.path.basename(pathfile)}: {e}"





def extraer_texto_pdf(path_pdf):
    from pdfminer.high_level import extract_text
    import logging
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    try:
        texto = extract_text(path_pdf)
        return texto.strip() or "[PDF sin texto visible]"
    except Exception as e:
        return f"[!] Error al leer PDF: {e}"


def _mostrar_info_extra(file_path, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM filesystem_entry WHERE type !='dir' AND full_path LIKE ?", ('%' + file_path + '%',))
    selected_file = cursor.fetchall()[0]
    partition_offset_bytes = cursor.execute(
            "SELECT partition_offset from partition_info WHERE partition_id = ?", (selected_file[1]+1,)
    ).fetchone()[0]
    cursor.execute("SELECT e01_path FROM case_info")
    path = cursor.fetchall()
    sha_row = cursor.execute(
        "SELECT sha256, size FROM filesystem_entry WHERE entry_id = ?",
        (selected_file[0],)
    ).fetchone()
    sha256_db = sha_row[0] if sha_row else None
    size_db   = sha_row[1] if sha_row else None
    conn.close()
    layout=AwesomeLayout()
    layout.render()
    layout.change_header(f"Información extra de: {file_path}")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar")
    
    metadata, content_lines = get_info_file2(
            ewf_path=path[0][0],
            partition_offset=partition_offset_bytes,
            path=selected_file[2],
            layout=layout
        )

    if sha256_db and str(sha256_db).strip():
        metadata["SHA-256"] = str(sha256_db).strip()
    else:
        if (size_db == 0) or (size_db is None and selected_file[6] == 0):
            metadata["SHA-256"] = "— (no calculado: tamaño 0 bytes)"
        else:
            metadata["SHA-256"] = "— (no disponible)"


    FileViewerPanel(metadata, content_lines, layout.body_win).render()
    layout.change_header("Artefactos interesantes encontrados")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver archivos, i: Ver información extra de un archivo")


def visualizar_archivos_interesantes(db_path, caso_dir):
    layout = AwesomeLayout()
    dir_interesantes = os.path.join(caso_dir, "archivos_interesantes")
    #exportar_archivos_interesantes(db_path, caso_dir)
    layout.render()
    layout.change_header("Artefactos interesantes encontrados")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver archivos, i: Ver información extra de un archivo")
    view = InterestingFilesViewer(layout.body_win, dir_interesantes, db_path)
    view.render()
    view.win.keypad(True)
    while True:
        
        if view.current_category is None:
            # Pantalla de categorías: NO mencionar 'i'
            layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Entrar en categoría")
        else:
            if view.current_category == 'Papelera restaurada':
                # Dentro de Papelera: 'i' deshabilitado
                layout.change_footer("q: Volver, ↑/↓: Navegar, ENTER: Ver archivo")
            elif view.current_category == '.eml':
                # Emails: mostrar atajos propios
                layout.change_footer("q: Volver, ↑/↓: Navegar, ENTER: Seleccionar, ESC: Salir")
            else:
                # Resto de categorías: 'i' disponible
                layout.change_footer("q: Volver, ↑/↓: Navegar, ENTER: Ver archivo, i: Información extra, ESC: Salir")

        view.render()
        key = layout.win.getch()
        if key in [27]:
            layout.clear()
            break
        view.handle_input(key)
