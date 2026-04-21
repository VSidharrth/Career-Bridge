from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.database import get_db
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
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
    if user["role"] != "admin":
        return RedirectResponse(url="/", status_code=303)

    db = get_db()

    # Stats
    stats = {
        "total_users": db.users.count_documents({}),
        "candidates": db.users.count_documents({"role": "candidate"}),
        "recruiters": db.users.count_documents({"role": "recruiter"}),
        "total_jobs": db.jobs.count_documents({}),
        "active_jobs": db.jobs.count_documents({"is_active": True}),
        "total_applications": db.applications.count_documents({}),
    }

    # Get filter params
    user_filter = request.query_params.get("user_filter", "all")
    job_filter = request.query_params.get("job_filter", "all")

    # Users list
    user_query = {}
    if user_filter == "candidate":
        user_query["role"] = "candidate"
    elif user_filter == "recruiter":
        user_query["role"] = "recruiter"
    elif user_filter == "blocked":
        user_query["blocked"] = True

    users = list(db.users.find(user_query).sort("created_at", -1).limit(100))
    for u in users:
        u["_id"] = str(u["_id"])

    # Jobs list
    job_query = {}
    if job_filter == "active":
        job_query["is_active"] = True
    elif job_filter == "inactive":
        job_query["is_active"] = False

    jobs = list(db.jobs.find(job_query).sort("created_at", -1).limit(100))
    for j in jobs:
        j["_id"] = str(j["_id"])
        recruiter_id = _to_object_id(j.get("recruiter_id", ""))
        recruiter = db.users.find_one({"_id": recruiter_id}) if recruiter_id else None
        j["recruiter_name"] = recruiter["name"] if recruiter else "Unknown"
        j["applicant_count"] = db.applications.count_documents({"job_id": j["_id"]})

    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user, "stats": stats,
        "users": users, "jobs": jobs, "msg": msg,
        "user_filter": user_filter, "job_filter": job_filter
    })


@router.post("/block-user/{user_id}")
async def block_user(request: Request, user_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    target_obj_id = _to_object_id(user_id)
    if not target_obj_id:
        return RedirectResponse(
            url="/admin/dashboard?msg=Invalid+user+id", status_code=303
        )

    target = db.users.find_one({"_id": target_obj_id})
    if not target:
        return RedirectResponse(
            url="/admin/dashboard?msg=User+not+found", status_code=303
        )

    if target and target["role"] != "admin":
        new_blocked = not target.get("blocked", False)
        db.users.update_one(
            {"_id": target_obj_id},
            {"$set": {"blocked": new_blocked}}
        )
        action = "blocked" if new_blocked else "unblocked"
        return RedirectResponse(
            url=f"/admin/dashboard?msg=User+{action}+successfully", status_code=303
        )

    return RedirectResponse(
        url="/admin/dashboard?msg=Cannot+modify+admin+users", status_code=303
    )


@router.post("/delete-job/{job_id}")
async def delete_job(request: Request, job_id: str):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    job_obj_id = _to_object_id(job_id)
    if not job_obj_id:
        return RedirectResponse(
            url="/admin/dashboard?msg=Invalid+job+id", status_code=303
        )

    result = db.jobs.delete_one({"_id": job_obj_id})
    if result.deleted_count == 0:
        return RedirectResponse(
            url="/admin/dashboard?msg=Job+not+found", status_code=303
        )

    db.applications.delete_many({"job_id": job_id})
    return RedirectResponse(
        url="/admin/dashboard?msg=Job+deleted+successfully", status_code=303
    )
