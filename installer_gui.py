"""
Instalador gráfico de Drunks POS.
Descarga la última versión desde GitHub Releases y la instala con una GUI.
Solo usa stdlib + tkinter (incluido en Python). Sin dependencias externas.
"""
import json
import os
import subprocess
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

# ── Constantes ────────────────────────────────────────────────────────────────
GITHUB_REPO     = "TheWiche/Drunks-POS"
APP_NAME        = "Drunks POS"
DEFAULT_INSTALL = r"C:\Drunks POS"
WIN_W, WIN_H    = 520, 440

BG       = "#0d0d1a"
ACCENT   = "#7c3aed"
FG       = "#ffffff"
FG_DIM   = "#8b8ba8"
SUCCESS  = "#10b981"
DANGER   = "#ef4444"
ENTRY_BG = "#1e1e35"
BTN_SEC  = "#2d2d4a"


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Instalador")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Centrar en pantalla
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{(sw-WIN_W)//2}+{(sh-WIN_H)//2}")

        self.install_path  = tk.StringVar(value=DEFAULT_INSTALL)
        self.make_shortcut = tk.BooleanVar(value=True)
        self.open_after    = tk.BooleanVar(value=True)

        self._build()

    # ── Construcción de UI ────────────────────────────────────────────────────
    def _build(self):
        # Cabecera morada
        hdr = tk.Frame(self.root, bg=ACCENT, height=76)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🍺  Drunks POS", font=("Segoe UI", 20, "bold"),
                 fg=FG, bg=ACCENT).pack(side=tk.LEFT, padx=24, pady=(18, 0))
        tk.Label(hdr, text="  Instalador", font=("Segoe UI", 11),
                 fg="#c4b5fd", bg=ACCENT).pack(side=tk.LEFT, pady=(22, 0))

        # Cuerpo
        body = tk.Frame(self.root, bg=BG, padx=28, pady=20)
        body.pack(fill=tk.BOTH, expand=True)

        # Ruta de instalación
        tk.Label(body, text="Carpeta de instalación:",
                 font=("Segoe UI", 10), fg=FG_DIM, bg=BG).pack(anchor=tk.W)

        path_row = tk.Frame(body, bg=BG)
        path_row.pack(fill=tk.X, pady=(5, 16))

        self.path_entry = tk.Entry(
            path_row, textvariable=self.install_path,
            font=("Segoe UI", 10), bg=ENTRY_BG, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            highlightthickness=1, highlightbackground="#2d2d4a",
            highlightcolor=ACCENT)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9, ipadx=8)

        browse = tk.Button(
            path_row, text="Examinar",
            font=("Segoe UI", 9), bg=BTN_SEC, fg=FG,
            activebackground="#3d3d5a", activeforeground=FG,
            relief=tk.FLAT, cursor="hand2", padx=12, pady=8,
            command=self._browse)
        browse.pack(side=tk.LEFT, padx=(8, 0))

        # Separador
        tk.Frame(body, bg="#2d2d4a", height=1).pack(fill=tk.X, pady=(0, 14))

        # Opciones
        tk.Label(body, text="Opciones:",
                 font=("Segoe UI", 10), fg=FG_DIM, bg=BG).pack(anchor=tk.W, pady=(0, 6))

        tk.Checkbutton(
            body, text="Crear acceso directo en el Escritorio",
            variable=self.make_shortcut,
            font=("Segoe UI", 10), fg=FG, bg=BG,
            selectcolor=ACCENT, activebackground=BG, activeforeground=FG
        ).pack(anchor=tk.W, pady=3)

        tk.Checkbutton(
            body, text="Abrir Drunks POS al terminar la instalación",
            variable=self.open_after,
            font=("Segoe UI", 10), fg=FG, bg=BG,
            selectcolor=ACCENT, activebackground=BG, activeforeground=FG
        ).pack(anchor=tk.W, pady=3)

        # Zona de estado y progreso
        status_frame = tk.Frame(body, bg=BG)
        status_frame.pack(fill=tk.X, pady=(18, 0))

        self.status_lbl = tk.Label(
            status_frame, text="",
            font=("Segoe UI", 9), fg=FG_DIM, bg=BG, anchor=tk.W)
        self.status_lbl.pack(fill=tk.X)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("D.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=ENTRY_BG,
                        borderwidth=0, thickness=5)
        self.progress = ttk.Progressbar(
            status_frame, style="D.Horizontal.TProgressbar",
            mode="indeterminate", length=464)

        # Botón principal
        self.install_btn = tk.Button(
            body, text="    Instalar ahora    ",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT, fg=FG,
            activebackground="#6d28d9", activeforeground=FG,
            relief=tk.FLAT, cursor="hand2", padx=28, pady=12,
            command=self._start_install)
        self.install_btn.pack(side=tk.BOTTOM, pady=(0, 4))

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(
            initialdir=self.install_path.get(),
            title="Elige la carpeta de instalación")
        if path:
            self.install_path.set(path.replace("/", "\\"))

    def _start_install(self):
        self.install_btn.config(state=tk.DISABLED, text="  Instalando...  ")
        self.progress.pack(fill=tk.X, pady=(6, 0))
        self.progress.start(12)
        threading.Thread(target=self._install, daemon=True).start()

    def _set_status(self, msg, color=None):
        self.root.after(0, lambda: self.status_lbl.config(
            text=msg, fg=color or FG_DIM))

    # ── Lógica de instalación ─────────────────────────────────────────────────
    def _install(self):
        dest = Path(self.install_path.get()) / "Drunks"
        try:
            # 1. Consultar última versión
            self._set_status("Consultando versión en GitHub...")
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
                raise RuntimeError(
                    "No se encontró el archivo en GitHub.\n"
                    "Verifica tu conexión a internet.")

            version = data.get("tag_name", "")
            size_mb = asset["size"] // (1024 * 1024)

            # 2. Descargar ZIP
            self._set_status(f"Descargando {asset['name']}  ({size_mb} MB)...")
            tmp_zip = Path(tempfile.gettempdir()) / "drunks_install.zip"
            urllib.request.urlretrieve(asset["browser_download_url"], tmp_zip)

            # 3. Extraer
            self._set_status("Extrayendo archivos...")
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(dest)
            tmp_zip.unlink(missing_ok=True)

            # 4. Acceso directo
            if self.make_shortcut.get():
                self._set_status("Creando acceso directo...")
                self._create_shortcut(dest)

            self.root.after(0, self._done, dest, version)

        except Exception as exc:
            self.root.after(0, self._on_error, str(exc))

    def _create_shortcut(self, dest: Path):
        desktop = Path(os.path.expandvars("%USERPROFILE%")) / "Desktop"
        lnk     = str(desktop / "Drunks POS.lnk")
        target  = str(dest / "INICIAR_SISTEMA.bat")
        wd      = str(dest)
        ps = (
            f"$s=New-Object -ComObject WScript.Shell;"
            f"$l=$s.CreateShortcut('{lnk}');"
            f"$l.TargetPath='{target}';"
            f"$l.WorkingDirectory='{wd}';"
            f"$l.Description='Drunks POS - Sistema de Ventas';"
            f"$l.Save()"
        )
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True)

    # ── Pantallas de resultado ────────────────────────────────────────────────
    def _done(self, dest: Path, version: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_lbl.config(
            text=f"✓  Instalado correctamente  {version}",
            fg=SUCCESS, font=("Segoe UI", 10, "bold"))
        tk.Label(self.status_lbl.master, text=str(dest),
                 font=("Segoe UI", 8), fg=FG_DIM, bg=BG,
                 anchor=tk.W).pack(fill=tk.X)

        if self.open_after.get():
            self._launch(dest)
            self.root.after(1800, self.root.quit)
        else:
            self.install_btn.config(
                state=tk.NORMAL, text="  Cerrar  ",
                bg=SUCCESS, command=self.root.quit)

    def _on_error(self, msg: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_lbl.config(
            text=f"✗  {msg}",
            fg=DANGER, font=("Segoe UI", 9))
        self.install_btn.config(
            state=tk.NORMAL, text="  Reintentar  ",
            bg=ACCENT)

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
