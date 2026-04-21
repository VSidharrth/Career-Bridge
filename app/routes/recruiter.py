from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.services.matching import calculate_match_score

router = APIRouter(prefix="/recruiter", tags=["recruiter"])
templates = Jinja2Templates(directory="app/templates")


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
    if user["role"] != "recruiter":
        return RedirectResponse(url="/", status_code=303)

    db = get_db()
    jobs = list(db.jobs.find({"recruiter_id": user["_id"]}).sort("created_at", -1))
    for job in jobs:
        job["_id"] = str(job["_id"])
        job["applicant_count"] = db.applications.count_documents({"job_id": job["_id"]})

    total_jobs = len(jobs)
    active_jobs = sum(1 for j in jobs if j.get("is_active"))
    total_applicants = sum(j["applicant_count"] for j in jobs)

    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("recruiter/dashboard.html", {
        "request": request, "user": user, "jobs": jobs,
        "stats": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applicants": total_applicants
        },
        "msg": msg
    })


@router.get("/post-job")
async def post_job_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "recruiter":
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("recruiter/post_job.html", {
        "request": request, "user": user, "job": None, "editing": False
    })


@router.post("/post-job")
async def post_job(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    title = form.get("title", "").strip()
    company = form.get("company", "").strip()
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    skills = form.get("skills_required", "").strip()
    skills_list = [s.strip().lower() for s in skills.split(",") if s.strip()]

    if not title or not company or not location or not description or not skills_list:
        return RedirectResponse(
            url="/recruiter/dashboard?msg=Please+fill+all+required+fields",
            status_code=303
        )

    job_doc = {
        "recruiter_id": user["_id"],
        "title": title,
        "company": company,
        "location": location,
        "type": form.get("type", "Full-time").strip(),
        "description": description,
        "skills_required": skills_list,
        "salary_range": form.get("salary_range", "").strip(),
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    db = get_db()
    db.jobs.insert_one(job_doc)
    return RedirectResponse(
        url="/recruiter/dashboard?msg=Job+posted+successfully!", status_code=303
    )


@router.get("/edit-job/{job_id}")
async def edit_job_page(request: Request, job_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/recruiter/dashboard?msg=Invalid+job+id", status_code=303)

    job = db.jobs.find_one({"_id": job_obj_id, "recruiter_id": user["_id"]})
    if not job:
        return RedirectResponse(url="/recruiter/dashboard?msg=Job+not+found", status_code=303)

    job["_id"] = str(job["_id"])
    return templates.TemplateResponse("recruiter/post_job.html", {
        "request": request, "user": user, "job": job, "editing": True
    })


@router.post("/edit-job/{job_id}")
async def edit_job(request: Request, job_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    title = form.get("title", "").strip()
    company = form.get("company", "").strip()
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    skills = form.get("skills_required", "").strip()
    skills_list = [s.strip().lower() for s in skills.split(",") if s.strip()]

    if not title or not company or not location or not description or not skills_list:
        return RedirectResponse(
            url="/recruiter/dashboard?msg=Please+fill+all+required+fields",
            status_code=303
        )

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/recruiter/dashboard?msg=Invalid+job+id", status_code=303)

    db.jobs.update_one(
        {"_id": job_obj_id, "recruiter_id": user["_id"]},
        {"$set": {
            "title": title,
            "company": company,
            "location": location,
            "type": form.get("type", "Full-time").strip(),
            "description": description,
            "skills_required": skills_list,
            "salary_range": form.get("salary_range", "").strip(),
        }}
    )
    return RedirectResponse(
        url="/recruiter/dashboard?msg=Job+updated+successfully!", status_code=303
    )


@router.post("/delete-job/{job_id}")
async def delete_job(request: Request, job_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/recruiter/dashboard?msg=Invalid+job+id", status_code=303)

    db.jobs.delete_one({"_id": job_obj_id, "recruiter_id": user["_id"]})
    db.applications.delete_many({"job_id": job_id})
    return RedirectResponse(
        url="/recruiter/dashboard?msg=Job+deleted", status_code=303
    )


@router.get("/applicants/{job_id}")
async def view_applicants(request: Request, job_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(url="/recruiter/dashboard?msg=Invalid+job+id", status_code=303)

    job = db.jobs.find_one({"_id": job_obj_id, "recruiter_id": user["_id"]})
    if not job:
        return RedirectResponse(url="/recruiter/dashboard?msg=Job+not+found", status_code=303)

    job["_id"] = str(job["_id"])
    applications = list(db.applications.find({"job_id": job_id}).sort("applied_at", -1))

    for app in applications:
        app["_id"] = str(app["_id"])
        candidate_id = _to_object_id(app.get("candidate_id", ""))
        candidate = db.users.find_one({"_id": candidate_id}) if candidate_id else None
        profile = db.profiles.find_one({"user_id": app["candidate_id"]})
        app["candidate_name"] = candidate["name"] if candidate else "Unknown"
        app["candidate_email"] = candidate["email"] if candidate else ""
        app["candidate_skills"] = profile.get("skills", []) if profile else []
        app["match_score"] = calculate_match_score(
            app["candidate_skills"], job.get("skills_required", [])
        )

    # Sort by match score
    applications.sort(key=lambda x: x["match_score"], reverse=True)

    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("recruiter/applicants.html", {
        "request": request, "user": user, "job": job,
        "applications": applications, "msg": msg
    })


@router.post("/update-status")
async def update_status(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "recruiter":
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    app_id = form.get("application_id")
    new_status = form.get("status")
    job_id = form.get("job_id")

    if new_status not in ("applied", "shortlisted", "rejected", "hired"):
        return RedirectResponse(
            url=f"/recruiter/applicants/{job_id}?msg=Invalid+status", status_code=303
        )

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    app_obj_id = _to_object_id(app_id)
    if not job_obj_id or not app_obj_id:
        return RedirectResponse(
            url="/recruiter/dashboard?msg=Invalid+request", status_code=303
        )

    job = db.jobs.find_one({"_id": job_obj_id, "recruiter_id": user["_id"]})
    if not job:
        return RedirectResponse(url="/recruiter/dashboard?msg=Job+not+found", status_code=303)

    result = db.applications.update_one(
        {"_id": app_obj_id, "job_id": str(job_obj_id)},
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        return RedirectResponse(
            url=f"/recruiter/applicants/{job_id}?msg=Application+not+found",
            status_code=303
        )

    return RedirectResponse(
        url=f"/recruiter/applicants/{job_id}?msg=Status+updated!", status_code=303
    )
