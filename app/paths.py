import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
TMP_UPLOADS_DIR = Path("/tmp") / "careerbridge_uploads"
IS_VERCEL = bool(os.getenv("VERCEL"))
