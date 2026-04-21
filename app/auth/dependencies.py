from fastapi import Request
from bson import ObjectId
from app.auth.utils import decode_access_token
from app.database import get_db


def get_current_user(request: Request):
    """Extract current user from JWT cookie. Returns user dict or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        db = get_db()
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("blocked"):
            return None
        user["_id"] = str(user["_id"])
        return user
    except Exception:
        return None
