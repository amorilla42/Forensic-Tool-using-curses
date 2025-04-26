import curses
from .renderizable import Renderizable

KEY_SCAPE = 27

class AwesomeMenu(Renderizable):

    def __init__(self, title, options, win=None):
        super().__init__(win)
        self.title = title
        self.options = options
        self.selected_option = 0

    def render(self):
        current_row = 0
        self.win.clear()
        self.win.refresh()
        
        MENU_INSTRUCTIONS = "↑/↓: Navegar | Enter: Seleccionar | ESC: Salir"

        # Calcular el ancho necesario (máximo entre el ancho del texto más largo y el mínimo deseado)
        max_option_width = max(len(p) for p in self.options) if self.options else 20
        max_option_width = max(max_option_width, len(MENU_INSTRUCTIONS) + 4 )  # Ancho entre 40 y ancho terminal-4
        box_width = min(max(max_option_width + 4, 40), self.width - 4)  # Ancho entre 40 y ancho terminal-4

        # Calcular altura necesaria
        box_height = min(len(self.options) + 4, self.height - 4)  # N° particiones + bordes + título

        # Posición centrada del recuadro
        start_y = max(1, (self.height - box_height) // 2)
        start_x = max(1, (self.width - box_width) // 2)

        # Crear ventana
        menu_win = curses.newwin(box_height, box_width, start_y, start_x)
        menu_win.bkgd(' ', curses.color_pair(1))
        menu_win.box()


        # Margen izquierdo fijo para el texto
        TEXT_MARGIN = 2
        
        while True:
            menu_win.clear()
            menu_win.box()  # Redibujar bordes

            # Título centrado
            menu_win.addstr(0, (box_width - len(self.title)) // 2, self.title)

            # Dibujar cada partición alineada a la izquierda
            for idx, part in enumerate(self.options):
                y = idx + 2  # 2 para dejar espacio para el borde y título
                if y >= box_height - 1:  # No sobrepasar el borde inferior
                    break
                    
                try:
                    if idx == current_row:
                        menu_win.addstr(y, TEXT_MARGIN, part.ljust(box_width - TEXT_MARGIN - 1), curses.A_REVERSE)
                    else:
                        menu_win.addstr(y, TEXT_MARGIN, part.ljust(box_width - TEXT_MARGIN - 1))
                except curses.error:
                    continue
            
            # Instrucciones al pie
            
            try:
                menu_win.addstr(box_height-1, (box_width - len(MENU_INSTRUCTIONS)) // 2, MENU_INSTRUCTIONS)
            except curses.error:
                pass
            
            menu_win.refresh()
            
            key = self.win.getch()
            
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(self.options) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                menu_win.clear()
                menu_win.refresh()
                self.win.clear()
                self.win.refresh()
                return current_row
            elif key == KEY_SCAPE:
                menu_win.clear()
                menu_win.refresh()
                self.win.clear()
                self.win.refresh()
                return None
