# main.py
import os
import json
import hashlib
import curses


"""
CASES_DIR = "cases"

def calcular_sha256(path):
    hash_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def crear_directorio_caso(nombre):
    base_dir = os.path.join(CASES_DIR, nombre)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def guardar_metadata(caso_dir, nombre, e01_path, partition_number, offset):
    metadata = {
        "case_name": nombre,
        "e01_path": e01_path,
        "partition_number": partition_number,
        "partition_offset": offset,
        "sha256": calcular_sha256(e01_path)
    }
    with open(os.path.join(caso_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

def cargar_metadata(caso_dir):
    metadata_path = os.path.join(caso_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError("No se encontró metadata.json en el directorio del caso.")
    with open(metadata_path, "r") as f:
        return json.load(f)

def seleccionar_opcion_menu(stdscr):
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    menu = ["1. Crear nuevo caso", "2. Abrir caso existente"]
    current_row = 0

    while True:
        stdscr.clear()
        for i, row in enumerate(menu):
            if i == current_row:
                stdscr.addstr(i, 0, row, curses.A_REVERSE)
            else:
                stdscr.addstr(i, 0, row)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_DOWN:
            current_row = (current_row + 1) % len(menu)
        elif key == curses.KEY_UP:
            current_row = (current_row - 1) % len(menu)
        elif key == 10:  # Enter key
            return current_row + 1

def seleccionar_caso_existente(stdscr):
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

def main(stdscr):
    stdscr.clear()

    # Menú de selección
    opcion = seleccionar_opcion_menu(stdscr)

    if opcion == 1:  # Crear nuevo caso
        stdscr.clear()
        stdscr.addstr(0, 0, "Nombre del caso: ")
        curses.echo()
        nombre = stdscr.getstr(1, 0).decode("utf-8")
        stdscr.addstr(2, 0, "Ruta al archivo .E01: ")
        e01_path = stdscr.getstr(3, 0).decode("utf-8").strip()
        caso_dir = crear_directorio_caso(nombre)

        try:
            fs, partition_number, offset = choose_partition_and_offset(e01_path)
            guardar_metadata(caso_dir, nombre, e01_path, partition_number, offset)
        except Exception as e:
            stdscr.addstr(5, 0, f"Error al montar la imagen: {e}")
            stdscr.refresh()
            stdscr.getch()
            return

    elif opcion == 2:  # Abrir caso existente
        caso_seleccionado = seleccionar_caso_existente(stdscr)
        if caso_seleccionado is None:
            return

        caso_dir = os.path.join(CASES_DIR, caso_seleccionado)
        try:
            metadata = cargar_metadata(caso_dir)
            fs = open_e01_with_offset(metadata["e01_path"], metadata["partition_offset"])
        except Exception as e:
            stdscr.addstr(5, 0, f"Error al abrir el caso: {e}")
            stdscr.refresh()
            stdscr.getch()
            return

    curses.wrapper(run_main_window, fs)

if __name__ == "__main__":
    curses.wrapper(main)

"""



import curses
from curses import wrapper
import sys
from curses_ui.main_window import main_window

def safe_main(stdscr):
    # Initialize the main window
    app = main_window(stdscr)
    app.run()

if __name__ == "__main__":
    try:
        wrapper(safe_main)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
    except Exception as e:
        print(f"Error inesperado: {e}")
