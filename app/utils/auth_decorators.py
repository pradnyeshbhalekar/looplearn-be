from functools import wraps
from flask import abort,request
import os
from app.utils.auth_middleware import require_auth


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        # allow CORS preflight
        if request.method == "OPTIONS":
            return "", 200

        user = require_auth()

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
        header = request.headers.get("Authorization")

        expected = f"Bearer {os.getenv('PIPELINE_SECRET')}"
        if not header or header != expected:
            abort(401)

        return fn(*args, **kwargs)

    return wrapper