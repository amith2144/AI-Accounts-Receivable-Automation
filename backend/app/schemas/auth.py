from typing import List, Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    role: str = "OPERATOR"
    exp: Optional[int] = None
    type: str = "access"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Operator or administrator username")
    password: str = Field(..., min_length=1, description="Operator secret password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class UserProfile(BaseModel):
    username: str
    role: str
    is_active: bool = True
    permissions: List[str] = Field(default_factory=list)
