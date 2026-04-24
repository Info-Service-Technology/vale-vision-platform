from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "P@SSw0r4nd210426"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=8)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)