import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.models.user import UserCreate, Token, User
from backend.auth.jwt_handler import get_current_user, create_access_token, verify_password, get_password_hash
from backend.core.database import db

router = APIRouter()

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    # Mocked registry
    hashed_pwd = get_password_hash(user_data.password)
    user = User(id=uuid.uuid4(), email=user_data.email, created_at=datetime.utcnow())
    return user

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock DB query
    access_token = create_access_token(data={"user_id": str(uuid.uuid4()), "email": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
