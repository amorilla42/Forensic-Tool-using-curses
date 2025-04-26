import curses
from .renderizable import Renderizable

class AwesomeLayout(Renderizable):
    """
    Pantalla que tiene un encabezado, un pie de página y un cuerpo.
    """
    def __init__(self, win=None):
        super().__init__(win)
        self.header_height = 3
        self.footer_height = 3
        self.body_height = self.height - (self.header_height + self.footer_height)

    def render(self):
        """
        Renderiza la pantalla.
        """
        self.win.clear()
        self.win.refresh()

        # Crear ventana para el pie de página
        self.footer_win = self._render_footer(" ↑↓: Elegir opcion | ENTER: Seleccionar | ESC: Salir")

        # Crear ventana para el cuerpo
        self.body_win = curses.newwin(self.body_height, self.width, self.header_height, 0)
        self.body_win.refresh()

        # Crear ventana para el encabezado
        self.header_win = self._render_header("Forensic Tool")

    def change_header(self, title):
        """
        Cambia el encabezado de la pantalla.
        """
        self.header_win.clear()
        self.header_win.bkgd(' ', curses.color_pair(1))
        self.header_win.addstr(1, 2, title, curses.A_BOLD)
        self.header_win.refresh()

    def change_footer(self, text):
        """
        Cambia el pie de página de la pantalla.
        """
        self.footer_win.clear()
        self.footer_win.bkgd(' ', curses.color_pair(1))
        self.footer_win.addstr(1, 2, text)
        self.footer_win.refresh()

    def _render_header(self, title, subtitle=""):
        """Dibujar cabecera"""
        height, width = self.win.getmaxyx()
        header = curses.newwin(3, width, 0, 0)
        header.bkgd(' ', curses.color_pair(1))
        header.addstr(1, 2, title, curses.A_BOLD)
        if subtitle:
            header.addstr(1, width - len(subtitle) - 4, f"[{subtitle}]", curses.A_BOLD)
        header.refresh()
        return header

    def _render_footer(self, help_text="", message="", is_error=False):
        height, width = self.win.getmaxyx()
        footer = curses.newwin(3, width, height - 3, 0)
        color = curses.color_pair(3) if is_error else curses.color_pair(4)
        footer.bkgd(' ', curses.color_pair(1))
        footer.addstr(1, 2, help_text)
        if message:
            footer.addstr(2, 2, message, color)
        footer.refresh()
        return footer
