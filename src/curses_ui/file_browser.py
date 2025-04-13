import curses
from forensic_core.e01_reader import open_e01_with_offset


class FileBrowser:
    def __init__(self, stdscr, y, x, h, w, fs):
        self.window = stdscr.derwin(h, w, y, x)
        self.selected = 0
        self.entries = []
        self.fs = fs
        try:
            self.current_dir = self.fs.open_dir("/")
        except Exception as e:
            raise RuntimeError(f"No se pudo abrir el directorio raíz del sistema de archivos: {e}")
        self.refresh_entries()

    def refresh_entries(self):
        self.entries = [e for e in self.current_dir if e.info.name.name.decode() not in [".", ".."]] 

    def display(self):
        self.window.clear()
        for i, entry in enumerate(self.entries):
            line = entry.info.name.name.decode()
            if i == self.selected:
                self.window.addstr(i, 0, line, curses.A_REVERSE)
            else:
                self.window.addstr(i, 0, line)
        self.window.refresh()

    def handle_input(self, key):
        if key == curses.KEY_UP and self.selected > 0:
            self.selected -= 1
        elif key == curses.KEY_DOWN and self.selected < len(self.entries) - 1:
            self.selected += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            entry = self.entries[self.selected]
            if entry.info.meta and entry.info.meta.type == 2:
                self.current_dir = entry.as_directory()
                self.refresh_entries()
                self.selected = 0
        self.display()