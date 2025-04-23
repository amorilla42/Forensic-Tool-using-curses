import curses

KEY_ENTER = 10
KEY_SCAPE = 27

class UIHandler:
    """Clase con la lógica de la Interfaz Gráfica"""

    def __init__(self,stdscr):
        self.stdscr = stdscr
        self._init_ui()
    
    def _init_ui(self):
        curses.curs_set(0)
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

    def draw_menu(self, title, options=[]):
        curses.curs_set(0)  # Ocultar cursor
        current_row = 0
        height, width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.refresh()
        
        MENU_INSTRUCTIONS = "↑/↓: Navegar | Enter: Seleccionar | ESC: Salir"

        # Calcular el ancho necesario (máximo entre el ancho del texto más largo y el mínimo deseado)
        max_option_width = max(len(p) for p in options) if options else 20
        max_option_width = max(max_option_width, len(MENU_INSTRUCTIONS) + 4 )  # Ancho entre 40 y ancho terminal-4
        box_width = min(max(max_option_width + 4, 40), width - 4)  # Ancho entre 40 y ancho terminal-4
        
        # Calcular altura necesaria
        box_height = min(len(options) + 4, height - 4)  # N° particiones + bordes + título
        
        # Posición centrada del recuadro
        start_y = max(1, (height - box_height) // 2)
        start_x = max(1, (width - box_width) // 2)
        
        # Crear ventana
        win = curses.newwin(box_height, box_width, start_y, start_x)
        win.bkgd(' ', curses.color_pair(1))
        win.box()
        
        
        # Margen izquierdo fijo para el texto
        TEXT_MARGIN = 2
        
        while True:
            win.clear()
            win.box()  # Redibujar bordes

            # Título centrado
            win.addstr(0, (box_width - len(title)) // 2, title)

            # Dibujar cada partición alineada a la izquierda
            for idx, part in enumerate(options):
                y = idx + 2  # 2 para dejar espacio para el borde y título
                if y >= box_height - 1:  # No sobrepasar el borde inferior
                    break
                    
                try:
                    if idx == current_row:
                        win.addstr(y, TEXT_MARGIN, part.ljust(box_width - TEXT_MARGIN - 1), curses.A_REVERSE)
                    else:
                        win.addstr(y, TEXT_MARGIN, part.ljust(box_width - TEXT_MARGIN - 1))
                except curses.error:
                    continue
            
            # Instrucciones al pie
            
            try:
                win.addstr(box_height-1, (box_width - len(MENU_INSTRUCTIONS)) // 2, MENU_INSTRUCTIONS)
            except curses.error:
                pass
            
            win.refresh()
            
            key = self.stdscr.getch()
            
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(options) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                win.clear()
                win.refresh()
                self.stdscr.clear()
                self.stdscr.refresh()
                return current_row
            elif key == KEY_SCAPE:
                win.clear()
                win.refresh()
                self.stdscr.clear()
                self.stdscr.refresh()
                return None

    def draw_centered_input(self):
        height, width = self.stdscr.getmaxyx()
        input_win = curses.newwin(1, width // 2, height // 2, (width // 4))
        input_win.bkgd(' ', curses.color_pair(2))
        input_win.refresh()

        curses.echo()
        user_input = input_win.getstr(0, 0).decode("utf-8")
        curses.noecho()
        input_win.clear()
        input_win.refresh()

        return user_input