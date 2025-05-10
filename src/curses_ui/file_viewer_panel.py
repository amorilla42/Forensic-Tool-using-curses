import curses
from .renderizable import Renderizable
from utils.text_sanitizer import TextSanitizer

class FileViewerPanel(Renderizable):
    def __init__(self, metadata: dict, content_lines: list[str], win=None):
        super().__init__(win)
        self.metadata = metadata
        self.content_lines = content_lines
        self.active_win = "left"
        self.left_scroll = 0
        self.right_scroll_y = 0
        self.right_scroll_x = 0
        self.left_scroll_x = 0  # Desplazamiento horizontal para metadatos
        
        if metadata:
            self.metadatamaslarga = max(max(len(str(k)) for k in metadata.keys()), max(len(str(k)) for k in metadata.values())) # Longitud máxima de la clave en metadatos
        else:
            self.metadatamaslarga = 0
        
        if content_lines:
            self.lineamaslarga = max(len(TextSanitizer.clean(line)) for line in content_lines)  # Longitud máxima de la línea en contenido
        else:
            self.lineamaslarga = 0
    
    def render(self):
        curses.curs_set(0)
        self.win.keypad(True)
        self._draw()  # Dibujar inicialmente
        while True:
            key = self.win.getch()
            redraw = False

            if key == 9:  # Tab
                self.active_win = "right" if self.active_win == "left" else "left"
                redraw = True
            elif key == 27:  # Esc
                self.win.clear()
                self.win.refresh()
                break
            elif self.active_win == "left":
                if key == curses.KEY_DOWN and self.left_scroll < len(self.metadata) - 1:
                    self.left_scroll += 5
                    redraw = True
                elif key == curses.KEY_UP and self.left_scroll > 0:
                    self.left_scroll -= 5
                    redraw = True
                elif key == curses.KEY_LEFT and self.left_scroll_x > 0:  # Mover izquierda en metadatos
                    self.left_scroll_x -= 5
                    redraw = True
                elif key == curses.KEY_RIGHT and self.left_scroll_x < self.metadatamaslarga:  # Mover derecha en metadatos
                    self.left_scroll_x += 5
                    redraw = True
            elif self.active_win == "right":
                if key == curses.KEY_DOWN and self.right_scroll_y < len(self.content_lines) - 1:
                    self.right_scroll_y += 5
                    redraw = True
                elif key == curses.KEY_UP and self.right_scroll_y > 0:
                    self.right_scroll_y -= 5
                    redraw = True
                elif key == curses.KEY_LEFT and self.right_scroll_x > 0:
                    self.right_scroll_x -= 5
                    redraw = True
                elif key == curses.KEY_RIGHT and self.right_scroll_x < self.lineamaslarga:  # Mover derecha en contenido
                    self.right_scroll_x += 5
                    redraw = True

            if redraw:
                self._draw()

        return

    def _draw(self):
        h, w = self.height, self.width
        mid_x = w // 2

        box_left = curses.newwin(h, mid_x, 0, 0)
        box_right = curses.newwin(h, w - mid_x, 0, mid_x)

        box_left.box()
        box_right.box()

        box_left.addstr(0, 2, " Metadatos ")
        box_right.addstr(0, 2, " Contenido ")

        win_left = box_left.derwin(h - 2, mid_x - 2, 1, 1)
        win_right = box_right.derwin(h - 2, w - mid_x - 2, 1, 1)

        # Colocamos los bordes alrededor de la ventana activa
        if self.active_win == "right":
            box_left.attron(curses.A_BOLD)
            box_left.border()
            box_left.attroff(curses.A_BOLD)
        else:
            box_right.attron(curses.A_BOLD)
            box_right.border()
            box_right.attroff(curses.A_BOLD)

        # Mostrar metadatos con desplazamiento horizontal
        visible_metadata = list(self.metadata.items())[self.left_scroll:self.left_scroll + h - 2]
        for i, (k, v) in enumerate(visible_metadata):
            # Desplazar los metadatos si exceden el ancho
            line = f"{k}: {v}"
            visible_line = line[self.left_scroll_x:self.left_scroll_x + mid_x - 3]
            try:
                win_left.addstr(i, 0, visible_line)
            except curses.error:
                pass

        # Mostrar contenido
        visible_content = self.content_lines[self.right_scroll_y:self.right_scroll_y + h - 2]
        for i, line in enumerate(visible_content):
            visible_line = TextSanitizer.clean(line)[self.right_scroll_x:self.right_scroll_x + (w - mid_x - 2)]
            try:
                win_right.addstr(i, 0, visible_line)
            except curses.error:
                pass

        # Solo refrescar lo necesario
        box_left.refresh()
        box_right.refresh()
        win_left.refresh()
        win_right.refresh()

    def clear(self):
        self.win.clear()
        self.win.refresh()
