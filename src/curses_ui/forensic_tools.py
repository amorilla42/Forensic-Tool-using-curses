import curses
import os
import sqlite3
from curses_ui.artifact_viewer_menu import artifact_menu
from curses_ui.file_browser import FileBrowser

from curses_ui.awesome_menu import AwesomeMenu
from curses_ui.awesome_input import AwesomeInput
from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_loader import CircleLoader


from curses_ui.ui_handler import UIHandler
from forensic_core.artifacts.registry.registry_analyzer import registry_analyzer
from forensic_core.artifacts.registry.sam_hive import visualizar_usuarios
from forensic_core.artifacts.registry.usernt_data_hive import visualizar_resumen_usuarios
from forensic_core.search_files import search_files
from forensic_core.e01_reader import digestE01
from utils.create_and_load_cases import CASES_DIR, crear_directorio_caso
from database.create_database import crear_base_de_datos


class ForensicTools:
    def __init__(self):
        self.ui = UIHandler()
        self.nombre_caso = None
        self.db_path = None
        self.caso_dir = None
        self.e01_path = None

    def new_case(self):
        from curses_ui.new_case_filesystem_browser import file_browser

        layout = AwesomeLayout()
        layout.render()
        layout.change_header("Introduce el nombre del caso")
        layout.change_footer("Presiona ESC para salir")

        
        #self.nombre_caso = AwesomeInput(layout.body_win).render()

        nombre = AwesomeInput(layout.body_win, prompt=" Nombre del caso ", default_text="").render()
        
        if nombre is None:
            # Cancelado con ESC
            import sys
            sys.exit(0)
        
        self.nombre_caso = nombre

        self.caso_dir = crear_directorio_caso(self.nombre_caso)

        layout.change_header("Navega y selecciona el archivo .E01")
        layout.change_footer("↑/↓ mover  ENTER abrir/seleccionar   ESC cancelar")

        selected = file_browser(layout.body_win, start_path=self.caso_dir, wanted_ext=".E01")
        #self.e01_path = "/home/desmo/Escritorio/TFG/Forensic-Tool-using-curses/alternateUniverse/portatil.E01"
        
        if not selected:
            # Cancelado
            layout.change_header("Operación cancelada")
            layout.change_footer("Pulsa cualquier tecla para volver")
            layout.body_win.getch()
            try:
                os.rmdir(self.caso_dir)
            except OSError:
                pass
            finally:
                import sys
                sys.exit(0)  # Exit the program if no file was selected
            

        self.e01_path = selected

        self.db_path = os.path.join(self.caso_dir, f"{self.nombre_caso}.db")
        crear_base_de_datos(self.db_path)

        # mostrar que esta cargando
        x = CircleLoader(layout.body_win)
        x.render()
        
        try:
            digestE01(self.e01_path, self.ui.stdscr, self.db_path, self.nombre_caso, self.caso_dir)
            x.clear()
        except Exception as e:
            self.ui.stdscr.addstr(5, 0, f"Error al montar la imagen: {e}")
            self.ui.stdscr.refresh()
            self.ui.stdscr.getch()

    def open_case(self):
        caso_seleccionado = self.seleccionar_caso_existente()
        if caso_seleccionado is None:
            return None
        self.caso_dir = os.path.join(CASES_DIR, caso_seleccionado)
        self.db_path = os.path.join(self.caso_dir, f"{caso_seleccionado}.db")
        self.nombre_caso = caso_seleccionado
        
        #cargar base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT e01_path FROM case_info WHERE case_name = ?", (self.nombre_caso,))
        self.e01_path = cursor.fetchone()[0]
        conn.close()
        return 1


        

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
        if selected_option is None:
            return None
        return cases[selected_option]


    def _scrollable_text(self, stdscr, title, text):
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.keypad(True)

        lines = text.splitlines()
        off = 0
        visible = max_y - 4  # caja + footer
        while True:
            win.clear()
            win.box()
            # header
            header = f" {title} "
            win.addstr(0, max(1, (max_x - 2 - len(header)) // 2), header, curses.A_BOLD)

            # body
            for i, line in enumerate(lines[off:off+visible]):
                win.addstr(1 + i, 2, line[:max_x - 6])

            # footer
            footer = "↑/↓: desplazar  |  q/ESC: salir"
            win.addstr(max_y - 3, max(2, (max_x - 2 - len(footer)) // 2), footer)

            win.refresh()
            key = win.getch()
            if key in (ord('q'), 27):
                win.clear()
                win.refresh()
                break
            elif key == curses.KEY_UP and off > 0:
                off -= 1
            elif key == curses.KEY_DOWN and off + visible < len(lines):
                off += 1

    def _show_help(self):
        # Obtener el hash del caso desde la base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT hash_sha256 FROM case_info WHERE case_name = ?", (self.nombre_caso,))
        case_hash_sha256 = cursor.fetchone()
        case_hash_md5 = cursor.execute("SELECT hash_md5 FROM case_info WHERE case_name = ?", (self.nombre_caso,)).fetchone()
        conn.close()

        case_hash_sha256 = case_hash_sha256[0] if case_hash_sha256 else "—"
        case_hash_md5 = case_hash_md5[0] if case_hash_md5 else "—"
        # Construye ayuda dinámica con datos del caso
        nombre = self.nombre_caso or "—"
        caso_dir = self.caso_dir or "—"
        db_path = self.db_path or "—"
        e01 = self.e01_path or "—"

        help_text = f"""    MENU PRINCIPAL
    F1  Ayuda                   (muestra esta ventana)
    F2  Usuarios                (información de usuarios extraídos del SAM y descifrado de contraseñas)
    F3  Visualizar Registros    (registros del sistema, eventos, etc.)
    F5  Buscar                  (archivos por nombre, tipo, etc.)
    F6  Artefactos de usuarios  (archivos interesantes clasificados por usuario, historial de busqueda de mavegador, etc.)
    ESC Salir

    FLUJO BÁSICO
    1) Crear/abrir caso
    2) Indexar imagen (.E01) si es nuevo
    3) Explorar: Usuarios / Registros / Búsqueda / Artefactos

    INFORMACION DEL CASO (actual)
    - Caso: {nombre}
    - Directorio: {caso_dir}
    - Base de datos: {db_path}
    - Imagen E01 donde se extrae la informacion: {e01}
    - Hash SHA256 de la imagen .E01: {case_hash_sha256}
    - Hash MD5 de la imagen .E01: {case_hash_md5}

    ESTRUCTURA DEL CASO
    {caso_dir}
        ├─ {os.path.basename(db_path) if db_path != "—" else "<db>"} (base de datos SQLite con todos los datos del caso)
        ├─ archivos_interesantes/   (archivos exportados de interes)
        ├─ browsers/...             (historial de navegacion por perfiles de usuario)
        ├─ temp/                    (archivos temporales de artefactos comunes para analizar)
        └─ exported_files/          (archivos exportados por el usuario de esta herramienta)

    BUENAS PRÁCTICAS FORENSES
    - No modificar la imagen .E01 original
    - Verificar SHA256 de la imagen y archivos exportados
    - Conservar hashes (p.ej., hashes.json en .eml)
    - Registrar fecha y hora de acciones
    - Documentar hallazgos y sospechas
    - Mantener un registro de cambios en el caso
    - Seguir protocolos de cadena de custodia
    - Realizar copias de seguridad periódicas
    - Mantener un entorno controlado y aislado
    """.rstrip("\n")

        self._scrollable_text(self.ui.stdscr, "AYUDA BASICA", help_text)



    def run(self):
        selected_option = AwesomeMenu(
            title="Seleccione una opcion",
            options=["1. Crear nuevo caso", "2. Abrir caso existente"]
        ).render()

        if selected_option is None:
            self.ui.stdscr.clear()
            self.ui.stdscr.refresh()
            return
        if selected_option == 0:
            self.new_case()
        elif selected_option == 1:
            caso_abierto=self.open_case()
            if caso_abierto is None:
                return

        while True:
            self.ui.draw_header("ANALIZADOR FORENSE E01")
            self.ui.draw_footer("F1: Ayuda | F2: Usuarios | F3: Visualizar Registros | F5: Buscar | F6: Artefactos | ESC: Salir")       

            key = self.ui.stdscr.getch()
            if key == 27: # Escape key
                break
            elif key == curses.KEY_UP:
                self.ui.stdscr.addstr(0, 0, "ssisisisisi")
                self.ui.stdscr.refresh()
                self.ui.stdscr.getch()
            elif key == curses.KEY_F1:
                self._show_help()
            elif key == curses.KEY_F2:
                visualizar_usuarios(self.db_path)
            elif key == ord('a'):    #####curses.KEY_F3:
                registry_analyzer(self.db_path, self.caso_dir)
            elif key == curses.KEY_F5:
                search_files(self.db_path, self.caso_dir)
            elif key == ord('c'): #####curses.KEY_F6:
                artifact_menu(self.db_path, self.caso_dir)
            else:
                self.ui.stdscr.addstr(0, 0, "Tecla no válida. Presiona ESC para salir.")
                self.ui.stdscr.refresh()
                self.ui.stdscr.getch()
            self.ui.stdscr.refresh()

