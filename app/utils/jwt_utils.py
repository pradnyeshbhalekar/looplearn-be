import jwt
from datetime import datetime, timezone
from app.config.jwt import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRES_IN

def create_jwt(payload: dict):
    payload = payload.copy()
    payload["exp"] = datetime.now(timezone.utc) + JWT_EXPIRES_IN
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

