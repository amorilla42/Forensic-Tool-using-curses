import curses
from .renderizable import Renderizable

KEY_SCAPE = 27

class AwesomeMenu(Renderizable):

    def __init__(self, title, options, win=None):
        super().__init__(win)
        self.title = title
        self.options = options
        self.selected_option = 0
        self.scroll_offset = 0  # ← Añadido para scroll

    def render(self):
        curses.curs_set(0)  # Ocultar cursor
        MENU_INSTRUCTIONS = "↑/↓: Navegar | Enter: Seleccionar | ESC: Salir"

        max_option_width = max(len(p) for p in self.options) if self.options else 20
        max_option_width = max(max_option_width, len(MENU_INSTRUCTIONS) + 4)
        box_width = min(max(max_option_width + 4, 40), self.width - 4)

        box_height = min(self.height - 4, len(self.options) + 4)
        visible_rows = box_height - 3  # -1 header, -1 footer, -1 separador

        start_y = max(1, (self.height - box_height) // 2)
        start_x = max(1, (self.width - box_width) // 2)

        menu_win = curses.newwin(box_height, box_width, start_y + 3, start_x)
        menu_win.bkgd(' ', curses.color_pair(1))
        TEXT_MARGIN = 2

        while True:
            menu_win.erase()
            menu_win.box()

            try:
                menu_win.addstr(0, (box_width - len(self.title)) // 2, self.title)
            except curses.error:
                pass

            # Ajustar scroll si el seleccionado está fuera del área visible
            if self.selected_option < self.scroll_offset:
                self.scroll_offset = self.selected_option
            elif self.selected_option >= self.scroll_offset + visible_rows:
                self.scroll_offset = self.selected_option - visible_rows + 1

            # Mostrar opciones visibles
            for idx in range(self.scroll_offset, min(len(self.options), self.scroll_offset + visible_rows)):
                part = self.options[idx]
                y = idx - self.scroll_offset + 2
                max_text_width = box_width - TEXT_MARGIN - 2
                part_display = ("…" + part[-(max_text_width - 1):]) if len(part) > max_text_width else part

                try:
                    if idx == self.selected_option:
                        menu_win.addstr(y, TEXT_MARGIN, part_display.ljust(max_text_width), curses.A_REVERSE)
                    else:
                        menu_win.addstr(y, TEXT_MARGIN, part_display.ljust(max_text_width))
                except curses.error:
                    continue

            # Indicadores de scroll
            if self.scroll_offset > 0:
                try:
                    menu_win.addstr(1, box_width - 3, "▲")
                except curses.error:
                    pass
            if self.scroll_offset + visible_rows < len(self.options):
                try:
                    menu_win.addstr(box_height - 2, box_width - 3, "▼")
                except curses.error:
                    pass

            try:
                menu_win.addstr(box_height - 1, (box_width - len(MENU_INSTRUCTIONS)) // 2, MENU_INSTRUCTIONS)
            except curses.error:
                pass

            menu_win.noutrefresh()
            curses.doupdate()

            key = self.win.getch()

            if key == KEY_SCAPE:
                self.win.nodelay(True)
                next1 = self.win.getch()
                next2 = self.win.getch()
                self.win.nodelay(False)

                if next1 == -1 and next2 == -1:
                    return None
                elif next1 == 91:
                    if next2 == 65: key = curses.KEY_UP
                    elif next2 == 66: key = curses.KEY_DOWN

            if key == curses.KEY_UP and self.selected_option > 0:
                self.selected_option -= 1
            elif key == curses.KEY_DOWN and self.selected_option < len(self.options) - 1:
                self.selected_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                menu_win.erase()
                menu_win.noutrefresh()
                self.win.erase()
                self.win.noutrefresh()
                curses.doupdate()
                return self.selected_option
