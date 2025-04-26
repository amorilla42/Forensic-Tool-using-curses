import curses
from utils.singleton import Singleton

KEY_ENTER = 10

class UIHandler(metaclass=Singleton):
    """Clase con la lógica de la Interfaz Gráfica"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._init_ui()
    
    def _init_ui(self):
        curses.curs_set(0) # Ocultar cursor
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)

        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Body
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
            curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success

        self.stdscr.clear()
        self.stdscr.refresh()

    def draw_header(self, title, subtitle=""):
        """Dibujar cabecera"""
        height, width = self.stdscr.getmaxyx()
        header = curses.newwin(3, width, 0, 0)
        header.bkgd(' ', curses.color_pair(1))
        header.addstr(1, 2, title, curses.A_BOLD)
        if subtitle:
            header.addstr(1, width - len(subtitle) - 4, f"[{subtitle}]", curses.A_BOLD)
        header.refresh()

    def draw_footer(self, help_text="", message="", is_error=False):
        height, width = self.stdscr.getmaxyx()
        footer = curses.newwin(3, width, height - 3, 0)
        color = curses.color_pair(3) if is_error else curses.color_pair(4)
        footer.bkgd(' ', curses.color_pair(1))
        footer.addstr(1, 2, help_text)
        if message:
            footer.addstr(2, 2, message, color)
        footer.refresh()

    def draw_footer_init(self, message="", is_error=False):
        self.draw_footer(" ↑↓: Elegir opcion | ENTER: Seleccionar | ESC: Salir", message, is_error)
