"""
Instalador de Drunks POS.
Descarga la última versión desde GitHub Releases.
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

GITHUB_REPO     = "TheWiche/Drunks-POS"
APP_NAME        = "Drunks POS"
DEFAULT_INSTALL = r"C:\Drunks POS"


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Instalador de {APP_NAME}")
        self.root.geometry("500x310")
        self.root.resizable(False, False)

        # Centrar en pantalla
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"500x310+{(sw-500)//2}+{(sh-310)//2}")

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("default")

        self.install_path  = tk.StringVar(value=DEFAULT_INSTALL)
        self.make_shortcut = tk.BooleanVar(value=True)
        self.open_after    = tk.BooleanVar(value=True)

        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self):
        # Encabezado
        hdr = ttk.Frame(self.root, padding=(16, 14, 16, 10))
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text=f"Instalador de {APP_NAME}",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W)
        ttk.Label(hdr, text="Elige la carpeta donde se instalará el programa y haz clic en Instalar.",
                  font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))

        ttk.Separator(self.root).pack(fill=tk.X)

        # Cuerpo
        body = ttk.Frame(self.root, padding=(16, 12, 16, 8))
        body.pack(fill=tk.BOTH, expand=True)

        ttk.Label(body, text="Carpeta de instalación:").pack(anchor=tk.W)
        path_row = ttk.Frame(body)
        path_row.pack(fill=tk.X, pady=(4, 10))
        ttk.Entry(path_row, textvariable=self.install_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        ttk.Button(path_row, text="Examinar...", command=self._browse).pack(
            side=tk.LEFT, padx=(6, 0))

        ttk.Checkbutton(body, text="Crear acceso directo en el Escritorio",
                        variable=self.make_shortcut).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(body, text="Abrir Drunks POS al terminar la instalación",
                        variable=self.open_after).pack(anchor=tk.W, pady=2)

        # Estado y barra
        status_frame = ttk.Frame(body)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.status_var,
                  font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.progress = ttk.Progressbar(status_frame, mode="determinate",
                                        maximum=100, length=450)
        self.progress.pack(fill=tk.X, pady=(4, 0))

        ttk.Separator(self.root).pack(fill=tk.X)

        # Botones
        btn_row = ttk.Frame(self.root, padding=(0, 8, 14, 8))
        btn_row.pack(fill=tk.X)
        self.cancel_btn = ttk.Button(btn_row, text="Cancelar", command=self.root.quit)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.install_btn = ttk.Button(btn_row, text="Instalar", command=self._start_install,
                                      style="Accent.TButton")
        self.install_btn.pack(side=tk.RIGHT)

    # ── Acciones ─────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(
            initialdir=self.install_path.get(),
            title="Elige la carpeta de instalación")
        if path:
            self.install_path.set(path.replace("/", "\\"))

    def _start_install(self):
        self.install_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        self.progress["value"] = 0
        threading.Thread(target=self._install, daemon=True).start()

    def _set_status(self, msg: str, pct: int = None):
        def _apply():
            self.status_var.set(msg)
            if pct is not None:
                self.progress["value"] = pct
        self.root.after(0, _apply)

    # ── Lógica de instalación ─────────────────────────────────────────────────
    def _install(self):
        dest = Path(self.install_path.get()) / "Drunks"
        try:
            # 1. Consultar GitHub
            self._set_status("Consultando versión en GitHub...", 0)
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
                raise RuntimeError("No se encontró el archivo de descarga en GitHub.\n"
                                   "Verifica tu conexión a internet.")

            version    = data.get("tag_name", "")
            total_size = asset["size"]
            total_mb   = max(total_size // (1024 * 1024), 1)

            # 2. Descargar con progreso real
            self._set_status(f"Descargando {asset['name']} ({total_mb} MB)...", 5)
            tmp_zip = Path(tempfile.gettempdir()) / "drunks_install.zip"
            downloaded = 0
            with urllib.request.urlopen(asset["browser_download_url"], timeout=120) as resp:
                with open(tmp_zip, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = 5 + int(downloaded * 70 / total_size)
                            mb  = downloaded // (1024 * 1024)
                            self._set_status(f"Descargando... {mb} / {total_mb} MB", pct)

            # 3. Extraer
            self._set_status("Extrayendo archivos...", 76)
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(dest)
            tmp_zip.unlink(missing_ok=True)

            # 4. Acceso directo
            if self.make_shortcut.get():
                self._set_status("Creando acceso directo...", 92)
                self._create_shortcut(dest)

            self._set_status(f"Instalación completada  {version}", 100)
            self.root.after(0, self._done, dest, version)

        except Exception as exc:
            self.root.after(0, self._on_error, str(exc))

    def _create_shortcut(self, dest: Path):
        desktop = Path(os.path.expandvars("%USERPROFILE%")) / "Desktop"
        lnk     = str(desktop / "Drunks POS.lnk")
        target  = str(dest / "Drunks.exe")
        wd      = str(dest)
        ps = (
            f"$s=New-Object -ComObject WScript.Shell;"
            f"$l=$s.CreateShortcut('{lnk}');"
            f"$l.TargetPath='{target}';"
            f"$l.WorkingDirectory='{wd}';"
            f"$l.Description='Drunks POS';"
            f"$l.Save()"
        )
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True)

    # ── Pantallas de resultado ────────────────────────────────────────────────
    def _done(self, dest: Path, version: str):
        self.install_btn.configure(state="normal", text="Cerrar",
                                   command=self.root.quit)
        self.cancel_btn.configure(state="disabled")
        if self.open_after.get():
            self._launch(dest)
            self.root.after(2500, self.root.quit)

    def _on_error(self, msg: str):
        self.status_var.set(f"Error: {msg}")
        self.progress["value"] = 0
        self.install_btn.configure(state="normal", text="Reintentar",
                                   command=self._start_install)
        self.cancel_btn.configure(state="normal")

    def _launch(self, dest: Path):
        exe = dest / "Drunks.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(dest))
        else:
            self.status_var.set(f"Instalado, pero no se encontró Drunks.exe en {dest}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    InstallerApp().run()
