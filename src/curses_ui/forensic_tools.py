import curses
import os
import sqlite3
from curses_ui.file_browser import FileBrowser

from curses_ui.awesome_menu import AwesomeMenu
from curses_ui.awesome_input import AwesomeInput
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_loader import CircleLoader

from curses_ui.ui_handler import UIHandler
from forensic_core.search_files import search_files
from forensic_core.e01_reader import digestE01
from utils.create_and_load_cases import CASES_DIR, crear_directorio_caso, guardar_metadata, cargar_metadata
from database.create_database import crear_base_de_datos


class ForensicTools:
    def __init__(self):
        self.ui = UIHandler()
        self.nombre_caso = None
        self.db_path = None
        self.caso_dir = None
        self.e01_path = None

    def new_case(self):
        layout = AwesomeLayout()
        layout.render()
        layout.change_header("Introduce el nombre del caso")
        layout.change_footer("Presiona ESC para salir")

        
        self.nombre_caso = AwesomeInput(layout.body_win).render()

        layout.change_header("Introduce la ruta al archivo .E01")
        layout.change_footer("Presiona ESC para salir")

        self.e01_path = AwesomeInput(layout.body_win).render()
        self.e01_path = "/home/desmo/Escritorio/TFG/Forensic-Tool-using-curses/alternateUniverse/portatil.E01"
        self.caso_dir = crear_directorio_caso(self.nombre_caso)

        self.db_path = os.path.join(self.caso_dir, f"{self.nombre_caso}.db")
        crear_base_de_datos(self.db_path)

        # mostrar que esta cargando
        x = CircleLoader(layout.body_win)
        x.render()
        
        try:
            digestE01(self.e01_path, self.ui.stdscr, self.db_path, self.nombre_caso)
            x.clear()
        except Exception as e:
            self.ui.stdscr.addstr(5, 0, f"Error al montar la imagen: {e}")
            self.ui.stdscr.refresh()
            self.ui.stdscr.getch()

    def open_case(self):
        caso_seleccionado = self.seleccionar_caso_existente()
        if caso_seleccionado is None:
            return
        self.caso_dir = os.path.join(CASES_DIR, caso_seleccionado)
        self.db_path = os.path.join(self.caso_dir, f"{caso_seleccionado}.db")
        self.nombre_caso = caso_seleccionado
        
        #cargar base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT e01_path FROM case_info WHERE case_name = ?", (self.nombre_caso,))
        self.e01_path = cursor.fetchone()[0]
        conn.close()


        

    def seleccionar_caso_existente(self):
        cases = [f for f in os.listdir(CASES_DIR) if os.path.isdir(os.path.join(CASES_DIR, f))]
        if not cases:
            self.ui.stdscr.addstr(0, 0, "No hay casos disponibles.")
            self.ui.stdscr.refresh()
            self.ui.stdscr.getch()
            return None

        cases = sorted(cases)
        menu = AwesomeMenu(title="Seleccione una opcion", options=cases)
        selected_option = menu.render()
        return cases[selected_option]


    def run(self):
        selected_option = AwesomeMenu(
            title="Seleccione una opcion",
            options=["1. Crear nuevo caso", "2. Abrir caso existente"]
        ).render()

        if selected_option == 0:
            self.new_case()
        elif selected_option == 1:
            self.open_case()

        while True:
            self.ui.draw_header("ANALIZADOR FORENSE E01")
            self.ui.draw_footer("F1: Ayuda | F2: Cargar imagen | F3: Analizar | F5: Buscar | F6: Exportar | ESC: Salir")       

            key = self.ui.stdscr.getch()
            if key == 27: # Escape key
                break
            elif key == curses.KEY_UP:
                self.ui.stdscr.addstr(0, 0, "ssisisisisi")
                self.ui.stdscr.refresh()
                self.ui.stdscr.getch()
            elif key == curses.KEY_F2:
                self.load_image()
            elif key == curses.KEY_F3:
                self.analyze_image()
            elif key == curses.KEY_F5:
                search_files(self.db_path)
            elif key == curses.KEY_F6:
                self.export_image()
            else:
                self.ui.stdscr.addstr(0, 0, "Tecla no válida. Presiona ESC para salir.")
                self.ui.stdscr.refresh()
                self.ui.stdscr.getch()
            self.ui.stdscr.refresh()

