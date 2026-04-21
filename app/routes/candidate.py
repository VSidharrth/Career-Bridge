import os
import uuid
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.services.resume_parser import extract_skills
from app.services.matching import get_matched_jobs
from app.config import settings

router = APIRouter(prefix="/candidate", tags=["candidate"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = os.path.join("app", "static", "uploads")


def _to_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None


@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?msg=Please+login+first", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/", status_code=303)

    db = get_db()
    profile = db.profiles.find_one({"user_id": user["_id"]})
    candidate_skills = profile.get("skills", []) if profile else []

    # Get application stats
    total_apps = db.applications.count_documents({"candidate_id": user["_id"]})
    shortlisted = db.applications.count_documents({
        "candidate_id": user["_id"], "status": "shortlisted"
    })
    hired = db.applications.count_documents({
        "candidate_id": user["_id"], "status": "hired"
    })

    # Get top matched jobs
    active_jobs = list(db.jobs.find({"is_active": True}).limit(50))
    for j in active_jobs:
        j["_id"] = str(j["_id"])
    matched_jobs = get_matched_jobs(candidate_skills, active_jobs)[:6]

    # Recent applications
    recent_apps = list(
        db.applications.find({"candidate_id": user["_id"]})
        .sort("applied_at", -1).limit(5)
    )
    for app in recent_apps:
        app["_id"] = str(app["_id"])
        job_obj_id = _to_object_id(app.get("job_id", ""))
        job = db.jobs.find_one({"_id": job_obj_id}) if job_obj_id else None
        app["job_title"] = job["title"] if job else "Deleted Job"
        app["company"] = job.get("company", "") if job else ""

    return templates.TemplateResponse("candidate/dashboard.html", {
        "request": request, "user": user, "profile": profile,
        "stats": {"total": total_apps, "shortlisted": shortlisted, "hired": hired},
        "matched_jobs": matched_jobs, "recent_apps": recent_apps
    })


@router.get("/profile")
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?msg=Please+login+first", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/", status_code=303)

    db = get_db()
    profile = db.profiles.find_one({"user_id": user["_id"]})
    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("candidate/profile.html", {
        "request": request, "user": user, "profile": profile, "msg": msg
    })


@router.post("/profile")
async def update_profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/", status_code=303)

    form = await request.form()
    db = get_db()

    update_data = {
        "phone": form.get("phone", "").strip(),
        "location": form.get("location", "").strip(),
        "bio": form.get("bio", "").strip(),
        "experience": form.get("experience", "").strip(),
        "education": form.get("education", "").strip(),
    }

    # Handle manual skills input
    skills_input = form.get("skills", "").strip()
    if skills_input:
        manual_skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
        # Merge with existing extracted skills
        profile = db.profiles.find_one({"user_id": user["_id"]})
        existing = set(profile.get("skills", [])) if profile else set()
        existing.update(manual_skills)
        update_data["skills"] = sorted(list(existing))

    db.profiles.update_one(
        {"user_id": user["_id"]},
        {"$set": update_data},
        upsert=True
    )
    return RedirectResponse(
        url="/candidate/profile?msg=Profile+updated+successfully!", status_code=303
    )


@router.post("/resume")
async def upload_resume(request: Request, resume: UploadFile = File(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/", status_code=303)

    # Validate file
    if not resume.filename:
        return RedirectResponse(
            url="/candidate/profile?msg=No+file+selected", status_code=303
        )

    ext = os.path.splitext(resume.filename)[1].lower()
    if ext not in (".pdf", ".docx"):
        return RedirectResponse(
            url="/candidate/profile?msg=Only+PDF+and+DOCX+files+allowed",
            status_code=303
        )

    content = await resume.read()
    if len(content) > settings.MAX_FILE_SIZE:
        return RedirectResponse(
            url="/candidate/profile?msg=File+too+large+(max+10MB)",
            status_code=303
        )

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{user['_id']}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract skills
    skills = extract_skills(file_path)

    db = get_db()
    # Merge with existing skills
    profile = db.profiles.find_one({"user_id": user["_id"]})
    existing_skills = set(profile.get("skills", [])) if profile else set()
    existing_skills.update(skills)

    db.profiles.update_one(
        {"user_id": user["_id"]},
        {"$set": {
            "resume_path": f"/static/uploads/{filename}",
            "skills": sorted(list(existing_skills))
        }},
        upsert=True
    )

    skill_count = len(skills)
    return RedirectResponse(
        url=f"/candidate/profile?msg=Resume+uploaded!+{skill_count}+skills+extracted.",
        status_code=303
    )


@router.get("/applications")
async def applications_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?msg=Please+login+first", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/", status_code=303)

    db = get_db()
    apps = list(
        db.applications.find({"candidate_id": user["_id"]})
        .sort("applied_at", -1)
    )
    for app in apps:
        app["_id"] = str(app["_id"])
        job_obj_id = _to_object_id(app.get("job_id", ""))
        job = db.jobs.find_one({"_id": job_obj_id}) if job_obj_id else None
        if job:
            app["job_title"] = job["title"]
            app["company"] = job.get("company", "")
            app["location"] = job.get("location", "")
            app["type"] = job.get("type", "")
        else:
            app["job_title"] = "Deleted Job"
            app["company"] = ""
            app["location"] = ""
            app["type"] = ""

    return templates.TemplateResponse("candidate/applications.html", {
        "request": request, "user": user, "applications": apps
    })
