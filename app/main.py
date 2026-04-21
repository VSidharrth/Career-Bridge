from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pymongo.errors import DuplicateKeyError
from app.database import connect_db, close_db, get_db
from app.config import settings
from app.auth.utils import hash_password
from app.paths import STATIC_DIR, UPLOADS_DIR, IS_VERCEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    connect_db()
    # Create default admin if none exists
    db = get_db()
    if not db.users.find_one({"role": "admin"}):
        try:
            db.users.insert_one({
                "email": settings.ADMIN_EMAIL,
                "password_hash": hash_password(settings.ADMIN_PASSWORD),
                "name": "Admin",
                "role": "admin",
                "blocked": False,
                "created_at": datetime.utcnow()
            })
            print(f"[OK] Default admin created: {settings.ADMIN_EMAIL}")
        except DuplicateKeyError:
            print("[WARN] Default admin email already exists, skipping auto-create")
    # On Vercel, project files are read-only. Keep local upload directory creation local-only.
    if not IS_VERCEL:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    close_db()


app = FastAPI(title="CareerBridge", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
from app.auth.routes import router as auth_router
from app.routes.pages import router as pages_router
from app.routes.jobs import router as jobs_router
from app.routes.candidate import router as candidate_router
from app.routes.recruiter import router as recruiter_router
from app.routes.admin import router as admin_router

app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(candidate_router)
app.include_router(recruiter_router)
app.include_router(admin_router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return HTMLResponse(
        content="""
        <html>
        <head><title>404 - Not Found</title>
        <script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-[#0a0a1a] text-white flex items-center justify-center min-h-screen">
            <div class="text-center">
                <h1 class="text-6xl font-bold text-indigo-400 mb-4">404</h1>
                <p class="text-xl text-slate-400 mb-8">Page not found</p>
                <a href="/" class="px-6 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-700 transition">
                    Go Home
                </a>
            </div>
        </body>
        </html>
        """,
        status_code=404
    )
