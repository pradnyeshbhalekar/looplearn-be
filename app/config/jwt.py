import os
from datetime import timedelta
from dotenv import load_dotenv


load_dotenv() 

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_IN = timedelta(days=30)