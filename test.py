from app.utils.jwt_utils import create_jwt

token = create_jwt({
    "user_id": "cron",
    "email": "cron@looplearn.ai",
    "role": "admin"
})

print(token)