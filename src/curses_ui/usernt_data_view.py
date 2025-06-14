import curses
import sqlite3
import os
from .renderizable import Renderizable


def show_scrollable_popup(win, text, title=" Detalles ", footer=" ↑/↓ para desplazarse, ESC para salir "):
    max_y, max_x = win.getmaxyx()
    popup = curses.newwin(max_y, max_x, 0, 0)
    popup.keypad(True)

    lines = text.split("\n")
    header_line = lines[0] if lines else ""
    body_lines = lines[1:] if len(lines) > 1 else []

    scroll_offset = 0
    cursor_index = 0
    content_height = max_y - 3  # sin header y footer

    while True:
        popup.clear()
        popup.box()
        popup.addstr(0, max(1, (max_x - len(title)) // 2), title[:max_x - 2])
        popup.addstr(max_y - 1, max(1, (max_x - len(footer)) // 2), footer[:max_x - 2])

        popup.addstr(1, 2, header_line[:max_x - 4], curses.A_BOLD | curses.A_UNDERLINE)

        visible_lines = body_lines[scroll_offset:scroll_offset + content_height]

        for i, line in enumerate(visible_lines):
            attr = curses.A_REVERSE if i == cursor_index else curses.A_NORMAL
            popup.addstr(i + 2, 2, line[:max_x - 4], attr)

        popup.refresh()
        key = popup.getch()

        if key in [27, ord("q")]:
            break
        elif key == curses.KEY_UP:
            if cursor_index > 0:
                cursor_index -= 1
            elif scroll_offset > 0:
                scroll_offset -= 1
        elif key == curses.KEY_DOWN:
            if cursor_index < len(visible_lines) - 1:
                cursor_index += 1
            elif scroll_offset + content_height < len(body_lines):
                scroll_offset += 1


def format_userassist_table(lines, screen_width=120):
    tipo_w = int(screen_width * 0.20)
    ruta_w = int(screen_width * 0.50)
    count_w = int(screen_width * 0.08)
    tiempo_w = screen_width - (tipo_w + ruta_w + count_w + 9)

    output = []
    header = f"{'Tipo':<{tipo_w}}│ {'Ruta / Identificador':<{ruta_w}}│ {'Veces':^{count_w}} │ {'Última ejecución':<{tiempo_w}}"
    separator = "─" * min(screen_width, len(header))
    output.append(header)
    output.append(separator)

    for line in lines:
        parsed = parse_userassist_line(line)
        if parsed:
            tipo, ruta, count, tiempo = parsed
            output.append(f"{tipo:<{tipo_w}}│ {ruta:<{ruta_w}}│ {count:^{count_w}} │ {tiempo:<{tiempo_w}}")

    return "\n".join(output)


def parse_userassist_line(line):
    try:
        if ":" not in line:
            return None
        tipo, resto = line.split(":", 1)
        partes = [x.strip() for x in resto.rsplit(",", 2)]
        if len(partes) != 3:
            return None
        ruta, count, tiempo = partes
        if not ruta or ruta == "":
            return None
        return tipo.strip(), ruta.strip(), count, tiempo
    except Exception:
        return None




class UserntDataViewer(Renderizable):
    def __init__(self, win, db_path, export_path):
        self.win = win
        self.db_path = db_path
        self.users = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.show_system_entries = False
        self.export_path = export_path
        self._load_users()

    def _load_users(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY username")
        self.users = [row[0] for row in cursor.fetchall()]
        conn.close()

    def clear(self):
        self.win.clear()

    def render(self):
        self.clear()
        max_y, max_x = self.win.getmaxyx()
        visible_height = max_y - 2

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_height:
            self.scroll_offset = self.selected_index - visible_height + 1

        visible_entries = self.users[self.scroll_offset:self.scroll_offset + visible_height]

        self.win.addstr(0, 3, "Usuarios disponibles (ENTER para ver resumen)", curses.A_BOLD)
        for idx, username in enumerate(visible_entries):
            screen_idx = idx + 1
            entry_idx = self.scroll_offset + idx
            if entry_idx == self.selected_index:
                self.win.addstr(screen_idx, 3, username[:max_x - 4], curses.A_REVERSE)
            else:
                self.win.addstr(screen_idx, 3, username[:max_x - 4])

        self.win.refresh()

    def handle_input(self, key):
        total_items = len(self.users)

        if key == curses.KEY_DOWN:
            self.selected_index = min(self.selected_index + 1, total_items - 1)
        elif key == curses.KEY_UP:
            self.selected_index = max(self.selected_index - 1, 0)
        elif key in [10, 13]:  # ENTER
            self._show_user_menu(self.users[self.selected_index])

    def _show_user_menu(self, username):
        options = [
            "Programas ejecutados (Menú Inicio)",
            "Documentos recientes",
            "Comandos ejecutados (Win+R)",
            "Dispositivos conectados (USB y similares)",
            "Archivos abiertos/guardados recientemente",
            "Ejecuciones visualizadas por Explorer",
            "Exportar toda la información a archivo .txt",
            "Activar/Desactivar entradas del sistema en MuiCache"
        ]

        selected = 0
        while True:
            self.clear()
            max_y, max_x = self.win.getmaxyx()
            self.win.addstr(0, 2, f"Resumen para: {username}", curses.A_BOLD)
            self.win.addstr(1, 2, "Selecciona una categoría:", curses.A_UNDERLINE)

            for i, option in enumerate(options):
                attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
                self.win.addstr(i + 3, 4, option, attr)

            self.win.refresh()
            key = self.win.getch()

            if key == curses.KEY_UP:
                selected = (selected - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(options)
            elif key in [10, 13]:
                if selected < 6:
                    self._show_category_data(username, selected)
                elif selected == 6:
                    self._export_user_data(username)
                elif selected == 7:
                    self.show_system_entries = not self.show_system_entries
            elif key in [27, ord("q")]:
                break

    def _show_category_data(self, username, index):
        mapping = [
            ("userassist", "name, run_count, last_run_time"),
            ("recent_docs", "extension, document_name"),
            ("run_mru", "order_key, command"),
            ("mountpoints2", "key_name, volume_label, data"),
            ("open_save_mru", "extension, entry_name, path"),
            ("muicache", "entry_name, description")
        ]

        table, fields = mapping[index]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {fields} FROM {table} WHERE username=?", (username,))
        rows = cursor.fetchall()
        conn.close()

        section_titles = [
            "Programas ejecutados desde Menú Inicio",
            "Documentos abiertos recientemente",
            "Comandos lanzados con Win+R",
            "Dispositivos externos conectados",
            "Archivos recientes en diálogos Abrir/Guardar",
            "Programas visualizados en Explorer (MuiCache)"
        ]

        if index == 0:
            max_y, max_x = self.win.getmaxyx()
            info = format_userassist_table([", ".join(str(col) for col in row) for row in rows], screen_width=max_x - 4)
        else:
            info = f"{section_titles[index]}\nUsuario: {username}\n\n"
            if not rows:
                info += "(Sin datos disponibles)"
            else:
                for row in rows:
                    if index == 5 and not self.show_system_entries:
                        if str(row[0]).lower().startswith("@shell32.dll") or str(row[0]).lower().startswith("@c:\\windows"):
                            continue
                    info += ", ".join(str(col) for col in row) + "\n"

        show_scrollable_popup(self.win, info, section_titles[index])

    def _export_user_data(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sections = [
            ("userassist", "Programas ejecutados desde Menú Inicio", "name, run_count, last_run_time"),
            ("recent_docs", "Documentos abiertos recientemente", "extension, document_name"),
            ("run_mru", "Comandos lanzados con Win+R", "order_key, command"),
            ("mountpoints2", "Dispositivos externos conectados", "key_name, volume_label, data"),
            ("open_save_mru", "Archivos recientes en diálogos Abrir/Guardar", "extension, entry_name, path"),
            ("muicache", "Programas visualizados en Explorer (MuiCache)", "entry_name, description")
        ]

        output = f"Resumen forense de usuario: {username}\n\n"
        for table, title, fields in sections:
            cursor.execute(f"SELECT {fields} FROM {table} WHERE username=?", (username,))
            rows = cursor.fetchall()
            output += f"== {title} ==\n"
            if not rows:
                output += "(Sin datos disponibles)\n"
            else:
                for row in rows:
                    if table == "muicache" and not self.show_system_entries:
                        if str(row[0]).lower().startswith("@shell32.dll") or str(row[0]).lower().startswith("@c:\\windows"):
                            continue
                    output += ", ".join(str(col) for col in row) + "\n"
            output += "\n"

        conn.close()

        os.makedirs(self.export_path, exist_ok=True)
        filename = f"{self.export_path}/{username}_forensic_report.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output)

        show_scrollable_popup(self.win, f"Datos exportados correctamente a:\n{filename}", "Exportación exitosa")
