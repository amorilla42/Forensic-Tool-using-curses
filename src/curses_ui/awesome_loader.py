import time
from .renderizable import Renderizable

class CircleLoader(Renderizable):
    """
    Clase para mostrar un círculo de carga en la pantalla.
    """
    def render(self):
        self.win.addstr(0, 0, f"Cargando...")
        self.win.refresh()


