"""
import curses
from .renderizable import Renderizable

class AwesomeInput(Renderizable):
    def render(self):
        input_win = curses.newwin(1, self.width // 2, self.height // 2, (self.width // 4))
        input_win.bkgd(' ', curses.color_pair(2))
        input_win.refresh()

        curses.echo()
        user_input = input_win.getstr(0, 0).decode("utf-8")
        curses.noecho()
        input_win.bkgd(' ', curses.color_pair(0))
        input_win.clear()
        input_win.refresh()

        return user_input
"""


import curses
from curses import textpad
from .renderizable import Renderizable

class AwesomeInput(Renderizable):
    def __init__(self, win, prompt=" Escribe aquí ", footer=" ENTER: aceptar  •  ESC: cancelar ",
                 width_hint=48, default_text=""):
        super().__init__(win)
        self.prompt = prompt
        self.footer = footer
        self.width_hint = width_hint
        self.default_text = default_text

    def _ensure_colors(self):
        # Asegura un color azul de fondo para el input (par 21 para evitar choques)
        if not curses.has_colors():
            return 0
        curses.start_color()
        try:
            curses.init_pair(21, curses.COLOR_WHITE, curses.COLOR_BLUE)  # texto blanco, fondo azul
        except curses.error:
            pass
        return curses.color_pair(21)

    def render(self):
        color_blue_bg = self._ensure_colors()

        # Dimensiones de la caja
        box_w = min(max(self.width_hint, len(self.prompt) + 6), max(30, self.width - 6))
        box_h = 5  # header, input, sep, footer
        start_y = max(1, (self.height - box_h) // 2)
        start_x = max(2, (self.width - box_w) // 2)

        # Ventana contenedora con borde
        box_win = curses.newwin(box_h, box_w, start_y, start_x)
        box_win.keypad(True)
        box_win.box()

        # Título centrado en el borde superior
        try:
            box_win.addnstr(0, max(1, (box_w - len(self.prompt)) // 2), self.prompt, box_w - 2, curses.A_BOLD)
        except curses.error:
            pass

        # Footer centrado
        try:
            box_win.addnstr(box_h - 1, max(1, (box_w - len(self.footer)) // 2), self.footer, box_w - 2, curses.A_DIM)
        except curses.error:
            pass

        # Área de entrada (1 línea), con fondo azul
        input_w = box_w - 4
        input_y = 2  # fila interior para el input
        input_x = 2
        input_win = box_win.derwin(1, input_w, input_y, input_x)
        if color_blue_bg:
            input_win.bkgd(' ', color_blue_bg)
        input_win.erase()

        # Texto por defecto (si lo hay)
        if self.default_text:
            try:
                input_win.addnstr(0, 0, self.default_text, input_w - 1)
            except curses.error:
                pass

        # Textbox con edición básica
        tb = textpad.Textbox(input_win, insert_mode=True)

        curses.curs_set(1)
        box_win.refresh()
        input_win.refresh()

        # Validator para terminar con ENTER, cancelar con ESC
        def validator(ch):
            if ch in (10, 13):        # ENTER
                return 7              # mapear a Ctrl-G (termina Textbox)
            if ch == 27:              # ESC
                # Señalamos cancelación levantando excepción que capturamos fuera
                raise KeyboardInterrupt
            return ch

        try:
            text = tb.edit(validator)
            result = text.strip()
        except KeyboardInterrupt:
            result = None
        finally:
            curses.curs_set(0)
            # limpiar la caja antes de salir
            try:
                box_win.clear()
                box_win.refresh()
            except curses.error:
                pass

        return result
