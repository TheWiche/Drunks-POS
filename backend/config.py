import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
    FRONTEND_DIR = Path(sys._MEIPASS) / "frontend"
else:
    APP_DIR = Path(__file__).parent.parent
    FRONTEND_DIR = APP_DIR / "frontend"

DB_PATH      = str(APP_DIR / "drunks.db")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
HOST         = "0.0.0.0"
PORT         = int(os.getenv("PORT", 8000))
