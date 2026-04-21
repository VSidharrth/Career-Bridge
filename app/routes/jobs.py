from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.services.matching import get_matched_jobs, calculate_match_score
from app.paths import TEMPLATES_DIR

router = APIRouter(tags=["jobs"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _to_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None


@router.get("/jobs")
async def jobs_list(request: Request):
    user = get_current_user(request)
    db = get_db()

    # Get query parameters
    search = request.query_params.get("search", "").strip()
    location = request.query_params.get("location", "").strip()
    job_type = request.query_params.get("type", "").strip()

    # Build query
    query = {"is_active": True}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"skills_required": {"$regex": search, "$options": "i"}}
        ]
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if job_type:
        query["type"] = job_type

    jobs = list(db.jobs.find(query).sort("created_at", -1))
    for job in jobs:
        job["_id"] = str(job["_id"])
        # Get recruiter name
        recruiter_id = _to_object_id(job.get("recruiter_id", ""))
        recruiter = db.users.find_one({"_id": recruiter_id}) if recruiter_id else None
        job["recruiter_name"] = recruiter["name"] if recruiter else "Unknown"

    # If candidate, add match scores
    if user and user["role"] == "candidate":
        profile = db.profiles.find_one({"user_id": user["_id"]})
        candidate_skills = profile.get("skills", []) if profile else []
        jobs = get_matched_jobs(candidate_skills, jobs)

    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("jobs/list.html", {
        "request": request, "user": user, "jobs": jobs,
        "search": search, "location": location, "job_type": job_type,
        "msg": msg
    })


@router.get("/jobs/{job_id}")
async def job_detail(request: Request, job_id: str):
    user = get_current_user(request)
    db = get_db()

    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/jobs?msg=Job+not+found", status_code=303)

    job = db.jobs.find_one({"_id": job_obj_id, "is_active": True})

    if not job:
        return RedirectResponse(url="/jobs?msg=Job+not+found", status_code=303)

    job["_id"] = str(job["_id"])
    recruiter_id = _to_object_id(job.get("recruiter_id", ""))
    recruiter = db.users.find_one({"_id": recruiter_id}) if recruiter_id else None
    job["recruiter_name"] = recruiter["name"] if recruiter else "Unknown"

    # Check if candidate already applied
    already_applied = False
    match_score = 0
    if user and user["role"] == "candidate":
        existing = db.applications.find_one({
            "job_id": job_id, "candidate_id": user["_id"]
        })
        already_applied = existing is not None
        profile = db.profiles.find_one({"user_id": user["_id"]})
        if profile:
            match_score = calculate_match_score(
                profile.get("skills", []), job.get("skills_required", [])
            )

    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("jobs/detail.html", {
        "request": request, "user": user, "job": job,
        "already_applied": already_applied, "match_score": match_score,
        "msg": msg
    })


@router.post("/jobs/{job_id}/apply")
async def apply_job(request: Request, job_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login?msg=Please+login+first", status_code=303)
    if user["role"] != "candidate":
        return RedirectResponse(url="/jobs?msg=Only+candidates+can+apply", status_code=303)

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/jobs?msg=Job+not+found", status_code=303)

    job = db.jobs.find_one({"_id": job_obj_id, "is_active": True})
    if not job:
        return RedirectResponse(url="/jobs?msg=Job+not+available", status_code=303)

    # Check if already applied
    existing = db.applications.find_one({
        "job_id": job_id, "candidate_id": user["_id"]
    })
    if existing:
        return RedirectResponse(
            url=f"/jobs/{job_id}?msg=Already+applied", status_code=303
        )

    form = await request.form()
    cover_letter = form.get("cover_letter", "")

    # Get candidate profile for resume
    profile = db.profiles.find_one({"user_id": user["_id"]})
    resume_path = profile.get("resume_path", "") if profile else ""

    application = {
        "job_id": job_id,
        "candidate_id": user["_id"],
        "resume_path": resume_path,
        "cover_letter": cover_letter,
        "status": "applied",
        "applied_at": datetime.utcnow()
    }
    db.applications.insert_one(application)

    return RedirectResponse(
        url=f"/jobs/{job_id}?msg=Application+submitted+successfully!",
        status_code=303
    )
