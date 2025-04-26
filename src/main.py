import curses
from curses import wrapper
import sys
from curses_ui.forensic_tools import ForensicTools
from curses_ui.ui_handler import UIHandler

def safe_main(stdscr):
    # Initialize the main window
    UIHandler(stdscr)
    ForensicTools().run()

if __name__ == "__main__":
    try:
        wrapper(safe_main)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
    except Exception as e:
        print(f"Error inesperado: {e}")