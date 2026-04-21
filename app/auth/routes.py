from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from app.database import get_db
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.config import settings
from app.paths import TEMPLATES_DIR

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login")
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=303)
        return RedirectResponse(url=f"/{user['role']}/dashboard", status_code=303)
    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("auth/login.html", {
        "request": request, "user": None, "msg": msg
    })


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    db = get_db()
    user = db.users.find_one({"email": email})

    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse("auth/login.html", {
            "request": request, "user": None,
            "msg": "Invalid email or password"
        })

    if user.get("blocked"):
        return templates.TemplateResponse("auth/login.html", {
            "request": request, "user": None,
            "msg": "Your account has been blocked. Contact admin."
        })

    token = create_access_token(str(user["_id"]), user["role"])
    if user["role"] == "admin":
        redirect_url = "/admin/dashboard"
    else:
        redirect_url = f"/{user['role']}/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token", value=token,
        httponly=True,
        max_age=settings.TOKEN_EXPIRY_HOURS * 3600,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/"
    )
    return response


@router.get("/register")
async def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url=f"/{user['role']}/dashboard", status_code=303)
    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("auth/register.html", {
        "request": request, "user": None, "msg": msg
    })


@router.post("/register")
async def register(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    role = form.get("role", "candidate")

    if not name or not email or not password:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "user": None,
            "msg": "All fields are required"
        })

    if len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "user": None,
            "msg": "Password must be at least 6 characters"
        })

    if role not in ("candidate", "recruiter"):
        role = "candidate"

    db = get_db()
    if db.users.find_one({"email": email}):
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "user": None,
            "msg": "Email already registered"
        })

    user_doc = {
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "role": role,
        "blocked": False,
        "created_at": datetime.utcnow()
    }
    result = db.users.insert_one(user_doc)

    # Create empty profile for candidates
    if role == "candidate":
        db.profiles.insert_one({
            "user_id": str(result.inserted_id),
            "phone": "",
            "location": "",
            "bio": "",
            "skills": [],
            "resume_path": "",
            "experience": "",
            "education": ""
        })

    return RedirectResponse(
        url="/login?msg=Registration+successful!+Please+login.",
        status_code=303
    )


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
