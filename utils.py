import os
import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Subscription, Payment, Referral

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
REFERRAL_BONUS_POINTS = int(os.getenv("REFERRAL_BONUS_POINTS", "10"))
POINTS_TO_RUBLE_RATIO = int(os.getenv("POINTS_TO_RUBLE_RATIO", "1"))


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


def generate_subscription_key(length: int = 20) -> str:
    """Generate random subscription key"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def format_date(date: datetime) -> str:
    """Format datetime to readable string"""
    return date.strftime("%d.%m.%Y")


def format_datetime(date: datetime) -> str:
    """Format datetime to readable string with time"""
    return date.strftime("%d.%m.%Y %H:%M")


def days_until(date: datetime) -> int:
    """Calculate days until given date"""
    delta = date - datetime.utcnow()
    return max(0, delta.days)


def escape_md(text: str) -> str:
    """Escape special characters for Markdown V2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


# Database utilities
async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str) -> User:
    """Get or create user in database"""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def create_subscription(
    session: AsyncSession,
    telegram_id: int,
    marzneshin_username: str,
    days: int
) -> Subscription:
    """Create subscription for user"""
    expired_at = datetime.utcnow() + timedelta(days=days)
    
    subscription = Subscription(
        telegram_id=telegram_id,
        marzneshin_username=marzneshin_username,
        status='active',
        expired_at=expired_at
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_active_subscription(session: AsyncSession, telegram_id: int) -> Subscription:
    """Get active subscription for user (returns most recent one)"""
    stmt = select(Subscription).where(
        (Subscription.telegram_id == telegram_id) & 
        (Subscription.status == 'active') &
        (Subscription.expired_at > datetime.utcnow())
    ).order_by(Subscription.expired_at.desc()).limit(1)
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def extend_subscription(
    session: AsyncSession,
    subscription: Subscription,
    additional_days: int
) -> Subscription:
    """Extend existing subscription"""
    subscription.expired_at = subscription.expired_at + timedelta(days=additional_days)
    subscription.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def add_points(session: AsyncSession, telegram_id: int, points: int) -> User:
    """Add points to user balance"""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.balance += points
        await session.commit()
        await session.refresh(user)
    
    return user


async def spend_points(session: AsyncSession, telegram_id: int, points: int) -> bool:
    """Spend points from user balance"""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user and user.balance_points >= points:
        user.balance_points -= points
        await session.commit()
        await session.refresh(user)
        return True
    
    return False


async def create_referral(
    session: AsyncSession,
    referrer_telegram_id: int,
    referrer_username: str,
    referred_telegram_id: int,
    referred_username: str
) -> Referral:
    """Create referral record"""
    referral = Referral(
        referrer_telegram_id=referrer_telegram_id,
        referrer_username=referrer_username,
        referred_telegram_id=referred_telegram_id,
        referred_username=referred_username,
        bonus_points=0
    )
    session.add(referral)
    await session.commit()
    await session.refresh(referral)
    return referral


async def activate_referral(session: AsyncSession, referral: Referral) -> Referral:
    """Activate referral when referred user makes first payment"""
    referral.is_active = True
    referral.activated_at = datetime.utcnow()
    referral.bonus_points = REFERRAL_BONUS_POINTS
    
    # Add bonus points to referrer
    await add_points(session, referral.referrer_telegram_id, REFERRAL_BONUS_POINTS)
    
    await session.commit()
    await session.refresh(referral)
    return referral


async def record_payment(
    session: AsyncSession,
    telegram_id: int,
    username: str,
    amount: float,
    payment_method: str,
    subscription_days: int,
    transaction_id: str = None
) -> Payment:
    """Record payment in database"""
    payment = Payment(
        telegram_id=telegram_id,
        username=username,
        amount=amount,
        payment_method=payment_method,
        subscription_days=subscription_days,
        transaction_id=transaction_id,
        status='completed'
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_referral_link(telegram_id: int) -> str:
    """Generate referral link for user"""
    # This will be used in the bot messages
    # Format: t.me/bot_username?start=ref_telegram_id
    return f"Your referral link would be: `t.me/your_bot_username?start=ref_{telegram_id}`"
