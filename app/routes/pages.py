from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.auth.dependencies import get_current_user
from app.database import get_db

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request):
    user = get_current_user(request)
    db = get_db()
    stats = {
        "jobs": db.jobs.count_documents({"is_active": True}),
        "candidates": db.users.count_documents({"role": "candidate"}),
        "recruiters": db.users.count_documents({"role": "recruiter"}),
        "applications": db.applications.count_documents({})
    }
    return templates.TemplateResponse("home.html", {
        "request": request, "user": user, "stats": stats
    })
