from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum, ForeignKey, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# --- Служебные таблицы для ИИ-моделей ---

class Model(Base):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)  # polza, gigachat, openai и т.д.
    model_name = Column(String(100), nullable=False)  # имя модели в API
    api_key_var = Column(String(100), nullable=False)  # название переменной окружения
    api_url = Column(String(255), nullable=False)  # URL API
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с ответами
    responses = relationship("AIResponse", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Model(name='{self.name}', provider='{self.provider}')>"


class AIResponse(Base):
    __tablename__ = 'ai_responses'
    
    id = Column(Integer, primary_key=True, index=True)
    proverb_id = Column(Integer, ForeignKey('proverbs.id'), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.utcnow)
    is_cached = Column(Boolean, default=False)
    usage_tokens = Column(Integer, default=0)
    response_time_ms = Column(Integer, default=0)
    
    # Связи
    proverb = relationship("Proverb", back_populates="ai_interpretations")
    model = relationship("Model", back_populates="responses")

    def __repr__(self):
        return f"<AIResponse(model='{self.model.name}', proverb_id={self.proverb_id})>"

# --- Основные таблицы ---

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
    
    # Связь с интерпретациями ИИ
    ai_interpretations = relationship("AIResponse", back_populates="proverb", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proverb(id={self.id}, text='{self.text[:30]}...')>"

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