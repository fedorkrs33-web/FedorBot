from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer)
    chat_id = Column(String)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    content = Column(Text)
    from_bot = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)