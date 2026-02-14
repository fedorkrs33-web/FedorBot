from pydantic import BaseModel
from typing import Optional

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