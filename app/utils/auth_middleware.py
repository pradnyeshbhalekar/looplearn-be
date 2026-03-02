from flask import request, abort
from app.utils.jwt_utils import decode_jwt
from app.models.user import get_user_by_id

def require_auth():
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        abort(401)

    token = header.split(" ")[1]

    try:
        payload = decode_jwt(token)
    except Exception:
        abort(401)

    user_id = payload.get("user_id")
    if not user_id:
        abort(401)

    user = get_user_by_id(user_id)
    if not user:
        abort(401)

    return {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }