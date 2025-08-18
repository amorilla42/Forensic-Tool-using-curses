import curses
import sqlite3
import textwrap

from .renderizable import Renderizable
from curses_ui.awesome_layout import AwesomeLayout


def _wrap(text, width):
    return textwrap.fill("" if text is None else str(text), width)

def _detail_from_row(headers, row, width, transforms=None):
    """
    Construye un detalle multi-línea con pares Cabecera: Valor.
    - headers: lista de etiquetas para cada columna.
    - row: tupla con los valores originales (sin recorte).
    - transforms: dict opcional {indice_columna: funcion_transform} para humanizar valores.
    """
    parts = []
    for idx, (hdr, val) in enumerate(zip(headers, row)):
        if transforms and idx in transforms:
            try:
                val = transforms[idx](val)
            except Exception:
                pass
        parts.append(f"{hdr}:\n{_wrap(val, width)}")
    return "\n\n".join(parts)

def _recortar(texto, ancho):
    s = "" if texto is None else str(texto).replace("\n", " ")
    return s if len(s) <= ancho else s[:ancho-1] + "…"

def _show_scrollable_popup(win, content, title=" Detalle ", footer=" ↑/↓ scroll, q/ESC salir "):
    max_y, max_x = win.getmaxyx()
    popup = curses.newwin(max_y, max_x, 3, 0)
    popup.keypad(True)
    lines = content.split("\n")
    off = 0
    visible = max_y - 2
    while True:
        popup.clear()
        popup.box()
        popup.addstr(0, max(2, (max_x - len(title)) // 2), title, curses.A_BOLD)
        for i, line in enumerate(lines[off:off+visible]):
            popup.addstr(1 + i, 2, line[:max_x-4])
        popup.addstr(max_y - 1, max(2, (max_x - len(footer)) // 2), footer, curses.A_DIM)
        popup.refresh()
        k = popup.getch()
        if k in (27, ord('q')):
            break
        elif k == curses.KEY_UP and off > 0:
            off -= 1
        elif k == curses.KEY_DOWN and off + visible < len(lines):
            off += 1


def _fetch_all(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def _human_start_type(v):
    try: v = int(v)
    except: return str(v) if v is not None else ""
    return {0:"Boot",1:"System",2:"Auto",3:"Manual",4:"Disabled"}.get(v, str(v))

def _human_service_type(v):
    # simplificado (bitmask frecuente)
    try: v = int(v)
    except: return str(v) if v is not None else ""
    if v & 0x00000001: return "Kernel Driver"
    if v & 0x00000002: return "FS Driver"
    if v & 0x00000010: return "Win32 Own Proc"
    if v & 0x00000020: return "Win32 Shared Proc"
    return str(v)

# ---------- formatters (SOFTWARE) ----------
def fmt_system_info(rows, width):
    # product_name, product_id, install_date, registered_owner, computer_name
    if not rows:
        return "Sin datos"
    w1 = int(width*0.22); w2 = int(width*0.18); w3 = int(width*0.18); w4 = int(width*0.20)
    w5 = width - (w1 + w2 + w3 + w4 + 9)
    out = []
    head = f"{'Producto':<{w1}}│ {'ProductID':<{w2}}│ {'Instalación (UTC)':<{w3}}│ {'Propietario':<{w4}}│ {'Equipo':<{w5}}"
    out.append(head); out.append("─"*len(head))
    for r in rows:
        p, pid, inst, owner, pc = r
        out.append(
            f"{_recortar(p,w1):<{w1}}│ {_recortar(pid,w2):<{w2}}│ {_recortar(inst,w3):<{w3}}│ "
            f"{_recortar(owner,w4):<{w4}}│ {_recortar(pc,w5):<{w5}}"
        )
    return "\n".join(out)

def fmt_installed_programs(rows, width):
    # name, version, publisher, install_date
    w1 = int(width*0.34); w2 = int(width*0.18); w3 = int(width*0.26)
    w4 = width - (w1 + w2 + w3 + 7)
    out = []
    head = f"{'Programa':<{w1}}│ {'Versión':<{w2}}│ {'Publisher':<{w3}}│ {'Fecha (raw)':<{w4}}"
    out.append(head); out.append("─"*len(head))
    for name, ver, pub, d in rows:
        out.append(
            f"{_recortar(name,w1):<{w1}}│ {_recortar(ver,w2):<{w2}}│ {_recortar(pub,w3):<{w3}}│ {_recortar(d,w4):<{w4}}"
        )
    return "\n".join(out)

def fmt_startup(rows, width):
    # name, command
    w1 = int(width*0.28)
    w2 = width - w1 - 3
    out = []
    head = f"{'Nombre':<{w1}}│ {'Comando':<{w2}}"
    out.append(head); out.append("─"*len(head))
    for name, cmd in rows:
        out.append(f"{_recortar(name,w1):<{w1}}│ {_recortar(cmd,w2):<{w2}}")
    return "\n".join(out)

def fmt_runonce(rows, width):
    return fmt_startup(rows, width)

def fmt_installed_components(rows, width):
    # component_id, stub_path, version, is_installed, component_name
    w1 = int(width*0.28); w2 = int(width*0.32); w3 = int(width*0.11); w4 = 7
    w5 = width - (w1 + w2 + w3 + w4 + 7)
    out = []
    head = f"{'ComponentID':<{w1}}│ {'StubPath':<{w2}}│ {'Version':<{w3}}│ {'Inst':^{w4}} │ {'Nombre':<{w5}}"
    out.append(head); out.append("─"*len(head))
    for cid, stub, ver, inst, name in rows:
        inst_s = str(inst) if inst is not None else ""
        out.append(
            f"{_recortar(cid,w1):<{w1}}│ {_recortar(stub,w2):<{w2}}│ {_recortar(ver,w3):<{w3}}│ {inst_s:^{w4}} │ {_recortar(name,w5):<{w5}}"
        )
    return "\n".join(out)

def fmt_app_paths(rows, width):
    # executable, path
    w1 = int(width*0.28)
    w2 = width - w1 - 3
    out = []
    head = f"{'Ejecutable':<{w1}}│ {'Ruta':<{w2}}"
    out.append(head); out.append("─"*len(head))
    for exe, path in rows:
        out.append(f"{_recortar(exe,w1):<{w1}}│ {_recortar(path,w2):<{w2}}")
    return "\n".join(out)

def fmt_app_paths_meta(rows, width):
    # executable, value_name, value_data, key_path, timestamp
    w1 = int(width*0.18); w2 = int(width*0.20); w3 = int(width*0.34)
    w4 = int(width*0.16); w5 = width - (w1 + w2 + w3 + w4 + 7)
    out = []
    head = f"{'Exe':<{w1}}│ {'Valor':<{w2}}│ {'Dato':<{w3}}│ {'Clave':<{w4}}│ {'Timestamp':<{w5}}"
    out.append(head); out.append("─"*len(head))
    for exe, vname, vdata, keyp, ts in rows:
        out.append(
            f"{_recortar(exe,w1):<{w1}}│ {_recortar(vname,w2):<{w2}}│ {_recortar(vdata,w3):<{w3}}│ {_recortar(keyp,w4):<{w4}}│ {_recortar(ts,w5):<{w5}}"
        )
    return "\n".join(out)

def fmt_svchost(rows, width):
    # group_name, services
    w1 = int(width*0.22)
    w2 = width - w1 - 3
    out = []
    head = f"{'Grupo':<{w1}}│ {'Servicios':<{w2}}"
    out.append(head); out.append("─"*len(head))
    for group, services in rows:
        out.append(f"{_recortar(group,w1):<{w1}}│ {_recortar(services,w2):<{w2}}")
    return "\n".join(out)

# ---------- formatters (SYSTEM) ----------
def fmt_system_lastboot(rows, width):
    # one row: last_boot_time
    w = width
    out = []
    head = f"{'Último arranque (UTC)':<{w}}"
    out.append(head); out.append("─"*len(head))
    if not rows:
        out.append("Sin datos")
    else:
        out.append(_recortar(rows[0][0], w))
    return "\n".join(out)

def fmt_system_services(rows, width):
    # service_name, display_name, image_path, start_type, service_type
    w1 = int(width*0.22); w2 = int(width*0.24); w3 = int(width*0.30)
    w4 = 8; w5 = width - (w1 + w2 + w3 + w4 + 7)
    out = []
    head = f"{'Servicio':<{w1}}│ {'Nombre':<{w2}}│ {'Imagen':<{w3}}│ {'Start':^{w4}} │ {'Tipo':<{w5}}"
    out.append(head); out.append("─"*len(head))
    for sname, dname, img, start, stype in rows:
        out.append(
            f"{_recortar(sname,w1):<{w1}}│ {_recortar(dname,w2):<{w2}}│ {_recortar(img,w3):<{w3}}│ "
            f"{_human_start_type(start):^{w4}} │ {_recortar(_human_service_type(stype),w5):<{w5}}"
        )
    return "\n".join(out)

def fmt_usb_devices(rows, width):
    # device_class, device_id, friendly_name, device_desc
    w1 = int(width*0.20); w2 = int(width*0.24); w3 = int(width*0.24)
    w4 = width - (w1 + w2 + w3 + 6)
    out = []
    head = f"{'Clase':<{w1}}│ {'ID':<{w2}}│ {'Nombre':<{w3}}│ {'Descripción':<{w4}}"
    out.append(head); out.append("─"*len(head))
    for dclass, did, fname, ddesc in rows:
        out.append(
            f"{_recortar(dclass,w1):<{w1}}│ {_recortar(did,w2):<{w2}}│ {_recortar(fname,w3):<{w3}}│ {_recortar(ddesc,w4):<{w4}}"
        )
    return "\n".join(out)

def fmt_power_schemes(rows, width):
    # scheme_name, friendly_name
    w1 = int(width*0.40)
    w2 = width - w1 - 3
    out = []
    head = f"{'Esquema':<{w1}}│ {'Nombre legible':<{w2}}"
    out.append(head); out.append("─"*len(head))
    for s, f in rows:
        out.append(f"{_recortar(s,w1):<{w1}}│ {_recortar(f,w2):<{w2}}")
    return "\n".join(out)

# ---------- main viewer ----------
class SystemArtifactsViewer(Renderizable):
    def __init__(self, win, db_path, layout):
        self.win = win
        self.db_path = db_path
        self.layout = layout
        self.options = [
            # SOFTWARE hive
            "Información del sistema",
            "Programas instalados",
            "Inicio automático (Run)",
            "RunOnce",
            "Active Setup (Installed Components)",
            "App Paths (resumen)",
            "App Paths (metadatos)",
            "Grupos de svchost",
            # SYSTEM hive
            "Último arranque",
            "Servicios",
            "Dispositivos USB",
            "Perfiles de energía"
        ]
        self.selected = 0

    def clear(self):
        self.win.clear()

    def render(self):
        self.clear()
        max_y, max_x = self.win.getmaxyx()
        self.win.addstr(0, 2, "Artefactos del sistema", curses.A_BOLD)
        self.win.addstr(1, 2, "Selecciona una categoría y pulsa ENTER", curses.A_UNDERLINE)

        for i, opt in enumerate(self.options):
            attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
            self.win.addstr(i + 3, 4, opt[:max_x - 6], attr)

        self.win.refresh()

    def handle_input(self, key):
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.options)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.options)
        elif key in (10, 13):
            self._open_section(self.selected)

    def _open_section(self, idx):
        max_y, max_x = self.win.getmaxyx()
        width = max_x - 4

        # --- SOFTWARE ---
        if idx == 0:
            rows = _fetch_all(self.db_path, "SELECT product_name, product_id, install_date, registered_owner, computer_name FROM system_info2")
            table = fmt_system_info(rows, width)
            _show_scrollable_popup(self.win, table, "SOFTWARE: Información del sistema")
            return

        elif idx == 1:
            rows = _fetch_all(self.db_path, "SELECT name, version, publisher, install_date FROM installed_programs ORDER BY name")
            self._interactive_table(
                "SOFTWARE: Programas instalados",
                rows,
                lambda r: fmt_installed_programs(r, width),
                headers=["Programa", "Versión", "Publisher", "Fecha (raw)"]
            )

        elif idx == 2:
            rows = _fetch_all(self.db_path, "SELECT name, command FROM startup_entries ORDER BY name")
            self._interactive_table(
                "SOFTWARE: Inicio automático (Run)",
                rows,
                lambda r: fmt_startup(r, width),
                headers=["Nombre", "Comando"]
            )

        elif idx == 3:
            rows = _fetch_all(self.db_path, "SELECT name, command FROM run_once_entries ORDER BY name")
            self._interactive_table(
                "SOFTWARE: RunOnce",
                rows,
                lambda r: fmt_runonce(r, width),
                headers=["Nombre", "Comando"]
            )

        elif idx == 4:
            rows = _fetch_all(self.db_path,
                "SELECT component_id, stub_path, version, is_installed, component_name FROM installed_components ORDER BY component_id")
            self._interactive_table(
                "SOFTWARE: Active Setup",
                rows,
                lambda r: fmt_installed_components(r, width),
                headers=["ComponentID", "StubPath", "Version", "IsInstalled", "Nombre"]
            )

        elif idx == 5:
            rows = _fetch_all(self.db_path, "SELECT executable, path FROM app_paths ORDER BY executable")
            self._interactive_table(
                "SOFTWARE: App Paths (resumen)",
                rows,
                lambda r: fmt_app_paths(r, width),
                headers=["Ejecutable", "Ruta"]
            )

        elif idx == 6:
            rows = _fetch_all(self.db_path,
                "SELECT executable, value_name, value_data, key_path, timestamp FROM app_paths_meta ORDER BY executable, value_name")
            self._interactive_table(
                "SOFTWARE: App Paths (metadatos)",
                rows,
                lambda r: fmt_app_paths_meta(r, width),
                headers=["Exe", "Valor", "Dato", "Clave", "Timestamp"]
            )

        elif idx == 7:
            rows = _fetch_all(self.db_path, "SELECT group_name, services FROM svchost_groups ORDER BY group_name")
            # opcional: detalle personalizado para listar cada servicio en línea aparte
            def _svchost_detail(row, w):
                grupo, servicios = row
                lst = []
                lst.append(f"Grupo:\n{_wrap(grupo, w)}")
                if servicios:
                    items = [s.strip() for s in str(servicios).split(",") if s.strip()]
                    if items:
                        lst.append("Servicios:")
                        lst.extend(f"  - {_wrap(s, w-4)}" for s in items)
                    else:
                        lst.append(f"Servicios:\n{_wrap(servicios, w)}")
                else:
                    lst.append("Servicios:\n—")
                return "\n\n".join(lst)

            self._interactive_table(
                "SOFTWARE: Grupos de svchost",
                rows,
                lambda r: fmt_svchost(r, width),
                headers=["Grupo", "Servicios"],
                custom_detail_fn=_svchost_detail
            )

        # --- SYSTEM ---
        elif idx == 8:
            rows = _fetch_all(self.db_path, "SELECT last_boot_time FROM system_info ORDER BY id DESC LIMIT 1")
            table = fmt_system_lastboot(rows, width)
            _show_scrollable_popup(self.win, table, "SYSTEM: Último arranque")
            return

        elif idx == 9:
            self._services_browser()

        elif idx == 10:
            rows = _fetch_all(self.db_path,
                "SELECT device_class, device_id, friendly_name, device_desc FROM usb_devices ORDER BY device_class, device_id")
            self._interactive_table(
                "SYSTEM: Dispositivos USB",
                rows,
                lambda r: fmt_usb_devices(r, width),
                headers=["Clase", "ID", "Nombre", "Descripción"]
            )

        elif idx == 11:
            rows = _fetch_all(self.db_path,
                "SELECT scheme_name, friendly_name FROM power_schemes ORDER BY scheme_name")
            self._interactive_table(
                "SYSTEM: Perfiles de energía",
                rows,
                lambda r: fmt_power_schemes(r, width),
                headers=["Esquema", "Nombre legible"]
            )

    def _interactive_table(self, title, full_rows, formatter, headers=None, transforms=None, custom_detail_fn=None):
        """
        Muestra la tabla con scroll y permite ver detalle (ENTER).
        El detalle usa los 'full_rows' y no el texto recortado.
        - headers: lista de etiquetas para detalle.
        - transforms: dict {idx: fn} para humanizar campos concretos.
        - custom_detail_fn: callable(row, width) -> str para detalle a medida.
        """
        self.layout.change_footer(" ↑/↓: Navegar  ENTER: Detalle  q/ESC: Volver ")
        selected = 0
        scroll = 0

        while True:
            self.win.clear()
            self.win.box()
            max_y, max_x = self.win.getmaxyx()
            width = max_x - 4

            self.win.addstr(0, max(2, (max_x - len(f" {title} ")) // 2), f" {title} ", curses.A_BOLD)
            table = formatter(full_rows)
            lines = table.split("\n")

            header_lines = 2
            vis_h = max_y - 2
            total = len(lines)

            data_count = max(0, total - header_lines)
            if data_count == 0:
                selected = 0
            else:
                selected = max(0, min(selected, data_count - 1))

            sel_line = selected + header_lines
            if sel_line < scroll + header_lines:
                scroll = sel_line - header_lines
            elif sel_line >= scroll + vis_h:
                scroll = sel_line - vis_h + 1

            max_scroll = max(0, total - vis_h)
            scroll = max(0, min(scroll, max_scroll))

            visibles = lines[scroll:scroll + vis_h]
            for i, line in enumerate(visibles):
                y = i + 1
                abs_line = scroll + i
                if abs_line >= header_lines:
                    data_idx = abs_line - header_lines
                    attr = curses.A_REVERSE if data_idx == selected else curses.A_NORMAL
                else:
                    attr = curses.A_BOLD if abs_line == 0 else curses.A_NORMAL
                self.win.addstr(y, 2, line[:max_x - 4], attr)

            self.win.refresh()
            k = self.win.getch()
            if k == curses.KEY_UP and data_count:
                selected = (selected - 1) % data_count
            elif k == curses.KEY_DOWN and data_count:
                selected = (selected + 1) % data_count
            elif k in (10, 13):
                if data_count:
                    row = full_rows[selected]  # <-- ¡fila original completa!
                    if custom_detail_fn:
                        detail = custom_detail_fn(row, max(20, width))
                    elif headers:
                        detail = _detail_from_row(headers, row, max(20, width), transforms=transforms)
                    else:
                        # fallback: volcar la tupla
                        detail = _wrap(" | ".join("" if v is None else str(v) for v in row), max(20, width))
                    _show_scrollable_popup(self.win, detail, title=f"Detalle: {title}")
            elif k in (27, ord('q')):
                self.layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver archivos")
                break
    def _readline(self, prompt="Filtro: "):
        """Pequeño prompt inline para leer una cadena."""
        max_y, max_x = self.win.getmaxyx()
        curses.curs_set(1)
        try:
            self.win.addstr(max_y-1, 2, " " * (max_x-4))
            self.win.addstr(max_y-1, 2, prompt, curses.A_BOLD)
            self.win.refresh()
            buf = []
            while True:
                ch = self.win.getch()
                if ch in (10, 13):  # Enter
                    return "".join(buf)
                if ch in (27,):     # ESC
                    return None
                if ch in (curses.KEY_BACKSPACE, 127, 8):
                    if buf:
                        buf.pop()
                        x = len(prompt) + len(buf)
                        self.win.addstr(max_y-1, 2+len(prompt), "".join(buf) + " ")
                        self.win.move(max_y-1, 2 + x)
                elif 32 <= ch <= 126:
                    buf.append(chr(ch))
                    self.win.addstr(max_y-1, 2+len(prompt), "".join(buf))
        finally:
            curses.curs_set(0)

    def _services_browser(self):
        # Carga filas originales (sin recortes)
        rows_all = _fetch_all(
            self.db_path,
            "SELECT service_name, display_name, image_path, start_type, service_type "
            "FROM system_services ORDER BY service_name"
        )

        # Estado de filtros
        query = ""
        start_filters = set()  # valores texto: {"Boot","System","Auto","Manual","Disabled"}
        type_filters = set()   # {"kernel","fs","win32"} (fs lo tratamos dentro de 'kernel' por simplicidad visual)
        only_with_path = False
        only_svchost = False
        hide_svchost = False
        suspicious_only = False
        sort_mode = 0  # 0=nombre, 1=start+nombre, 2=ruta

        selected = 0
        scroll = 0

        def start_label(v):
            return _human_start_type(v)

        def type_label(v):
            t = _human_service_type(v)
            return t

        def is_svchost(p):
            return isinstance(p, str) and "svchost.exe" in p.lower()

        def _norm(p):
            if not p:
                return ""
            s = str(p).strip().strip('"').replace("/", "\\").lower()

            # Quitar prefijos de namespace NT
            if s.startswith("\\??\\") or s.startswith("\\\\?\\"):
                s = s[4:]

            # Normalizaciones típicas
            s = s.replace("%systemroot%", "\\windows")
            s = s.replace("\\systemroot\\", "\\windows\\")
            s = s.replace("%windir%", "\\windows")
            s = s.replace("%systemdrive%", "c:")

            # Compactar dobles backslashes
            while "\\\\" in s:
                s = s.replace("\\\\", "\\")

            return s


        def _extract_exe(img):
            """Devuelve solo la ruta del ejecutable (sin args) normalizada."""
            if not img:
                return ""
            s = str(img).strip()
            if s.startswith('"'):
                j = s.find('"', 1)
                exe = s[1:j] if j > 1 else s.strip('"')
            else:
                exe = s.split()[0]
            return _norm(exe)

        def _is_interpreter_path(s):
            names = [
                "\\cmd.exe", "\\powershell.exe", "\\wscript.exe", "\\cscript.exe",
                "\\rundll32.exe", "\\mshta.exe", "\\regsvr32.exe"
            ]
            return any(n in s for n in names)

        def _is_kernel_or_fs(stype):
            try:
                v = int(stype)
            except Exception:
                return False
            return bool(v & 0x00000001) or bool(v & 0x00000002)  # Kernel / FS

        def suspicious_reason(row):
            """
            Devuelve una cadena con la razón de sospecha o None si no es sospechoso.
            row = (service_name, display_name, image_path, start_type, service_type)
            """
            _, _, img, _, stype = row
            exe = _extract_exe(img)
            if not exe:
                return None

            bad_dirs = ["\\users\\", "\\appdata\\", "\\local settings\\", "\\temp\\", "\\tmp\\", "\\programdata\\"]
            if any(b in exe for b in bad_dirs):
                return "Ubicación de usuario/AppData/Temp/ProgramData"

            if exe.startswith("\\\\"):
                return "Ruta UNC (red)"

            if _is_interpreter_path(exe):
                return "Usa intérprete/lanzador (cmd/powershell/wscript/etc.)"

            if _is_kernel_or_fs(stype) and "system32\\drivers\\" not in exe:
                return "Driver fuera de system32\\drivers\\"


            return None

        def is_suspicious_service_row(row):
            return suspicious_reason(row) is not None


        # Ordenación estable
        start_order = {"Boot": 0, "System": 1, "Auto": 2, "Manual": 3, "Disabled": 4}

        def apply_filters():
            # filtra
            res = []
            q = query.lower().strip()
            for r in rows_all:
                sname, dname, img, st, stype = r
                s_lbl = start_label(st) or ""
                t_lbl = (type_label(stype) or "").lower()

                # texto
                if q:
                    hay = False
                    for field in (sname, dname, img):
                        if field and q in str(field).lower():
                            hay = True
                            break
                    if not hay:
                        continue

                # filtros start
                if start_filters:
                    if (s_lbl or "") not in start_filters:
                        continue

                # filtros tipo
                if type_filters:
                    tl = t_lbl
                    want = []
                    if "kernel" in type_filters:
                        want.append("kernel driver")
                        want.append("fs driver")
                    if "win32" in type_filters:
                        want.append("win32 own proc")
                        want.append("win32 shared proc")
                    if not any(w in tl for w in want):
                        continue

                # solo con ruta
                if only_with_path and (not img or not str(img).strip()):
                    continue

                # svchost solo / ocultar
                if only_svchost and not is_svchost(img):
                    continue
                if hide_svchost and is_svchost(img):
                    continue

                # sospechosos
                if suspicious_only and not is_suspicious_service_row(r):
                    continue

                res.append(r)

            # ordenar
            if sort_mode == 0:
                res.sort(key=lambda r: (str(r[0] or "").lower(), str(r[1] or "").lower()))
            elif sort_mode == 1:
                res.sort(key=lambda r: (start_order.get(start_label(r[3]) or "Manual", 99),
                                        str(r[0] or "").lower()))
            else:
                res.sort(key=lambda r: (str(r[2] or "").lower(), str(r[0] or "").lower()))
            return res

        def filters_badge(max_w):
            parts = []
            if query:
                parts.append(f"q='{query}'")
            if start_filters:
                parts.append("start=" + ",".join(sorted(start_filters, key=lambda x: start_order.get(x, 99))))
            if type_filters:
                parts.append("type=" + ",".join(sorted(type_filters)))
            if only_with_path:
                parts.append("path=solo")
            if only_svchost:
                parts.append("svchost=solo")
            if hide_svchost:
                parts.append("svchost=ocultar")
            if suspicious_only:
                parts.append("suspicious=on")
            sm = {0:"sort=nombre", 1:"sort=start", 2:"sort=ruta"}[sort_mode]
            parts.append(sm)
            s = " | ".join(parts) if parts else "sin filtros"
            return s[:max_w]

        headers = ["Servicio", "Nombre", "Imagen", "Inicio", "Tipo"]
        transforms = {3: _human_start_type, 4: _human_service_type}

        self.layout.change_footer(
            " f:buscar  a/m/d/y/b:Start  x:limpiar Start  k/w:t.TIPO  t:limpiar Tipo  "
            "p:solo ruta  v:solo svchost  V:ocultar svchost  u:sospechosos  o:orden  c:limpiar q  r:reset  ENTER:detalle  q/ESC:salir "
        )

        while True:
            filtered = apply_filters()
            # mantener selección en rango
            if filtered:
                selected = max(0, min(selected, len(filtered)-1))
            else:
                selected = 0

            self.win.clear()
            self.win.box()
            max_y, max_x = self.win.getmaxyx()
            width = max_x - 4

            # título
            title = " SYSTEM: Servicios "
            self.win.addstr(0, max(2, (max_x - len(title)) // 2), title, curses.A_BOLD)

            # línea de filtros (estado)
            status = filters_badge(max_x - 4)
            self.win.addstr(1, 2, status, curses.A_DIM)

            # render de tabla
            # usamos el formatter existente, pero pintamos desde y=2 para dejar la línea de estado
            table = fmt_system_services(
                [(r[0], r[1], r[2], r[3], r[4]) for r in filtered],
                width
            )
            lines = table.split("\n")

            header_lines = 2
            vis_h = max_y - 3  # una línea extra usada por el status
            total = len(lines)

            data_count = max(0, total - header_lines)
            sel_line = selected + header_lines

            # scroll con la nueva altura visible
            if sel_line < scroll + header_lines:
                scroll = sel_line - header_lines
            elif sel_line >= scroll + vis_h:
                scroll = sel_line - vis_h + 1
            scroll = max(0, min(scroll, max(0, total - vis_h)))

            visibles = lines[scroll:scroll + vis_h]
            for i, line in enumerate(visibles):
                y = i + 2  # +2 por título y status
                abs_line = scroll + i
                if abs_line >= header_lines:
                    data_idx = abs_line - header_lines
                    attr = curses.A_REVERSE if data_idx == selected else curses.A_NORMAL
                else:
                    attr = curses.A_BOLD if abs_line == 0 else curses.A_NORMAL
                self.win.addstr(y, 2, line[:max_x - 4], attr)

            self.win.refresh()
            k = self.win.getch()

            if k == curses.KEY_UP and data_count:
                selected = (selected - 1) % max(1, data_count)
            elif k == curses.KEY_DOWN and data_count:
                selected = (selected + 1) % max(1, data_count)
            elif k in (10, 13):
                if filtered:
                    row = filtered[selected]
                    detail = _detail_from_row(headers, row, max(20, width), transforms={3: _human_start_type, 4: _human_service_type})
                    reason = suspicious_reason(row)
                    if reason:
                        detail += f"\n\nSospechoso: {reason}"
                    _show_scrollable_popup(self.win, detail, title="Detalle: Servicio")

            elif k in (27, ord('q')):
                self.layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Abrir sección")
                return

            # ---- filtros / toggles ----
            elif k == ord('f'):
                s = self._readline("Buscar (q): ")
                if s is not None:
                    query = s.strip()
            elif k == ord('c'):
                query = ""

            # start type toggles
            elif k == ord('a'):
                start_filters ^= {"Auto"} if "Auto" in start_filters else {"Auto"}
            elif k == ord('m'):
                start_filters ^= {"Manual"} if "Manual" in start_filters else {"Manual"}
            elif k == ord('d'):
                start_filters ^= {"Disabled"} if "Disabled" in start_filters else {"Disabled"}
            elif k == ord('y'):  # system
                start_filters ^= {"System"} if "System" in start_filters else {"System"}
            elif k == ord('b'):
                start_filters ^= {"Boot"} if "Boot" in start_filters else {"Boot"}
            elif k == ord('x'):
                start_filters.clear()

            # type filters
            elif k == ord('k'):
                if "kernel" in type_filters:
                    type_filters.remove("kernel")
                else:
                    type_filters.add("kernel")
            elif k == ord('w'):
                if "win32" in type_filters:
                    type_filters.remove("win32")
                else:
                    type_filters.add("win32")
            elif k == ord('t'):
                type_filters.clear()

            # others
            elif k == ord('p'):
                only_with_path = not only_with_path
            elif k == ord('v'):
                only_svchost = True
                hide_svchost = False
            elif k == ord('V'):
                hide_svchost = True
                only_svchost = False
            elif k == ord('u'):
                suspicious_only = not suspicious_only
            elif k == ord('o'):
                sort_mode = (sort_mode + 1) % 3
            elif k == ord('r'):
                query = ""
                start_filters.clear()
                type_filters.clear()
                only_with_path = False
                only_svchost = False
                hide_svchost = False
                suspicious_only = False
                sort_mode = 0


def visualizar_artefactos_sistema(db_path):
    layout = AwesomeLayout()
    layout.render()
    layout.change_header("Artefactos del sistema")
    layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Abrir sección")

    view = SystemArtifactsViewer(layout.body_win, db_path, layout)
    view.render()
    view.win.keypad(True)

    while True:
        key = layout.win.getch()
        if key in (27, ord('q')):
            layout.clear()
            break
        view.handle_input(key)
        view.render()
