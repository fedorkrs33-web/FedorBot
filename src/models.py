from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum
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

class Proverb(Base):
    __tablename__ = 'proverbs'
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    added_by = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    blocked_by = Column(String, nullable=True)
    blocked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)