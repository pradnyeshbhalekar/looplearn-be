from functools import wraps
from flask import abort,request
import os
from app.utils.auth_middleware import require_auth


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(user, *args, **kwargs):

        # allow CORS preflight
        if request.method == "OPTIONS":
            return "", 200

        if user.get("role") != "admin":
            abort(403)

        return fn(user, *args, **kwargs)

    return wrapper


def require_editor(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = require_auth()
        if user["role"] not in ("admin", "editor"):
            abort(403)
        return fn(user, *args, **kwargs)
    return wrapper


def require_pipeline_secret(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization") or ""
        token = header.split("Bearer ", 1)[1].strip() if header.startswith("Bearer ") else None
        allowed = {
            v for v in [
                os.getenv("PIPELINE_SECRET"),
                os.getenv("CRON_SECRET"),
                os.getenv("PIPELINE_TOKEN")
            ] if v
        }
        if not token or (allowed and token not in allowed):
            if request.remote_addr not in ("127.0.0.1", "::1"):
                abort(401)

        return fn(*args, **kwargs)

    return wrapper
