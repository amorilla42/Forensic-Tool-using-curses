import curses
import textwrap
from Registry import Registry
from .renderizable import Renderizable
from datetime import datetime


class RegistryViewerPanel(Renderizable):
    def __init__(self, win, hive_path, tmp_path, layout):
        self.win = win
        self.hive_path = hive_path
        self.registry = Registry.Registry(hive_path)
        self.root_key = self.registry.root()
        self.current_key = self.root_key
        self.current_key_path = self.root_key.path()
        self.current_path = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.mode = "browse"
        self.search_term = ""
        self.results = []
        self.parent_stack = []
        self.tmp_path = tmp_path
        self.layout = layout

    def clear(self):
        self.win.clear()

    def render(self):
        self.clear()
        max_y, max_x = self.win.getmaxyx()
        breadcrumb = "\\".join(self.current_path) or self.registry.root().name()
        self.win.addstr(0, 0, f"Ruta: {breadcrumb}"[:max_x - 1], curses.A_BOLD)

        key = self._get_current_key()
        if key is None:
            self.win.addstr(2, 0, "Clave no encontrada.")
            self.win.refresh()
            return

        subkeys = key.subkeys()
        values = key.values()
        entries = [("[+] " + k.name(), "subkey") for k in subkeys]
        entries += [("[v] " + v.name(), "value") for v in values]

        visible_height = max_y - 3
        total_items = len(entries)

        # Corrige el scroll si está fuera de rango
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_height:
            self.scroll_offset = self.selected_index - visible_height + 1

        visible_entries = entries[self.scroll_offset:self.scroll_offset + visible_height]

        for idx, (name, typ) in enumerate(visible_entries):
            screen_idx = idx + 2
            entry_idx = self.scroll_offset + idx
            if entry_idx == self.selected_index:
                self.win.addstr(screen_idx, 0, name[:max_x - 1], curses.A_REVERSE)
            else:
                self.win.addstr(screen_idx, 0, name[:max_x - 1])

        self.win.refresh()

    def _get_current_key(self):
        try:
            key = self.registry.root()
            for p in self.current_path:
                key = key.subkey(p)
            return key
        except Registry.RegistryKeyNotFoundException:
            return None

    def _get_subkey_path(self, subkey):
        try:
            return subkey.path()
        except Exception:
            # En caso de que .path() no funcione correctamente por alguna razón
            return self.current_key_path + "\\" + subkey.name()



    def handle_input(self, key):
        current_key = self._get_current_key()
        total_items = len(current_key.subkeys()) + len(current_key.values())

        if key == curses.KEY_LEFT:
            if self.current_path:
                self.current_path.pop()
                self.selected_index = 0
                self.scroll_offset = 0
        if key == curses.KEY_DOWN:
            self.selected_index = min(self.selected_index + 1, total_items - 1)
        elif key == curses.KEY_UP:
            self.selected_index = max(self.selected_index - 1, 0)
        elif key in [10, 13]:  # ENTER
            self._select_item(current_key)
        elif key == ord("b"):
            self.search_mode()
        elif key == ord("e"):
            self._export_selected(current_key)
        elif key == ord("i"):
            self._show_info(current_key)
    
    def _select_item(self, key):
        subkeys = key.subkeys()
        values = key.values()
        if self.selected_index < len(subkeys):
            selected_subkey = subkeys[self.selected_index]
            self.current_path.append(selected_subkey.name())
            self.selected_index = 0
            self.scroll_offset = 0
        else:
            value_index = self.selected_index - len(subkeys)
            if value_index < len(values):
                selected_value = values[value_index]
                self._view_value(selected_value)



    def _view_value(self, value):
        self._popup(f"Nombre: {value.name()}\nTipo: {value.value_type_str()}\nValor: {value.value()}\nTamaño: {len(value.raw_data())} bytes",)

    def _show_info(self, key):
        try:
            subkeys = key.subkeys()
            values = key.values()
            total_items = len(subkeys) + len(values)
            
            if total_items == 0:
                self._popup("No hay subclaves ni valores en esta clave.", "Información", "Presiona cualquier tecla para continuar")
                return


            if self.selected_index < len(key.subkeys()):
                # Es una subclave
                target = key.subkeys()[self.selected_index]
                last_modified = target.timestamp().isoformat()
                info = f"Nombre: {target.name()}\nÚltima modificación: {last_modified}"
            else:
                # Es un valor
                value_index = self.selected_index - len(key.subkeys())
                target = key.values()[value_index]
                value_type = target.value_type_str()
                val = target.value()
                info = f"Nombre: {target.name()}\nTipo: {value_type}\n"

                if isinstance(val, bytes):
                    # Mostrar hexdump legible
                    hex_lines = []
                    for i in range(0, len(val), 16):
                        chunk = val[i:i+16]
                        hex_part = ' '.join(f'{b:02x}' for b in chunk)
                        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                        hex_lines.append(f"{hex_part:<48}  {ascii_part}")
                    hexdump = "\n".join(hex_lines)
                    info += f"Valor (hex):\n{hexdump}"
                    info += f"\nTamaño: {len(val)} bytes"
                else:
                    info += f"Valor: {val}"
                    raw = target.raw_data()
                    info += f"\nTamaño: {len(raw)} bytes" if raw else ""

            self._popup(info, "Información avanzada", "↑/↓: Navegar, Presiona cualquier otra tecla para continuar")
        except Exception as e:
            self._popup(f"Error obteniendo info: {e}", "Error", "Presiona cualquier tecla para continuar")



    def _export_selected(self, key):
        try:
            if self.selected_index < len(key.subkeys()):
                subkey = key.subkeys()[self.selected_index]
                export_path = f"{self.tmp_path}/{subkey.name()}.reg"
                with open(export_path, "w") as f:
                    f.write(f"[{subkey.path()}]\n")
                    for v in subkey.values():
                        f.write(f"\"{v.name()}\"={repr(v.value())}\n")
                self._popup(f"Clave exportada a: {export_path}", "Exportación exitosa", "Presiona cualquier tecla para continuar")
            else:
                value = key.values()[self.selected_index - len(key.subkeys())]
                export_path = f"{self.tmp_path}/{value.name()}.txt"
                with open(export_path, "w") as f:
                    f.write(str(value.value()))
                self._popup(f"Valor exportado a: {export_path}", "Exportación exitosa", "Presiona cualquier tecla para continuar")
        except Exception as e:
            self._popup(f"Error exportando: {e}", "Error de exportación", "Presiona cualquier tecla para continuar")

    def _show_search_results(self):
        index = 0
        while True:
            self.clear()
            max_y, max_x = self.win.getmaxyx()
            self.win.addstr(0, 0, "Resultados de búsqueda (ENTER para ir, q para salir)", curses.A_BOLD)

            visible_results = self.results[index:index + max_y - 2]
            for i, result in enumerate(visible_results):
                path = result[1] if result[0] == "subkey" else f"{result[1]}\\{result[2]}"
                attr = curses.A_REVERSE if i == 0 else curses.A_NORMAL
                self.win.addstr(i + 1, 0, path[:max_x - 1], attr)

            self.win.refresh()
            key = self.win.getch()

            if key == ord("q"):
                break
            elif key == curses.KEY_DOWN:
                if index + 1 < len(self.results):
                    index += 1
            elif key == curses.KEY_UP:
                if index > 0:
                    index -= 1
            elif key in [10, 13]:  # ENTER
                selected = self.results[index]
                if selected[0] == "subkey":
                    self.current_key_path = selected[1]
                    self.current_path = selected[1].split("\\")[1:]  # Omitir root
                elif selected[0] == "value":
                    self.current_key_path = selected[1]
                    self.current_path = selected[1].split("\\")[1:]
                self.selected_index = 0
                self.scroll_offset = 0
                break


    def _search_recursive(self, key, term):
        try:
            # Buscar en el nombre del subkey
            if term.lower() in key.name().lower():
                self.results.append(("subkey", key.path()))

            # Buscar en los nombres de los valores
            for val in key.values():
                if term.lower() in val.name().lower():
                    self.results.append(("value", key.path(), val.name()))

            # Recursividad en subkeys
            for subkey in key.subkeys():
                self._search_recursive(subkey, term)

        except Exception:
            pass  # Ignorar claves inaccesibles


    def search_mode(self):
        max_y, max_x = self.win.getmaxyx()
        popup_h = 5
        popup_w = 60
        popup_y = (max_y - popup_h) // 2
        popup_x = (max_x - popup_w) // 2

        win = curses.newwin(popup_h, popup_w, popup_y, popup_x)
        win.box()
        win.addstr(1, 2, "Introduce el término de búsqueda:")

        # Ventana para input justo debajo del texto
        input_win = curses.newwin(1, popup_w - 4, popup_y + 2, popup_x + 2)
        input_win.attrset(curses.A_REVERSE)
        input_win.refresh()

        curses.echo()
        win.refresh()
        search_term = input_win.getstr().decode("utf-8").strip()
        curses.noecho()

        if not search_term:
            return

        self.results = []
        self._search_recursive(self._get_current_key(), search_term)

        if not self.results:
            self._popup("No se encontraron resultados.", "Búsqueda", "Presiona cualquier tecla para continuar")
        else:
            self._show_search_results()


    def _popup(self, text, title=" Información básica ",footer=" ↑/↓: Navegar, Presiona cualquier otra tecla para continuar "):
        max_y, max_x = self.win.getmaxyx()
        popup_h = min(15, max_y - 4)
        popup_w = min(80, max_x - 4)
        popup_y = (max_y - popup_h) // 2
        popup_x = (max_x - popup_w) // 2

        # Preparamos el texto envuelto
        wrapped_lines = []
        for line in text.split("\n"):
            wrapped_lines.extend(textwrap.wrap(line, width=popup_w - 4) or [""])

        total_lines = len(wrapped_lines)
        scroll_pos = 0

        # Creamos la ventana una vez, activamos teclas especiales
        popup = curses.newwin(popup_h, popup_w, popup_y, popup_x)
        popup.keypad(True)

        while True:
            popup.erase()
            popup.box()
            #header del popup
            popup.addstr(0, (popup_w - len(title)) // 2, title)

            #contenido del popup
            for idx in range(popup_h - 2):
                line_index = scroll_pos + idx
                if line_index >= total_lines:
                    break
                popup.addstr(idx + 1, 2, wrapped_lines[line_index][:popup_w - 4])
            
            #footer del popup
            popup.addstr(popup_h-1, (popup_w - len(footer)) // 2, footer)
            
            popup.refresh()
            key = popup.getch()

            if key not in (curses.KEY_DOWN, curses.KEY_UP):
                break
            elif key == curses.KEY_DOWN and scroll_pos + popup_h - 2 < total_lines:
                scroll_pos += 1
            elif key == curses.KEY_UP and scroll_pos > 0:
                scroll_pos -= 1
