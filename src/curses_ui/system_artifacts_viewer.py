import curses
import sqlite3
import textwrap

from .renderizable import Renderizable
from curses_ui.awesome_layout import AwesomeLayout

def _fmt_size_short(n):
    try:
        n = int(n)
    except Exception:
        return ""
    units = ["B","KB","MB","GB","TB","PB"]
    x = float(n); i = 0
    while x >= 1024 and i < len(units)-1:
        x /= 1024.0; i += 1
    return f"{int(x)} {units[i]}" if i == 0 else f"{x:.1f} {units[i]}"

def _fmt_bytes_full(n):
    try:
        n = int(n)
    except Exception:
        return ""
    return f"{n} bytes (0x{n:X}) — {_fmt_size_short(n)}"



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

def fmt_partitions(rows, width):
    # rows: (description, fs_type, label, start_offset, length, partition_offset, block_size, block_count, case_name, partition_id)
    w1 = int(width*0.26)  # Descripción
    w2 = int(width*0.08)  # FS
    w3 = int(width*0.16)  # Label
    w4 = int(width*0.16)  # Inicio
    w5 = int(width*0.16)  # Tamaño
    w6 = width - (w1 + w2 + w3 + w4 + w5 + 8)  # Offset (lo que quede de width)

    out = []
    head = f"{'Descripción':<{w1}}│ {'FS':<{w2}}│ {'Etiqueta':<{w3}}│ {'Inicio(Sector)':<{w4}}│ {'Tamaño':<{w5}}│ {'Offset':<{w6}}"
    out.append(head); out.append("─"*len(head))

    for desc, fs, label, start_off, _length, part_off, block_sz, block_cnt, *_ in rows:
        try:
            calc_size = int(block_sz or 0) * int(block_cnt or 0)
        except Exception:
            calc_size = 0

        out.append(
            f"{_recortar(desc, w1):<{w1}}│ {_recortar(fs, w2):<{w2}}│ {_recortar(label, w3):<{w3}}│ "
            f"{_recortar(start_off, w4):<{w4}}│ {_recortar(_fmt_size_short(calc_size), w5):<{w5}}│ "
            f"{_recortar(_fmt_size_short(part_off), w6):<{w6}}"
        )
    return "\n".join(out)


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
            "Active Setup (Installed Components)",
            "App Paths (resumen)",
            "App Paths (metadatos)",
            "Grupos de svchost",
            # SYSTEM hive
            "Último arranque",
            "Servicios",
            "Dispositivos USB",
            "Perfiles de energía",
            "Particiones (disco)"
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
            rows = _fetch_all(self.db_path,
                "SELECT component_id, stub_path, version, is_installed, component_name FROM installed_components ORDER BY component_id")
            self._interactive_table(
                "SOFTWARE: Active Setup",
                rows,
                lambda r: fmt_installed_components(r, width),
                headers=["ComponentID", "StubPath", "Version", "IsInstalled", "Nombre"]
            )

        elif idx == 4:
            rows = _fetch_all(self.db_path, "SELECT executable, path FROM app_paths ORDER BY executable")
            self._interactive_table(
                "SOFTWARE: App Paths (resumen)",
                rows,
                lambda r: fmt_app_paths(r, width),
                headers=["Ejecutable", "Ruta"]
            )

        elif idx == 5:
            rows = _fetch_all(self.db_path,
                "SELECT executable, value_name, value_data, key_path, timestamp FROM app_paths_meta ORDER BY executable, value_name")
            self._interactive_table(
                "SOFTWARE: App Paths (metadatos)",
                rows,
                lambda r: fmt_app_paths_meta(r, width),
                headers=["Exe", "Valor", "Dato", "Clave", "Timestamp"]
            )

        elif idx == 6:
            rows = _fetch_all(self.db_path, "SELECT group_name, services FROM svchost_groups ORDER BY group_name")
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
        elif idx == 7:
            rows = _fetch_all(self.db_path, "SELECT last_boot_time FROM system_info ORDER BY id DESC LIMIT 1")
            table = fmt_system_lastboot(rows, width)
            _show_scrollable_popup(self.win, table, "SYSTEM: Último arranque")
            return

        elif idx == 8:
            self._services_browser()

        elif idx == 9:
            rows = _fetch_all(self.db_path,
                "SELECT device_class, device_id, friendly_name, device_desc FROM usb_devices ORDER BY device_class, device_id")
            self._interactive_table(
                "SYSTEM: Dispositivos USB",
                rows,
                lambda r: fmt_usb_devices(r, width),
                headers=["Clase", "ID", "Nombre", "Descripción"]
            )

        elif idx == 10:
            rows = _fetch_all(self.db_path,
                "SELECT scheme_name, friendly_name FROM power_schemes ORDER BY scheme_name")
            self._interactive_table(
                "SYSTEM: Perfiles de energía",
                rows,
                lambda r: fmt_power_schemes(r, width),
                headers=["Esquema", "Nombre legible"]
            )

        elif idx == 11:  # Particiones (disco)
            rows = _fetch_all(
                self.db_path,
                """
                SELECT
                    description,
                    fs_type,
                    label,
                    start_offset,
                    length,
                    partition_offset,
                    block_size,
                    block_count,
                    case_name,
                    partition_id
                FROM partition_info
                ORDER BY start_offset
                """
            )

            def _partition_detail(row, w):
                desc, fs, label, start_off, length, part_off, block_sz, block_cnt, case_name, part_id = row
                try:
                    calc_size = int(block_sz or 0) * int(block_cnt or 0)
                except Exception:
                    calc_size = 0

                parts = [
                    f"Descripción:\n{_wrap(desc, w)}",
                    f"FS:\n{_wrap(fs, w)}",
                    f"Etiqueta:\n{_wrap(label, w)}",
                    f"Sector de Inicio:\n{_wrap(start_off, w)}",
                    f"Tamaño (calculado = block_size × block_count):\n{_wrap(_fmt_bytes_full(calc_size), w)}",
                    f"Tamaño en sectores:\n{_wrap(length, w)}",
                ]

                parts.extend([
                    f"Offset de partición:\n{_wrap(_fmt_bytes_full(part_off), w)}",
                    f"Tamaño de bloque:\n{_wrap(_fmt_bytes_full(block_sz), w)}",
                    f"Número de bloques:\n{_wrap(block_cnt, w)}",
                    f"Caso:\n{_wrap(case_name, w)}",
                    f"Partition ID:\n{_wrap(part_id, w)}",
                ])
                return "\n\n".join(parts)

            self._interactive_table(
                "SYSTEM: Particiones / Volúmenes",
                rows,
                lambda r: fmt_partitions(r, width),
                headers=None,                 # usamos detalle personalizado
                custom_detail_fn=_partition_detail
            )


    def _interactive_table(self, title, full_rows, formatter, headers=None, transforms=None, custom_detail_fn=None):
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


            if len(lines) >= 1:
                self.win.addstr(1, 2, lines[0][:max_x-4], curses.A_BOLD)
            if len(lines) >= 2:
                self.win.addstr(2, 2, lines[1][:max_x-4], curses.A_NORMAL)


            data_lines = lines[header_lines:]

            # Calcular scroll y visibilidad (las dos primeras líneas son el encabezado)
            vis_h = max(1, (max_y - 2) - header_lines)

            data_count = len(data_lines)
            if data_count == 0:
                selected = 0
            else:
                selected = max(0, min(selected, data_count - 1))


            if selected < scroll:
                scroll = selected
            elif selected >= scroll + vis_h:
                scroll = selected - vis_h + 1
            scroll = max(0, min(scroll, max(0, data_count - vis_h)))

            # Pintar datos comenzando en y=3
            for i, line in enumerate(data_lines[scroll:scroll + vis_h]):
                y = 3 + i
                attr = curses.A_REVERSE if (scroll + i) == selected else curses.A_NORMAL
                self.win.addstr(y, 2, line[:max_x - 4], attr)

            self.win.refresh()
            k = self.win.getch()

            if k == curses.KEY_UP and data_count:
                selected = (selected - 1) % data_count
            elif k == curses.KEY_DOWN and data_count:
                selected = (selected + 1) % data_count
            elif k in (10, 13):
                if data_count:
                    row = full_rows[selected]
                    if custom_detail_fn:
                        detail = custom_detail_fn(row, max(20, width))
                    elif headers:
                        detail = _detail_from_row(headers, row, max(20, width), transforms=transforms)
                    else:
                        detail = _wrap(" | ".join("" if v is None else str(v) for v in row), max(20, width))
                    _show_scrollable_popup(self.win, detail, title=f"Detalle: {title}")
            elif k in (27, ord('q')):
                self.layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Ver archivos")
                break



    def _readline(self, prompt="Filtro: "):

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
        rows_all = _fetch_all(
            self.db_path,
            "SELECT "
            " service_name, display_name, image_path, start_type, service_type, "
            " image_exe_path, normalized_image_path, servicedll, object_name, description, "
            " is_svchost, suspicious, suspicious_reason "
            "FROM system_services "
            "ORDER BY service_name"
        )

        # índices legibles de las columnas

        SNAME, DNAME, IMG, START, STYPE, IMG_EXE, IMG_NORM, SRVDLL, OBJ, DESC, IS_SVCHOST, SUSP, REASON = range(13)

        # ---- filtros ----
        query = ""
        start_filters = set()     # {"Boot","System","Auto","Manual","Disabled"}
        type_filters = set()      # {"kernel","win32"}
        only_with_path = False
        only_svchost = False
        hide_svchost = False
        suspicious_only = False   
        sort_mode = 0             # 0=nombre, 1=start+nombre, 2=ruta

        selected = 0
        scroll = 0

        def start_label(v): return _human_start_type(v)
        def type_label(v):  return _human_service_type(v)
        def is_svchost(img): return isinstance(img, str) and "svchost.exe" in img.lower()

        start_order = {"Boot": 0, "System": 1, "Auto": 2, "Manual": 3, "Disabled": 4}

        def _yesno(v):
            try:
                return "Sí" if int(v) == 1 else "No"
            except Exception:
                return "Sí" if str(v).lower() in ("true", "1") else "No"

        def apply_filters():
            res = []
            q = query.lower().strip()
            for r in rows_all:
                s_lbl = start_label(r[START]) or ""
                t_lbl = (type_label(r[STYPE]) or "").lower()

                # texto
                if q:
                    hay = False
                    for field in (r[SNAME], r[DNAME], r[IMG], r[IMG_EXE], r[IMG_NORM], r[SRVDLL]):
                        if field and q in str(field).lower():
                            hay = True; break
                    if not hay:
                        continue

                # start type
                if start_filters and (s_lbl or "") not in start_filters:
                    continue

                # tipo (agrupado en kernel/FS o win32)
                if type_filters:
                    want = []
                    if "kernel" in type_filters:
                        want += ["kernel driver", "fs driver"]
                    if "win32" in type_filters:
                        want += ["win32 own proc", "win32 shared proc"]
                    if not any(w in t_lbl for w in want):
                        continue

                # mostrar solo con ruta distinta de None o vacía
                if only_with_path and not (r[IMG] and str(r[IMG]).strip()):
                    continue

                # svchost
                if only_svchost and not is_svchost(r[IMG]):
                    continue
                if hide_svchost and is_svchost(r[IMG]):
                    continue


                if suspicious_only:
                    try:
                        if int(r[SUSP]) != 1:
                            continue
                    except Exception:

                        continue

                res.append(r)

            # ordenación
            if sort_mode == 0:
                res.sort(key=lambda r: (str(r[SNAME] or "").lower(), str(r[DNAME] or "").lower()))
            elif sort_mode == 1:
                res.sort(key=lambda r: (start_order.get(start_label(r[START]) or "Manual", 99),
                                        str(r[SNAME] or "").lower()))
            else:
                res.sort(key=lambda r: (str(r[IMG] or "").lower(), str(r[SNAME] or "").lower()))
            return res

        # ---- badge de filtros (se muestran en la parte superior) ----
        def filters_badge(max_w):
            parts = []
            if query: parts.append(f"q='{query}'")
            if start_filters: parts.append("start=" + ",".join(sorted(start_filters, key=lambda x: start_order.get(x, 99))))
            if type_filters: parts.append("type=" + ",".join(sorted(type_filters)))
            if only_with_path: parts.append("path=solo")
            if only_svchost: parts.append("svchost=solo")
            if hide_svchost: parts.append("svchost=ocultar")
            if suspicious_only: parts.append("suspicious=on")  # <- ahora viene de BD
            parts.append({0:"sort=nombre", 1:"sort=start", 2:"sort=ruta"}[sort_mode])
            return " | ".join(parts)[:max_w]

        # cabeceras para el DETALLE (ENTER) usando columnas extendidas
        headers_detail = [
            "Servicio", "Nombre", "Imagen", "Inicio", "Tipo",
            "Ejecutable", "Ruta normalizada", "ServiceDll",
            "Cuenta (ObjectName)", "Descripción",
            "svchost", "Sospechoso", "Motivo"
        ]
        transforms_detail = {
            START: _human_start_type,
            STYPE: _human_service_type,
            IS_SVCHOST: _yesno,
            SUSP: _yesno
        }

        self.layout.change_footer(
            "f:Buscar| c:Limpiar buscar| a/m/d/y/b:Start| x:Limpiar Start| k/w:Tipo| t:limpiar Tipo| "
            "p:Ruta| v/V:svchost| u:sospechosos| o:orden| r:reset| ENTER:detalle| q/ESC:salir"
        )

        while True:
            filtered = apply_filters()
            selected = max(0, min(selected, len(filtered)-1)) if filtered else 0

            self.win.clear(); self.win.box()
            max_y, max_x = self.win.getmaxyx()
            width = max_x - 4

            
            title = " SYSTEM: Servicios "
            self.win.addstr(0, max(2, (max_x - len(title)) // 2), title, curses.A_BOLD)

            # línea de filtros (estado) fija en y=1
            status = filters_badge(max_x - 4)
            self.win.addstr(1, 2, status, curses.A_DIM)

            # Construir tabla 
            table = fmt_system_services(
                [(r[SNAME], r[DNAME], r[IMG], r[START], r[STYPE]) for r in filtered],
                width
            )
            lines = table.split("\n")
            header_lines = 2  # cabecera + separador

            # --- cabecera FIJA de la tabla en y=2 y y=3 ---
            if len(lines) >= 1:
                self.win.addstr(2, 2, lines[0][:max_x-4], curses.A_BOLD)
            if len(lines) >= 2:
                self.win.addstr(3, 2, lines[1][:max_x-4], curses.A_NORMAL)

            # Solo datos a partir de aquí
            data_lines = lines[header_lines:]

            # Altura visible: interior (max_y-2) menos (1 línea status + 2 cabeceras) => max_y - 5
            vis_h = max(1, (max_y - 2) - (1 + header_lines))

            data_count = len(data_lines)
            selected = max(0, min(selected, data_count - 1)) if data_count else 0

            # scroll solo de datos NO LA CABECERA
            if selected < scroll:
                scroll = selected
            elif selected >= scroll + vis_h:
                scroll = selected - vis_h + 1
            scroll = max(0, min(scroll, max(0, data_count - vis_h)))

            # Pintar datos comenzando en y=4
            for i, line in enumerate(data_lines[scroll:scroll + vis_h]):
                y = 4 + i
                attr = curses.A_NORMAL

                # marcar sospechosos en negrita PARA QUE SE VEA CLARAMENTE
                if data_count:
                    data_idx = scroll + i
                    try:
                        if int(filtered[data_idx][SUSP] or 0) == 1:
                            attr |= curses.A_BOLD
                    except Exception:
                        pass
                    if data_idx == selected:
                        attr |= curses.A_REVERSE

                self.win.addstr(y, 2, line[:max_x - 4], attr)


            self.win.refresh()
            k = self.win.getch()
            if k == curses.KEY_UP and data_count > 0:
                selected = (selected - 1) % data_count
            elif k == curses.KEY_DOWN and data_count > 0:
                selected = (selected + 1) % data_count
            elif k in (10, 13) and filtered:
                row = filtered[selected]
                detail = _detail_from_row(headers_detail, row, max(20, width), transforms=transforms_detail)
                _show_scrollable_popup(self.win, detail, title="Detalle: Servicio")
            elif k in (27, ord('q')):
                self.layout.change_footer("ESC: Salir, ↑/↓: Navegar, ENTER: Abrir sección")
                return

            # ---- toggles / filtros ----
            elif k == ord('f'):
                s = self._readline("Buscar (q): ")
                if s is not None:
                    query = s.strip()
            elif k == ord('c'):
                query = ""
            elif k == ord('a'):
                start_filters ^= {"Auto"} if "Auto" in start_filters else {"Auto"}
            elif k == ord('m'):
                start_filters ^= {"Manual"} if "Manual" in start_filters else {"Manual"}
            elif k == ord('d'):
                start_filters ^= {"Disabled"} if "Disabled" in start_filters else {"Disabled"}
            elif k == ord('y'):
                start_filters ^= {"System"} if "System" in start_filters else {"System"}
            elif k == ord('b'):
                start_filters ^= {"Boot"} if "Boot" in start_filters else {"Boot"}
            elif k == ord('x'):
                start_filters.clear()
            elif k == ord('k'):
                type_filters.symmetric_difference_update({"kernel"})
            elif k == ord('w'):
                type_filters.symmetric_difference_update({"win32"})
            elif k == ord('t'):
                type_filters.clear()
            elif k == ord('p'):
                only_with_path = not only_with_path
            elif k == ord('v'):
                only_svchost, hide_svchost = True, False
            elif k == ord('V'):
                hide_svchost, only_svchost = True, False
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
