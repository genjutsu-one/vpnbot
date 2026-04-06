from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    telegram_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32), unique=True, nullable=False)
    subscription_key = Column(String(20), nullable=True)
    balance_points = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(32), nullable=False)
    subscription_key = Column(String(20), unique=True, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    expire_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_telegram_id = Column(Integer, nullable=False, index=True)
    referrer_username = Column(String(32), nullable=False)
    referred_telegram_id = Column(Integer, nullable=False, index=True)
    referred_username = Column(String(32), nullable=False)
    bonus_points = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(32), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(20), nullable=False)  # 'sbp', 'card', 'stars', 'points'
    status = Column(String(20), default='pending')  # 'pending', 'completed', 'failed'
    subscription_days = Column(Integer, nullable=False)
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
