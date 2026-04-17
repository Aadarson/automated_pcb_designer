from fastapi import APIRouter, Depends
from typing import List
from backend.models.user import User
from backend.auth.jwt_handler import get_current_user

router = APIRouter()

@router.get("/")
async def get_projects(current_user: User = Depends(get_current_user)):
    return []
