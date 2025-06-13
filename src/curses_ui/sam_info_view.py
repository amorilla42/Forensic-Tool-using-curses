import curses
import textwrap

from utils.hashcat import crack_usuario, is_hashcat_installed
from .renderizable import Renderizable

class SamInfoViewer(Renderizable):
    def __init__(self, win, user_entries):
        self.win = win
        self.users = user_entries  # Lista de dicts con username, rid, lm_hash, nt_hash
        self.selected_index = 0
        self.scroll_offset = 0

    def clear(self):
        self.win.clear()

    def render(self):
        self.clear()
        max_y, max_x = self.win.getmaxyx()
        

        visible_height = max_y - 2

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_height:
            self.scroll_offset = self.selected_index - visible_height + 1

        visible_entries = self.users[self.scroll_offset:self.scroll_offset + visible_height]

        for idx, user in enumerate(visible_entries):
            screen_idx = idx + 1
            entry_idx = self.scroll_offset + idx
            line = f"{user['username']} (RID: {user['rid']})"
            if entry_idx == self.selected_index:
                self.win.addstr(screen_idx, 3, line[:max_x - 1], curses.A_REVERSE)
            else:
                self.win.addstr(screen_idx, 3, line[:max_x - 1])

        self.win.refresh()

    def handle_input(self, key):
        total_items = len(self.users)

        if key == curses.KEY_DOWN:
            self.selected_index = min(self.selected_index + 1, total_items - 1)
        elif key == curses.KEY_UP:
            self.selected_index = max(self.selected_index - 1, 0)
        elif key == ord("c"):
            self._decrypt_password()
        elif key in [10, 13]:  # ENTER
            self._view_selected_user()

    def _decrypt_password(self):
        hashcat_installed = is_hashcat_installed()
        if not hashcat_installed:
            self._popup("Hashcat no está instalado o no se encuentra en el PATH. Por favor, instálalo para poder descifrar las contraseñas.", " Error ")
            return
        
        user = self.users[self.selected_index]
        info = f"Usuario: {user['username']}\nRID: {user['rid']}"
        pass_clear_text = crack_usuario(user)
        if pass_clear_text:
            info += f"\n→ Contraseña descifrada: \n→ NT Hash: {pass_clear_text['nt_password']}\n→ LM Hash: {pass_clear_text['lm_password']}"
        else:
            info += "\n→ No se pudo descifrar la contraseña."
        
        self._popup(info, f" Contraseña de {user['username']} ")

    def _view_selected_user(self):
        user = self.users[self.selected_index]
        info = f"Usuario: {user['username']}\nRID: {user['rid']}\nUltimo login: {user['last_login']} \nCuenta desactivada: {user['account_disabled']}\nContraseña nunca expira: {user['password_never_expires']}\nUsuario normal: {user['normal_user']}\nUsuario administrador: {user['admin_user']}\nPista de contraseña: {user['password_hint']} \nLM Hash: {user['lm_hash']}\nNT Hash: {user['nt_hash']}"

        # Detección de hash vacío o conocidos
        nt = user["nt_hash"].lower()
        lm = user["lm_hash"].lower()
        HASHES_LM_CONOCIDOS = {
            "aad3b435b51404eeaad3b435b51404ee": "(hash LM desactivado)",
            "44efce164ab921ca01fdc9a6aa77f593": "ADMIN",
            "e52cac67419a9a224a3b108f3fa6cb6d": "PASSWORD",
            "cfbf7b4c2b0b56c8aad3b435b51404ee": "GUEST",
        }

        HASHES_NT_CONOCIDOS = {
            "31d6cfe0d16ae931b73c59d7e0c089c0": "(Contraseña vacía)",
            "b0c8b778ab5e82ada9fff2bd0429b92a": "Password1",
            "6810c0cc6d36093c28f51bbe4f95e6dd": "support",
            "8846f7eaee8fb117ad06bdd830b7586c": "password",
            "a9d1cbf71942327e98b40cf5ef38a960": "admin",
            "25d55ad283aa400af464c76d713c07ad": "12345678",
            "0cb6948805f797bf2a82807973b89537": "1234",
        }

        if nt in HASHES_NT_CONOCIDOS:
            info += f"\n→ Contraseña detectada: {HASHES_NT_CONOCIDOS[nt]}"
        if lm in HASHES_LM_CONOCIDOS:
            info += f"\n→ LM hash conocido: {HASHES_LM_CONOCIDOS[lm]}"


        self._popup(info, f" Detalles de {user['username']} ")

    def _popup(self, text, title=" Detalles ", footer=" Presiona cualquier tecla para continuar "):
        max_y, max_x = self.win.getmaxyx()
        popup_h = min(15, max_y - 4)
        popup_w = min(80, max_x - 4)
        popup_y = (max_y - popup_h) // 2
        popup_x = (max_x - popup_w) // 2

        wrapped_lines = []
        for line in text.split("\n"):
            wrapped_lines.extend(textwrap.wrap(line, width=popup_w - 4) or [""])

        popup = curses.newwin(popup_h, popup_w, popup_y, popup_x)
        popup.box()
        popup.keypad(True)

        for i, line in enumerate(wrapped_lines[:popup_h - 2]):
            popup.addstr(i + 1, 2, line[:popup_w - 4])

        popup.addstr(0, (popup_w - len(title)) // 2, title)
        popup.addstr(popup_h - 1, (popup_w - len(footer)) // 2, footer)
        popup.refresh()
        popup.getch()
