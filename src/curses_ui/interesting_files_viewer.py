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

class InterestingFilesViewer(Renderizable):
    def __init__(self, win, dir_interesantes, db_path):
        self.win = win
        self.db_path = db_path
        self.dir_interesantes = dir_interesantes
        self.categories = {
            '.pdf': [], '.doc': [], '.txt': [], '.snt': [], '.pst': [],
            '.ost': [], '.zip': [], '.rar': [], '.7z': [], 'Papelera restaurada': []
        }
        self.selected_index = 0
        self.current_category = None
        self.scroll_offset = 0
        self._load_files()

    def _load_files(self):
        for root, _, files in os.walk(self.dir_interesantes):
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
                filepath = os.path.basename(archivos[self.selected_index])
                _mostrar_info_extra(filepath, self.db_path)
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
        view.render()
        key = layout.win.getch()
        if key in [27]:
            layout.clear()
            break
        view.handle_input(key)
