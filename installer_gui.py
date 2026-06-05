"""
Instalador gráfico de Drunks POS.
Descarga la última versión desde GitHub Releases y la instala con una GUI.
No requiere dependencias externas — solo stdlib + tkinter (incluido en Python).
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

# ── Constantes ────────────────────────────────────────────────────────────────
GITHUB_REPO      = "TheWiche/Drunks-POS"
APP_NAME         = "Drunks POS"
DEFAULT_INSTALL  = r"C:\Drunks POS"
WIN_W, WIN_H     = 520, 460

# Paleta de colores
BG       = "#0d0d1a"
CARD     = "#16162a"
ACCENT   = "#7c3aed"
ACCHOV   = "#6d28d9"
FG       = "#ffffff"
FG_DIM   = "#8b8ba8"
SUCCESS  = "#10b981"
DANGER   = "#ef4444"
ENTRY_BG = "#1e1e35"
BTN_BG   = "#2d2d4a"


# ── Helpers de estilo ─────────────────────────────────────────────────────────
def label(parent, text, size=10, bold=False, color=None, **kw):
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        fg=color or FG, bg=kw.pop("bg", BG), **kw)

def btn(parent, text, command, size=10, bg=None, fg=FG, **kw):
    b = tk.Button(
        parent, text=text, command=command,
        font=("Segoe UI", size),
        bg=bg or BTN_BG, fg=fg,
        activebackground=ACCHOV, activeforeground=FG,
        relief=tk.FLAT, cursor="hand2",
        padx=kw.pop("padx", 16), pady=kw.pop("pady", 9),
        **kw)
    if bg:
        b.bind("<Enter>", lambda e: b.config(bg=ACCHOV if bg == ACCENT else bg))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


# ── Ventana principal ─────────────────────────────────────────────────────────
class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Instalador")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Centrar en pantalla
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - WIN_W) // 2
        y = (self.root.winfo_screenheight() - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # Variables de estado
        self.install_path   = tk.StringVar(value=DEFAULT_INSTALL)
        self.make_shortcut  = tk.BooleanVar(value=True)
        self.open_after     = tk.BooleanVar(value=True)

        self._build_header()
        self._build_body()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=ACCENT, height=80)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        inner = tk.Frame(hdr, bg=ACCENT)
        inner.pack(side=tk.LEFT, padx=24, pady=0, fill=tk.Y)

        label(inner, "🍺  Drunks POS", size=20, bold=True, bg=ACCENT).pack(
            anchor=tk.W, pady=(18, 0))
        label(inner, "Instalador de sistema", size=10, color="#d4b8ff", bg=ACCENT).pack(
            anchor=tk.W)

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG, padx=30, pady=22)
        body.pack(fill=tk.BOTH, expand=True)

        # ── Ruta de instalación ──────────────────────────────────────────────
        label(body, "Carpeta de instalación:", color=FG_DIM).pack(anchor=tk.W)

        row = tk.Frame(body, bg=BG)
        row.pack(fill=tk.X, pady=(5, 18))

        self.path_entry = tk.Entry(
            row, textvariable=self.install_path,
            font=("Segoe UI", 10), bg=ENTRY_BG, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#2d2d4a",
            highlightcolor=ACCENT)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9, ipadx=10)

        btn(row, "Examinar", self._browse, padx=14, pady=8).pack(side=tk.LEFT, padx=(8, 0))

        # ── Separador ────────────────────────────────────────────────────────
        sep = tk.Frame(body, bg="#2d2d4a", height=1)
        sep.pack(fill=tk.X, pady=(0, 16))

        # ── Opciones ─────────────────────────────────────────────────────────
        label(body, "Opciones:", color=FG_DIM).pack(anchor=tk.W, pady=(0, 8))

        self._chk(body, "Crear acceso directo en el Escritorio", self.make_shortcut)
        self._chk(body, "Abrir Drunks POS al terminar la instalación", self.open_after)

        # ── Zona de progreso ─────────────────────────────────────────────────
        self.prog_frame = tk.Frame(body, bg=BG)
        self.prog_frame.pack(fill=tk.X, pady=(20, 0))

        self.status_lbl = label(self.prog_frame, "", color=FG_DIM)
        self.status_lbl.pack(anchor=tk.W)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("D.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=ENTRY_BG,
                        borderwidth=0, thickness=5)
        self.progress = ttk.Progressbar(
            self.prog_frame, style="D.Horizontal.TProgressbar",
            mode="indeterminate", length=460)

        # ── Botón instalar ────────────────────────────────────────────────────
        self.install_btn = btn(
            body, "    Instalar ahora    ",
            self._start_install, size=12, bold=True,
            bg=ACCENT, pady=12, padx=28)
        self.install_btn.pack(side=tk.BOTTOM, pady=(0, 4))

    def _chk(self, parent, text, var):
        tk.Checkbutton(
            parent, text=text, variable=var,
            font=("Segoe UI", 10),
            fg=FG, bg=BG,
            selectcolor=ACCENT,
            activebackground=BG, activeforeground=FG,
            highlightthickness=0
        ).pack(anchor=tk.W, pady=3)

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.install_path.get(),
                                       title="Elige la carpeta de instalación")
        if path:
            self.install_path.set(path.replace("/", "\\"))

    def _start_install(self):
        self.install_btn.config(state=tk.DISABLED, text="  Instalando...  ")
        self.progress.pack(fill=tk.X, pady=(6, 0))
        self.progress.start(12)
        threading.Thread(target=self._install, daemon=True).start()

    def _status(self, msg, color=None):
        self.root.after(0, lambda: self.status_lbl.config(
            text=msg, fg=color or FG_DIM))

    # ── Lógica de instalación ─────────────────────────────────────────────────
    def _install(self):
        dest = Path(self.install_path.get())
        try:
            # 1. Consultar última versión en GitHub
            self._status("Consultando versión en GitHub...")
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json",
                         "User-Agent": "DrunksInstaller/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            asset = next(
                (a for a in data.get("assets", []) if a["name"].endswith(".zip")),
                None)
            if not asset:
                raise RuntimeError("No se encontró el archivo de instalación en GitHub.\n"
                                   "Verifica tu conexión a internet.")

            version = data.get("tag_name", "")

            # 2. Descargar ZIP
            self._status(f"Descargando {asset['name']}  ({asset['size'] // (1024*1024)} MB)...")
            tmp_zip = Path(tempfile.gettempdir()) / "drunks_install.zip"
            urllib.request.urlretrieve(asset["browser_download_url"], tmp_zip)

            # 3. Extraer
            self._status("Extrayendo archivos...")
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(dest)
            tmp_zip.unlink(missing_ok=True)

            # 4. Acceso directo
            if self.make_shortcut.get():
                self._status("Creando acceso directo en el Escritorio...")
                self._create_shortcut(dest)

            self.root.after(0, self._done, dest, version)

        except Exception as exc:
            self.root.after(0, self._on_error, str(exc))

    def _create_shortcut(self, dest: Path):
        desktop = Path(os.path.expandvars("%USERPROFILE%")) / "Desktop"
        lnk     = desktop / "Drunks POS.lnk"
        target  = dest / "INICIAR_SISTEMA.bat"
        ps = (
            f'$s=New-Object -ComObject WScript.Shell;'
            f'$l=$s.CreateShortcut("{lnk}");'
            f'$l.TargetPath="{target}";'
            f'$l.WorkingDirectory="{dest}";'
            f'$l.Description="Drunks POS - Sistema de Ventas";'
            f'$l.Save()'
        )
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True)

    # ── Estados finales ───────────────────────────────────────────────────────
    def _done(self, dest: Path, version: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_lbl.config(
            text=f"✓  Instalado correctamente  {version}",
            fg=SUCCESS, font=("Segoe UI", 10, "bold"))
        label(self.prog_frame, str(dest), color=FG_DIM, size=9).pack(anchor=tk.W)

        if self.open_after.get():
            self._launch(dest)
            self.root.after(1500, self.root.quit)
        else:
            self.install_btn.config(
                text="  Cerrar  ", state=tk.NORMAL,
                bg=SUCCESS, command=self.root.quit)

    def _on_error(self, msg: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_lbl.config(
            text=f"✗  Error: {msg}",
            fg=DANGER, font=("Segoe UI", 9))
        self.install_btn.config(
            state=tk.NORMAL, text="    Reintentar    ", bg=ACCENT)

    def _launch(self, dest: Path):
        bat = dest / "INICIAR_SISTEMA.bat"
        if bat.exists():
            subprocess.Popen(
                ["cmd", "/c", str(bat)],
                cwd=str(dest),
                creationflags=subprocess.CREATE_NEW_CONSOLE)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = InstallerApp()
    app.run()
