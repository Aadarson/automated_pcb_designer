from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.models.user import User

from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("user_id")
    email: str = payload.get("email")
    if user_id is None or email is None:
        raise credentials_exception
    return User(id=user_id, email=email, created_at=datetime.utcnow())

async def get_current_user_optional(token: str = Depends(oauth2_scheme_optional)) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id: str = payload.get("user_id")
    email: str = payload.get("email")
    if user_id is None or email is None:
        return None
    return User(id=user_id, email=email, created_at=datetime.utcnow())
