from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    balance = Column(Integer, default=0)  # Баллы
    trial_used = Column(Boolean, default=False)  # Флаг: пробный период использован
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    marzneshin_username = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), default='active')  # 'active', 'expired', 'revoked'
    expired_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_telegram_id = Column(Integer, nullable=False, index=True)
    referrer_username = Column(String(255), nullable=False)
    referred_telegram_id = Column(Integer, nullable=False, index=True, unique=True)
    referred_username = Column(String(255), nullable=False)
    bonus_points = Column(Integer, default=10)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(20), nullable=False)  # 'sbp', 'card', 'points', 'stars'
    status = Column(String(20), default='completed')  # 'completed', 'failed', 'pending'
    subscription_days = Column(Integer, nullable=False)
    transaction_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
