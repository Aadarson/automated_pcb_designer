from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class User(BaseModel):
    id: UUID
    email: str
    created_at: datetime

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
