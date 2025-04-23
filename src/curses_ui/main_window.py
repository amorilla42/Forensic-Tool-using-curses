import curses
import os
from curses_ui.file_browser import FileBrowser
from forensic_core.e01_reader import digestE01
from utils.create_and_load_cases import CASES_DIR, crear_directorio_caso, guardar_metadata, cargar_metadata
from database.create_database import crear_base_de_datos


class main_window:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.reader = None
        self.selected_partition = None
        self.current_image = None
        self.init_ui()


    def init_ui(self):
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

    def draw_header(self, title=""):
        height, width = self.stdscr.getmaxyx()
        header = curses.newwin(3, width, 0, 0)
        header.bkgd(' ', curses.color_pair(1))
        header.addstr(1, 2, title or "ANALIZADOR FORENSE E01", curses.A_BOLD)
        if self.current_image:
            header.addstr(1, width - len(self.current_image) - 4, f"[{self.current_image}]", curses.A_BOLD)
        header.refresh()

    def draw_footer(self, message="", is_error=False):
        height, width = self.stdscr.getmaxyx()
        footer = curses.newwin(3, width, height - 3, 0)
        color = curses.color_pair(3) if is_error else curses.color_pair(4)
        footer.bkgd(' ', curses.color_pair(1))
        help_text = "F1: Ayuda | F2: Cargar imagen | F3: Analizar | F5: Buscar | F6: Exportar | ESC: Salir"
        footer.addstr(1, 2, help_text)
        if message:
            footer.addstr(2, 2, message, color)
        footer.refresh()

    def draw_header_init(self, title=""):
        height, width = self.stdscr.getmaxyx()
        header = curses.newwin(3, width, 0, 0)
        header.bkgd(' ', curses.color_pair(1))
        header.addstr(1, 2, title or "Seleccione una opcion", curses.A_BOLD)
        header.refresh()

    def draw_footer_init(self, message="", is_error=False):
        height, width = self.stdscr.getmaxyx()
        footer = curses.newwin(3, width, height - 3, 0)
        color = curses.color_pair(3) if is_error else curses.color_pair(4)
        footer.bkgd(' ', curses.color_pair(1))
        help_text = " ↑↓: Elegir opcion | ENTER: Seleccionar | ESC: Salir"
        footer.addstr(1, 2, help_text)
        if message:
            footer.addstr(2, 2, message, color)
        footer.refresh()

    def draw_header_custom(self, title=""):
        height, width = self.stdscr.getmaxyx()
        header = curses.newwin(3, width, 0, 0)
        header.bkgd(' ', curses.color_pair(1))
        header.addstr(1, 2, title or "Seleccione una opcion", curses.A_BOLD)
        header.refresh()
    
    def draw_footer_custom(self, text="", message="", is_error=False):
        height, width = self.stdscr.getmaxyx()
        footer = curses.newwin(3, width, height - 3, 0)
        color = curses.color_pair(3) if is_error else curses.color_pair(4)
        footer.bkgd(' ', curses.color_pair(1))
        help_text = text or " ↑↓: Elegir opcion | ENTER: Seleccionar | ESC: Salir"
        footer.addstr(1, 2, help_text)
        if message:
            footer.addstr(2, 2, message, color)
        footer.refresh()

    def init_panel(self):
        height, width = self.stdscr.getmaxyx()
        self.panel = curses.newwin(4, width // 2, (height // 2) - 2, (width // 2) - (width // 4))
        self.panel.refresh()
        menu = ["1. Crear nuevo caso", "2. Abrir caso existente"]
        current_row = 0
        
        self.stdscr.clear()
        self.stdscr.refresh()
        self.draw_header_init()
        self.draw_footer_init()
        
        while True:
            self.panel.clear()
            for i, row in enumerate(menu):
                if i == current_row:
                    self.panel.addstr(i, 0, row, curses.A_REVERSE)
                else:
                    self.panel.addstr(i, 0, row)

            self.panel.refresh()
            key = self.stdscr.getch()

            if key == curses.KEY_DOWN:
                current_row = (current_row + 1) % len(menu)
            elif key == curses.KEY_UP:
                current_row = (current_row - 1) % len(menu)
            elif key == 10:  # Enter key
                self.gestioncasos(current_row)
                self.stdscr.clear()
                self.stdscr.refresh()
                return current_row + 1
            elif key == 27:  # Escape key
                self.stdscr.clear()
                self.stdscr.refresh()
                return None

    def gestioncasos(self, option):
        if option == 0:  # Crear nuevo caso
            self.panel.clear()
            self.panel.refresh()
            self.draw_header_custom("Introduce el nombre del caso")
            self.draw_footer_custom("Presiona ESC para salir")
            
            height, width = self.stdscr.getmaxyx()
            
            input_win = curses.newwin(1, width // 2, height // 2, (width // 4))
            input_win.bkgd(' ', curses.color_pair(2))
            input_win.refresh()

            curses.echo()

            nombre_caso = input_win.getstr(0, 0).decode("utf-8")
            self.panel.clear()
            self.panel.refresh()

            self.draw_header_custom("Introduce la ruta al archivo .E01")
            self.draw_footer_custom("Presiona ESC para salir")
            
            input_win.clear()
            input_win.refresh()
            e01_path = input_win.getstr(0, 0).decode("utf-8").strip()

            curses.noecho()
            e01_path = "/home/desmo/Escritorio/TFG/Forensic-Tool-using-curses/alternateUniverse/portatil.E01"
            caso_dir = crear_directorio_caso(nombre_caso)

            db_path = os.path.join(caso_dir, f"{nombre_caso}.db")
            crear_base_de_datos(db_path)



            try:
                digestE01(e01_path,self.stdscr,db_path,nombre_caso)
                self.stdscr.addstr(5, 0, "Imagen montada y analizada correctamente.")
                self.stdscr.refresh()
                self.stdscr.getch()
            except Exception as e:
                self.stdscr.addstr(5, 0, f"Error al montar la imagen: {e}")
                self.stdscr.refresh()
                self.stdscr.getch()
                return

        elif option == 1:  # Abrir caso existente
            caso_seleccionado = self.seleccionar_caso_existente(self.stdscr)
            if caso_seleccionado is None:
                return
            caso_dir = os.path.join(CASES_DIR, caso_seleccionado)
            try:
                metadata = cargar_metadata(caso_dir)
                fs = self.open_e01_with_offset(metadata["e01_path"], metadata["partition_offset"])
            except Exception as e:
                self.stdscr.addstr(5, 0, f"Error al abrir el caso: {e}")
                self.stdscr.refresh()
                self.stdscr.getch()
                return

    def seleccionar_caso_existente(self, stdscr):
        cases = [f for f in os.listdir(CASES_DIR) if os.path.isdir(os.path.join(CASES_DIR, f))]
        if not cases:
            stdscr.addstr(0, 0, "No hay casos disponibles.")
            stdscr.refresh()
            stdscr.getch()
            return None

        cases = sorted(cases)
        selected_case = 0

        while True:
            stdscr.clear()
            for i, case in enumerate(cases):
                if i == selected_case:
                    stdscr.addstr(i, 0, case, curses.A_REVERSE)
                else:
                    stdscr.addstr(i, 0, case)

            stdscr.refresh()
            key = stdscr.getch()

            if key == curses.KEY_DOWN:
                selected_case = (selected_case + 1) % len(cases)
            elif key == curses.KEY_UP:
                selected_case = (selected_case - 1) % len(cases)
            elif key == 10:  # Enter key
                return cases[selected_case]
            elif key == 27:  # Escape key
                return None

    def run(self):
        
        self.init_panel()

        while True:
            self.draw_header()
            self.draw_footer()        

            key = self.stdscr.getch()
            if key == 27: # Escape key
                break
            elif key == curses.KEY_UP:
                self.stdscr.addstr(0, 0, "ssisisisisi")
                self.stdscr.refresh()
                self.stdscr.getch()
            elif key == curses.KEY_F2:
                self.load_image()
            elif key == curses.KEY_F3:
                self.analyze_image()
            elif key == curses.KEY_F5:
                self.search_image()
            elif key == curses.KEY_F6:
                self.export_image()
            else:
                self.stdscr.addstr(0, 0, "Tecla no válida. Presiona ESC para salir.")
                self.stdscr.refresh()
                self.stdscr.getch()
            self.stdscr.refresh()



def main(stdscr):
    window = main_window(stdscr)
    window.run()

if __name__ == "__main__":
    curses.wrapper(main)