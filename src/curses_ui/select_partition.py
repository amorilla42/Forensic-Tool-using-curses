import curses

#from curses_ui.main_window import main_window
"""
def select_partition(stdscr, partitions):
    curses.curs_set(0)
    current_row = 0
    height, width = stdscr.getmaxyx()
    # Crear ventana con bordes
    win_partitions = curses.newwin(30, width - 3, 2, 2)
    win_partitions.bkgd(' ', curses.color_pair(1))
    win_partitions.box()
    win_partitions.refresh()
    
    
    while True:
        win_partitions.clear()
        

        #main_window.draw_header_custom(stdscr, "Selecciona una partición")
        #main_window.draw_footer_custom(stdscr, "↑↓: Elegir opción | ENTER: Seleccionar | ESC: Salir")

        # Dibujar las opciones
        for idx, partition in enumerate(partitions):
            x = (width - len(partition)) // 2
            y = height // 2 - len(partitions) // 2 + idx
            
            if idx == current_row:
                win_partitions.addstr(y, x, partition, curses.A_REVERSE)
            else:
                win_partitions.addstr(y, x, partition)
        
        win_partitions.refresh()
        
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(partitions) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            win_partitions.clear()
            win_partitions.refresh()
            return current_row
        elif key == 27:  # ESC
            return None
"""        


def select_partition(stdscr, partitions):
    curses.curs_set(0)  # Ocultar cursor
    current_row = 0
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    stdscr.refresh()
    
    # Calcular el ancho necesario (máximo entre el ancho del texto más largo y el mínimo deseado)
    max_part_width = max(len(p) for p in partitions) if partitions else 20
    box_width = min(max(max_part_width + 4, 40), width - 4)  # Ancho entre 40 y ancho terminal-4
    
    # Calcular altura necesaria
    box_height = min(len(partitions) + 4, height - 4)  # N° particiones + bordes + título
    
    # Posición centrada del recuadro
    start_y = max(1, (height - box_height) // 2)
    start_x = max(1, (width - box_width) // 2)
    
    # Crear ventana
    win = curses.newwin(box_height, box_width, start_y, start_x)
    win.bkgd(' ', curses.color_pair(1))
    win.box()
    
    # Título centrado
    title = "Seleccione partición:"
    try:
        win.addstr(0, (box_width - len(title)) // 2, title)
    except curses.error:
        pass
    
    # Margen izquierdo fijo para el texto
    text_margin = 2
    
    while True:
        win.clear()
        win.box()  # Redibujar bordes
        
        # Dibujar cada partición alineada a la izquierda
        for idx, part in enumerate(partitions):
            y = idx + 2  # 2 para dejar espacio para el borde y título
            if y >= box_height - 1:  # No sobrepasar el borde inferior
                break
                
            try:
                if idx == current_row:
                    win.addstr(y, text_margin, part.ljust(box_width - text_margin - 1), curses.A_REVERSE)
                else:
                    win.addstr(y, text_margin, part.ljust(box_width - text_margin - 1))
            except curses.error:
                continue
        
        # Instrucciones al pie
        instructions = "↑/↓: Navegar | Enter: Seleccionar | ESC: Salir"
        try:
            win.addstr(box_height-1, (box_width - len(instructions)) // 2, instructions)
        except curses.error:
            pass
        
        win.refresh()
        
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(partitions) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            return current_row
        elif key == 27:  # ESC
            return None