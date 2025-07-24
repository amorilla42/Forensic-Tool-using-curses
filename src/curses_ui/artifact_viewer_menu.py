from curses_ui.awesome_layout import AwesomeLayout
from curses_ui.awesome_menu2 import AwesomeMenu
from curses_ui.interesting_files_viewer import visualizar_archivos_interesantes
from forensic_core.artifacts.registry.usernt_data_hive import visualizar_resumen_usuarios




def artifact_menu(db_path, caso_dir):

    layout = AwesomeLayout()
    while True:
        layout.render()
        layout.change_header("Analizador de Artefactos del Sistema")
        layout.change_footer("Presiona ESC para salir")

        menu = AwesomeMenu(title="Seleccione accion", options=["Archivos interesantes","Artefactos de usuarios"], win=layout.body_win)
        selected_option = menu.render()
        if selected_option is None:
            layout.body_win.clear()
            layout.body_win.refresh()
            break
       
        if selected_option == 0:
            visualizar_archivos_interesantes(db_path, caso_dir)

        elif selected_option == 1:
            visualizar_resumen_usuarios(db_path, caso_dir)
