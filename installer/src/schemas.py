from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageCreate(BaseModel):
    message_id: int
    chat_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    content: str
    from_bot: bool = False

class MessageResponse(MessageCreate):
    id: int
    created_at: str
    
    class Config:
        from_attributes = True

class ProverbCreate(BaseModel):
    text: str
    added_by: str

class ProverbUpdate(BaseModel):
    text: Optional[str] = None
    is_active: Optional[bool] = None

class ProverbResponse(ProverbCreate):
    id: int
    added_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    is_admin: bool = False

class UserUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_blocked: Optional[bool] = None
    blocked_by: Optional[str] = None

class UserResponse(UserCreate):
    id: int
    created_at: datetime
    is_blocked: bool
    blocked_by: Optional[str] = None
    blocked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True