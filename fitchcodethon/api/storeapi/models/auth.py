from datetime import datetime, timedelta
from jose import jwt
from storeapi.config import config

def create_access_token(data: dict):
    to_encode = data.copy()
    # Corrected: Use datetime.utcnow() to get the current time
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt
