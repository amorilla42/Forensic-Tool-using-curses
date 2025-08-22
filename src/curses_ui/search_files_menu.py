import curses
from .renderizable import Renderizable

KEY_SCAPE = 27
MARGEN_ARRIBA = 2
MARGEN_ABAJO = 10


class SearchFilesMenu(Renderizable):

    def __init__(self, title, options, info, win=None):
        super().__init__(win)
        self.title = title
        self.options = options
        self.info = info
        self.selected_option = 0
        

    def render(self):
        current_row = 0
        curses.curs_set(0)  # Ocultar cursor

        MENU_INSTRUCTIONS = "↑/↓: Navegar | Enter: Seleccionar | ESC: Salir"

        max_option_width = max(len(p) for p in self.options) if self.options else 20
        max_option_width = max(max_option_width, len(MENU_INSTRUCTIONS) + 4)
        self.box_width = min(max(max_option_width + 4, 40), self.width - 4)

        box_height = min(len(self.options) + 4, self.height - MARGEN_ABAJO)

        start_y = max(1, (self.height - box_height) // 2)
        start_x = max(1, (self.width - self.box_width) // 2)

        menu_win = curses.newwin(box_height, self.box_width, start_y + MARGEN_ARRIBA, start_x)
        menu_win.bkgd(' ', curses.color_pair(1))
        TEXT_MARGIN = 2
        
        # Ventana para mostrar la info de cada linea de la lista
        self.info_win = curses.newwin(3, self.width-4, start_y + MARGEN_ARRIBA + box_height + 1, 2)
        self.info_win.bkgd(' ', curses.color_pair(1))
        self.print_info_row(0)

        while True:
            menu_win.erase()
            menu_win.box()

            try:
                menu_win.addstr(0, (self.box_width - len(self.title)) // 2, self.title)
            except curses.error:
                pass

            visible_rows = box_height - 3
            start_idx = max(0, current_row - visible_rows + 1)
            end_idx = min(start_idx + visible_rows, len(self.options))

            for idx in range(start_idx, end_idx):
                part = self.options[idx]

                y = idx - start_idx + 2

                max_text_width = self.box_width - TEXT_MARGIN - 2
                if len(part) > max_text_width:
                    part_display = "…" + part[-(max_text_width - 1):]
                else:
                    part_display = part

                try:
                    if idx == current_row:
                        menu_win.addstr(y, TEXT_MARGIN, part_display.ljust(max_text_width), curses.A_REVERSE)
                    else:
                        menu_win.addstr(y, TEXT_MARGIN, part_display.ljust(max_text_width))
                except curses.error:
                    continue

            if start_idx > 0:
                try:
                    menu_win.addstr(1, self.box_width - 3, "▲")
                except curses.error:
                    pass
            if end_idx < len(self.options):
                try:
                    menu_win.addstr(box_height - 2, self.box_width - 3, "▼")
                except curses.error:
                    pass

            try:
                menu_win.addstr(box_height - 1, (self.box_width - len(MENU_INSTRUCTIONS)) // 2, MENU_INSTRUCTIONS)
            except curses.error:
                pass

            menu_win.noutrefresh()
            curses.doupdate()

            key = self.win.getch()

            if key == 27:  # ESC o secuencia ANSI
                self.win.nodelay(True)
                next1 = self.win.getch()
                next2 = self.win.getch()
                self.win.nodelay(False)

                if next1 == -1 and next2 == -1:
                    return None
                elif next1 == 91:
                    if next2 == 65:
                        key = curses.KEY_UP
                    elif next2 == 66:
                        key = curses.KEY_DOWN
                    elif next2 == 67:
                        key = curses.KEY_RIGHT
                    elif next2 == 68:
                        key = curses.KEY_LEFT

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
                self.print_info_row(current_row)
            elif key == curses.KEY_DOWN and current_row < len(self.options) - 1:
                current_row += 1
                self.print_info_row(current_row)
            elif key == curses.KEY_ENTER or key in [10, 13]:
                menu_win.erase()
                menu_win.noutrefresh()
                self.win.erase()
                self.win.noutrefresh()
                curses.doupdate()
                return current_row

    def print_info_row(self, row):
        text = self.info[row]
        self.info_win.erase()
        self.info_win.box()
        self.info_win.addstr(0, (self.width - 16) // 2 , "Path del archivo")
        self.win.noutrefresh()
        curses.doupdate()
        

        max_text_width = self.width - 6
        if len(text) > max_text_width:
            part_display = "…" + text[-(max_text_width - 1):]
        else:
            part_display = text

        try:
            self.info_win.addstr(1, 1, part_display.ljust(max_text_width))
        except curses.error:
            pass
        self.info_win.noutrefresh()
        curses.doupdate()
        
