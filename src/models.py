from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

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


class Model(Base):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    api_key_var = Column(String(100), nullable=False)
    api_url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    responses = relationship("AIResponse", back_populates="model", cascade="all, delete-orphan")


class Proverb(Base):
    __tablename__ = 'proverbs'
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    added_by = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    ai_interpretations = relationship("AIResponse", back_populates="proverb", cascade="all, delete-orphan")
    # comparisons будет добавлено ниже


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
    
    proverb = relationship("Proverb", back_populates="ai_interpretations")
    model = relationship("Model", back_populates="responses")


class Comparison(Base):
    __tablename__ = 'comparisons'

    id = Column(Integer, primary_key=True, index=True)
    proverb_id = Column(Integer, ForeignKey('proverbs.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    result_text = Column(Text, nullable=False)
    model_ids = Column(String, nullable=False)  # например: "1,3,5"
    is_cached = Column(Boolean, default=True)

    proverb = relationship("Proverb", back_populates="comparisons")


# === ДОБАВЛЯЕМ СВЯЗИ ПОСЛЕ ОБЪЯВЛЕНИЯ ВСЕХ МОДЕЛЕЙ ===

# Обновляем Proverb, чтобы он знал про Comparison
Proverb.comparisons = relationship("Comparison", back_populates="proverb", cascade="all, delete-orphan")
