import curses
import os

def file_browser(win, start_path, wanted_ext=".E01", title=" Selecciona el archivo .E01 "):
    """
    Navegador sencillo en curses.
    - Mueve con ↑/↓
    - ENTER: entrar en dir / seleccionar archivo
    - '.' y '..' para permanecer/subir
    - ESC o 'q' para cancelar (devuelve None)
    - Muestra solo archivos con la extensión wanted_ext (case-insensitive)
    """
    def list_entries(path):
        try:
            entries = os.listdir(path)
        except Exception:
            entries = []
        dirs = []
        files = []
        ext = (wanted_ext or "").lower()
        for e in entries:
            full = os.path.join(path, e)
            if os.path.isdir(full):
                dirs.append(e + "/")
            elif not ext or e.lower().endswith(ext.lower()):
                files.append(e)
        # Orden alfabético: dirs primero
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        return ["./", "../"] + dirs + files

    def clamp(n, lo, hi):
        return max(lo, min(n, hi))

    cur_path = os.path.abspath(start_path or os.getcwd())
    cursor = 0
    scroll = 0

    win.keypad(True)
    curses.curs_set(0)

    while True:
        win.erase()
        max_y, max_x = win.getmaxyx()

        # Marco / header / footer
        try:
            win.box()
        except Exception:
            pass

        header = title
        footer = "↑/↓ mover  ENTER abrir/seleccionar   ESC cancelar"
        path_line = f"Ruta: {cur_path}"

        # Pintar header centrado
        if header:
            win.addstr(0, max(1, (max_x - len(header)) // 2), header[:max_x-2])
        # Pintar ruta actual en la línea 1 (dentro del box)
        win.addstr(1, 2, path_line[:max_x-4])

        # Área de lista
        list_top = 2  # ya ocupamos línea 0 (box) y 1 (ruta)
        list_bottom = max_y - 2  # dejamos última para footer
        visible_h = max(1, list_bottom - list_top)

        items = list_entries(cur_path)
        if not items:
            items = ["./", "../"]

        cursor = clamp(cursor, 0, len(items)-1)
        # Ajustar scroll para que el cursor quede visible
        if cursor < scroll:
            scroll = cursor
        elif cursor >= scroll + visible_h:
            scroll = cursor - visible_h + 1
        scroll = clamp(scroll, 0, max(0, len(items) - visible_h))

        # Pintar items visibles
        for i in range(visible_h):
            idx = scroll + i
            if idx >= len(items):
                break
            name = items[idx]
            line = list_top + i
            # Resaltar la fila seleccionada
            if idx == cursor:
                win.attron(curses.A_REVERSE)
                win.addnstr(line, 2, name, max_x-4)
                win.attroff(curses.A_REVERSE)
            else:
                win.addnstr(line, 2, name, max_x-4)

        # Footer
        win.addstr(max_y-1, max(1, (max_x - len(footer)) // 2), footer[:max_x-2])

        win.refresh()
        ch = win.getch()

        if ch in (curses.KEY_UP, ord('k')):
            cursor = clamp(cursor - 1, 0, len(items)-1)
        elif ch in (curses.KEY_DOWN, ord('j')):
            cursor = clamp(cursor + 1, 0, len(items)-1)
        elif ch in (curses.KEY_NPAGE,):  # PageDown
            cursor = clamp(cursor + visible_h, 0, len(items)-1)
        elif ch in (curses.KEY_PPAGE,):  # PageUp
            cursor = clamp(cursor - visible_h, 0, len(items)-1)
        elif ch in (curses.KEY_HOME,):
            cursor = 0
        elif ch in (curses.KEY_END,):
            cursor = len(items)-1
        elif ch in (27, ord('q')):  # ESC o q => cancelar
            return None
        elif ch in (curses.KEY_ENTER, 10, 13):
            selected = items[cursor]
            if selected == "./":
                # refrescar (no cambia path)
                continue
            elif selected == "../":
                parent = os.path.dirname(cur_path.rstrip(os.sep))
                if not parent:
                    parent = os.sep
                if os.path.isdir(parent):
                    cur_path = parent or os.sep
                    cursor = 0
                    scroll = 0
                continue
            else:
                sel_path = os.path.join(cur_path, selected)
                if selected.endswith("/"):
                    # Directorio
                    new_dir = sel_path.rstrip(os.sep)
                    if os.path.isdir(new_dir):
                        cur_path = new_dir
                        cursor = 0
                        scroll = 0
                    continue
                else:
                    # Archivo (ya filtrado por extensión si aplica)
                    return os.path.abspath(sel_path)
        else:
            # Ignorar otras teclas
            pass