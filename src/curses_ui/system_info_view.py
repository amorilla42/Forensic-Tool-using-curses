import curses
from .renderizable import Renderizable
from utils.text_sanitizer import TextSanitizer

class SystemInfoViewer(Renderizable):
    def __init__(self, system_info: dict, win=None):
        super().__init__(win)
        self.system_info = system_info
        self.section_order = ["metadata", "services", "usb", "power"]
        self.active_section_idx = 0
        self.scrolls = {key: 0 for key in self.section_order}

        self.sections = {
            "metadata": list({"Last Boot Time": system_info.get("last_boot_time", "Desconocido")}.items()),
            "services": system_info.get("services", []),
            "usb": system_info.get("usb_devices", []),
            "power": system_info.get("power_schemes", [])
        }

        self.section_titles = {
            "metadata": " Información del Sistema (1) ",
            "services": " Servicios (2) ",
            "usb": " Dispositivos USB (3) ",
            "power": " Esquemas de Energía (4) "
        }

    def render(self):
        curses.curs_set(0)
        self.win.keypad(True)
        self._draw()

        while True:
            key = self.win.getch()
            redraw = False

            if key == 9:  # Tab
                self.active_section_idx = (self.active_section_idx + 1) % len(self.section_order)
                redraw = True
            elif key in [ord("1"), ord("2"), ord("3"), ord("4")]:
                self.active_section_idx = int(chr(key)) - 1
                redraw = True
            elif key == 27:  # ESC
                break
            elif key == curses.KEY_DOWN:
                section = self.section_order[self.active_section_idx]
                if self.scrolls[section] < len(self.sections[section]) - 1:
                    self.scrolls[section] += 1
                    redraw = True
            elif key == curses.KEY_UP:
                section = self.section_order[self.active_section_idx]
                if self.scrolls[section] > 0:
                    self.scrolls[section] -= 1
                    redraw = True

            if redraw:
                self._draw()

    def _draw(self):
        h, w = self.height, self.width
        section = self.section_order[self.active_section_idx]
        data = self.sections[section]
        scroll = self.scrolls[section]

        box = curses.newwin(h, w, 3, 0)
        box.box()
        box.addstr(0, 2, self.section_titles[section][:w-4])
        content_win = box.derwin(h - 2, w - 2, 1, 1)
        content_win.erase()

        visible = data[scroll:scroll + h - 2]
        for i, item in enumerate(visible):
            try:
                if isinstance(item, tuple):
                    line = f"{item[0]}: {item[1]}"
                elif isinstance(item, (list, tuple)):
                    line = " | ".join(map(str, item))
                else:
                    line = str(item)
                content_win.addstr(i, 0, TextSanitizer.clean(line[:w - 3]))
            except curses.error:
                pass

        # Evita parpadeo: sólo sobreescribe sin borrar la pantalla base
        box.overwrite(self.win)
        self.win.refresh()



    def clear(self):
        self.win.clear()
        self.win.refresh()
