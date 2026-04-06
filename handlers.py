"""
Legit VPN Telegram Bot - Main Handlers
Полная переделка под новый спец
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User as TgUser, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScope, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import os
import logging
import secrets
import string

from keyboards import *
from utils import *
from models import User, Subscription, Referral, Payment
from database import AsyncSessionLocal
from marzneshin_api import MarzneshinAPI, MARZNESHIN_API_URL

logger = logging.getLogger(__name__)

# Initialize routers
user_router = Router()
admin_router = Router()

# FSM States
class AdminStates(StatesGroup):
    wait_user_id = State()
    wait_extend_days = State()
    wait_points_amount = State()
    wait_notification_text = State()

# ========== CONFIGURATION ==========

# Админы из .env
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

def is_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    return telegram_id in ADMIN_IDS

# ========== TEXT MESSAGES ==========

START_MESSAGE = """<b>Добро пожаловать в Legit VPN!</b>

Забудь про «недоступно в вашем регионе» и вечные загрузки. Наш VPN работает даже на парковке!

<blockquote>Безлимитный трафик
Максимальная анонимность
Стабильное соединение</blockquote>

<i>Твой интернет — твои правила.</i>"""

TRIAL_SUCCESS = """<b>Твой тест-драйв Legit VPN начался!</b>

Мы активировали для тебя бесплатный доступ на <code>3 дня</code>.

Теперь весь интернет в твоем распоряжении без ограничений по скорости!

<code>{key_link}</code>

Приятного пользования!"""

SUBSCRIPTION_SUCCESS = """<b>Твоя подписка Legit VPN активирована!</b>

Теперь все ограничения сняты, а скорость на максимуме.

Статус подписки: <b>Активна</b>
Срок действия: до <code>{date}</code>

<code>{key_link}</code>

Спасибо, что выбрали нас!"""

ACCOUNT_INFO = """<b>Ваш аккаунт Legit VPN</b>

Ваш ID: <code>{user_id}</code>
Баланс: <code>{balance}Б</code>
Подписка активна до: <code>{date}</code>
Дней до конца подписки: <code>{days_left}</code>"""

ACCOUNT_INFO_NO_SUB = """<b>Ваш аккаунт Legit VPN</b>

Ваш ID: <code>{user_id}</code>
Баланс: <code>{balance}Б</code>
Подписка: <b>Неактивна</b>"""

PAYMENT_METHOD_MESSAGE = """<b>Выберите способ оплаты:</b>"""

SUBSCRIPTION_MENU = """<b>Выбирай свой тариф Legit VPN</b>

Оплачивая подписку, ты получаешь не просто доступ, а гарантию стабильности:

<blockquote>Высокая скорость: без лагов при просмотре 4K-видео.
Конфиденциальность: мы не храним логи твоих действий.
Любые устройства: одна подписка на телефон, планшет и ПК.
Поддержка 24/7: всегда поможем, если что-то пойдет не так.</blockquote>

Выбери подходящий период и жми кнопку оплаты ниже:"""

SUBSCRIPTION_MENU_POINTS = """<b>Выбирай свой тариф Legit VPN</b>

Оплачивая подписку, ты получаешь не просто доступ, а гарантию стабильности:

<blockquote>Высокая скорость: без лагов при просмотре 4K-видео.
Конфиденциальность: мы не храним логи твоих действий.
Любые устройства: одна подписка на телефон, планшет и ПК.
Поддержка 24/7: всегда поможем, если что-то пойдет не так.</blockquote>

Выбери подходящий период и жми кнопку оплаты ниже:"""

REFERRAL_MESSAGE = """<b>Приглашай друзей — пользуйся Legit VPN бесплатно!</b>

За каждого активного приглашенного пользователя мы начисляем <code>10 баллов</code> на твой баланс. Копи баллы и оплачивай ими подписку на любой срок.

<b>Твоя ссылка:</b> <code>{referral_link}</code>

За накрутку — блокировка реферальной программы!"""

RESET_WARNING = """<b>Внимание</b>

Это действие удалит доступ на всех ваших текущих устройствах. Вам придется настраивать их заново по новой ссылке.

Вы уверены?"""

RESET_SUCCESS = """<b>Все устройства удалены!</b>

Ваш новый ключ:

<code>{key_link}</code>

Приятного пользования!"""

HELP_MESSAGE = """<b>Выберете нужный пункт меню:</b>"""

TRIAL_ALREADY_USED = """Вы уже использовали пробный период. Пожалуйста, оформите подписку."""

INSUFFICIENT_POINTS = """У вас недостаточно баллов для этой подписки."""

STARS_UNAVAILABLE = """Оплата через Telegram Stars пока недоступна."""

# ========== ADMIN MESSAGES ==========

ADMIN_START_MESSAGE = """<b>Добро пожаловать в админ-панель Legit VPN!</b>

Вы вошли как администратор системы.

Доступные команды:
<blockquote>
/admin - Администраторская панель
/stats - Статистика системы
/users - Управление пользователями
/notify - Отправить уведомление всем
</blockquote>

Для управления используйте кнопки ниже или введите /admin"""

ADMIN_STATS_MESSAGE = """<b>Статистика системы - Marzneshin</b>

Пользователи:
  Всего: <code>{total}</code>
  Активных: <code>{active}</code>
  Онлайн: <code>{online}</code>
  Истекли: <code>{expired}</code>"""

# ========== USER HANDLERS ==========

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start command - show main menu with admin check"""
    try:
        await state.clear()
        
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        
        # Show different message for admins
        if is_admin(message.from_user.id):
            await message.answer(ADMIN_START_MESSAGE, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
        else:
            await message.answer(START_MESSAGE, parse_mode="HTML", reply_markup=get_main_keyboard())
            
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await message.answer("Ошибка при запуске. Попробуйте позже.")


@user_router.callback_query(F.data == "trial_vip")
async def trial_vip(callback: CallbackQuery):
    """Trial period - 3 days free"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
            
            # Check if already used
            if user.trial_used:
                await callback.answer(TRIAL_ALREADY_USED, show_alert=True)
                return
            
            # Mark as used
            user.trial_used = True
            
            # Create Marzneshin user
            async with MarzneshinAPI() as api:
                user_data = await api.create_user(callback.from_user.id, subscription_days=3)
                marzneshin_username = user_data.get('username')
                
                # Create subscription in DB
                await create_subscription(session, callback.from_user.id, marzneshin_username, days=3)
                await session.commit()
                
                key_link = f"{MARZNESHIN_API_URL}/sub/{marzneshin_username}"
                
                await callback.message.answer(
                    TRIAL_SUCCESS.format(key_link=key_link),
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
    except Exception as e:
        logger.error(f"Trial error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@user_router.callback_query(F.data == "buy_menu")
async def buy_menu(callback: CallbackQuery):
    """Show payment method selection"""
    await callback.message.edit_text(
        PAYMENT_METHOD_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_payment_method_keyboard()
    )


@user_router.callback_query(F.data == "pay_sbp")
async def pay_sbp(callback: CallbackQuery):
    """SBP payment method selected"""
    await callback.message.edit_text(
        SUBSCRIPTION_MENU,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
    )


@user_router.callback_query(F.data == "pay_card")
async def pay_card(callback: CallbackQuery):
    """Card payment method selected"""
    await callback.message.edit_text(
        SUBSCRIPTION_MENU,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
    )


@user_router.callback_query(F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery):
    """Stars payment - not available"""
    await callback.answer(STARS_UNAVAILABLE, show_alert=True)


@user_router.callback_query(F.data == "pay_points")
async def pay_points(callback: CallbackQuery):
    """Points payment method selected"""
    await callback.message.edit_text(
        SUBSCRIPTION_MENU_POINTS,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard_points()
    )


@user_router.callback_query(F.data.startswith("buy_sbp_") | F.data.startswith("buy_points_"))
async def buy_subscription(callback: CallbackQuery):
    """Buy subscription with SBP or Points"""
    try:
        parts = callback.data.split("_")
        method = parts[1]  # 'sbp' or 'points'
        days = int(parts[2])
        
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
            
            # Calculate price
            prices = {30: 99, 90: 279, 180: 579, 365: 999}
            price = prices.get(days, 99)
            
            # Check points if using points payment
            if method == "points":
                if user.balance < price:
                    await callback.answer(INSUFFICIENT_POINTS, show_alert=True)
                    return
                user.balance -= price
            
            # Create Marzneshin user
            async with MarzneshinAPI() as api:
                user_data = await api.create_user(callback.from_user.id, subscription_days=days)
                marzneshin_username = user_data.get('username')
                
                # Create subscription in DB
                await create_subscription(session, callback.from_user.id, marzneshin_username, days=days)
                
                # Record payment
                await session.commit()
                
                payment = Payment(
                    telegram_id=callback.from_user.id,
                    username=user.username or str(callback.from_user.id),
                    amount=price,
                    payment_method=method,
                    status='completed',
                    subscription_days=days
                )
                session.add(payment)
                await session.commit()
                
                expire_date = (datetime.utcnow() + timedelta(days=days)).strftime("%d.%m.%Y")
                key_link = f"{MARZNESHIN_API_URL}/sub/{marzneshin_username}"
                
                await callback.message.edit_text(
                    SUBSCRIPTION_SUCCESS.format(date=expire_date, key_link=key_link),
                    parse_mode="HTML",
                    reply_markup=get_subscription_active_keyboard()
                )
                
    except Exception as e:
        logger.error(f"Buy subscription error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@user_router.callback_query(F.data == "back_payment")
async def back_payment(callback: CallbackQuery):
    """Back to payment method selection"""
    await callback.message.edit_text(
        PAYMENT_METHOD_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_payment_method_keyboard()
    )


@user_router.message(Command("account"))
async def cmd_account(message: Message):
    """Account info"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
            sub = await get_active_subscription(session, message.from_user.id)
            
            if sub:
                days_left = (sub.expired_at - datetime.utcnow()).days
                text = ACCOUNT_INFO.format(
                    user_id=message.from_user.id,
                    balance=user.balance,
                    date=sub.expired_at.strftime("%d.%m.%Y"),
                    days_left=max(0, days_left)
                )
            else:
                text = ACCOUNT_INFO_NO_SUB.format(
                    user_id=message.from_user.id,
                    balance=user.balance
                )
            
            await message.answer(text, parse_mode="HTML", reply_markup=get_profile_keyboard(bool(sub)))
            
    except Exception as e:
        logger.error(f"Account command error: {e}")
        await message.answer("Ошибка при получении информации аккаунта.")


@user_router.callback_query(F.data == "cmd_account")
async def callback_account(callback: CallbackQuery):
    """Account info via callback"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
            sub = await get_active_subscription(session, callback.from_user.id)
            
            if sub:
                days_left = (sub.expired_at - datetime.utcnow()).days
                text = ACCOUNT_INFO.format(
                    user_id=callback.from_user.id,
                    balance=user.balance,
                    date=sub.expired_at.strftime("%d.%m.%Y"),
                    days_left=max(0, days_left)
                )
            else:
                text = ACCOUNT_INFO_NO_SUB.format(
                    user_id=callback.from_user.id,
                    balance=user.balance
                )
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_profile_keyboard(bool(sub)))
            
    except Exception as e:
        logger.error(f"Account callback error: {e}")
        await callback.answer("Ошибка при получении информации аккаунта.", show_alert=True)


@user_router.message(Command("pay"))
async def cmd_pay(message: Message):
    """Start payment process"""
    await message.answer(
        PAYMENT_METHOD_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_payment_method_keyboard()
    )


@user_router.message(Command("update_keys"))
async def cmd_update_keys(message: Message):
    """Update subscription keys"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
            sub = await get_active_subscription(session, message.from_user.id)
            
            if not sub:
                await message.answer("У вас нет активной подписки.")
                return
            
            await message.answer(
                RESET_WARNING,
                parse_mode="HTML",
                reply_markup=get_reset_keys_confirmation_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Update keys error: {e}")
        await message.answer("Ошибка при обновлении ключей.")


@user_router.callback_query(F.data == "reset_keys")
async def reset_keys_button(callback: CallbackQuery):
    """Reset keys via button"""
    try:
        async with AsyncSessionLocal() as session:
            sub = await get_active_subscription(session, callback.from_user.id)
            
            if not sub:
                await callback.answer("У вас нет активной подписки.", show_alert=True)
                return
            
            await callback.message.edit_text(
                RESET_WARNING,
                parse_mode="HTML",
                reply_markup=get_reset_keys_confirmation_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Reset keys button error: {e}")
        await callback.answer("Ошибка.", show_alert=True)


@user_router.callback_query(F.data == "reset_keys_confirm")
async def reset_keys_confirm(callback: CallbackQuery):
    """Confirm reset keys"""
    try:
        async with AsyncSessionLocal() as session:
            # Get all old subscriptions and delete them
            old_subs = await session.execute(
                select(Subscription).where(Subscription.telegram_id == callback.from_user.id)
            )
            old_subs = old_subs.scalars().all()
            
            async with MarzneshinAPI() as api:
                for old_sub in old_subs:
                    try:
                        await api.delete_user(old_sub.marzneshin_username)
                        old_sub.status = "revoked"
                    except Exception as e:
                        logger.warning(f"Failed to delete {old_sub.marzneshin_username}: {e}")
                        old_sub.status = "revoked"
                
                await session.commit()
                
                # Create new subscription for 30 days
                user_data = await api.create_user(callback.from_user.id, subscription_days=30)
                marzneshin_username = user_data.get('username')
                
                await create_subscription(session, callback.from_user.id, marzneshin_username, days=30)
                await session.commit()
                
                key_link = f"{MARZNESHIN_API_URL}/sub/{marzneshin_username}"
                
                await callback.message.edit_text(
                    RESET_SUCCESS.format(key_link=key_link),
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
    except Exception as e:
        logger.error(f"Reset keys confirm error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@user_router.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery):
    """Help menu"""
    await callback.message.edit_text(
        HELP_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_help_keyboard()
    )


@user_router.callback_query(F.data == "back_profile")
async def back_profile(callback: CallbackQuery):
    """Back to profile"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
            sub = await get_active_subscription(session, callback.from_user.id)
            
            if sub:
                days_left = (sub.expired_at - datetime.utcnow()).days
                text = ACCOUNT_INFO.format(
                    user_id=callback.from_user.id,
                    balance=user.balance,
                    date=sub.expired_at.strftime("%d.%m.%Y"),
                    days_left=max(0, days_left)
                )
            else:
                text = ACCOUNT_INFO_NO_SUB.format(
                    user_id=callback.from_user.id,
                    balance=user.balance
                )
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_profile_keyboard(bool(sub)))
            
    except Exception as e:
        logger.error(f"Back to profile error: {e}")


@user_router.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    """Referral menu"""
    try:
        referral_link = await get_referral_link(callback.from_user.id)
        await callback.message.edit_text(
            REFERRAL_MESSAGE.format(referral_link=referral_link),
            parse_mode="HTML",
            reply_markup=get_help_keyboard()  # Back button only
        )
    except Exception as e:
        logger.error(f"Referral error: {e}")
        await callback.answer("Ошибка.", show_alert=True)


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command"""
    await message.answer(
        HELP_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_help_keyboard()
    )


# ========== ADMIN HANDLERS ==========

@admin_router.message(CommandStart())
async def admin_start(message: Message):
    """Admin start"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    
    await message.answer(ADMIN_START_MESSAGE, parse_mode="HTML", reply_markup=get_admin_main_keyboard())


@admin_router.message(Command("admin"))
async def admin_menu(message: Message):
    """Admin menu command"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(ADMIN_START_MESSAGE, parse_mode="HTML", reply_markup=get_admin_main_keyboard())


@admin_router.callback_query(F.data == "admin_main")
async def admin_main_menu(callback: CallbackQuery):
    """Admin main menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        ADMIN_START_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_admin_main_keyboard()
    )


@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Admin statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        async with MarzneshinAPI() as api:
            stats = await api.get_system_stats()
            
            text = ADMIN_STATS_MESSAGE.format(
                total=stats.get('total', 0),
                active=stats.get('active', 0),
                online=stats.get('online', 0),
                expired=stats.get('expired', 0)
            )
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
            
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@admin_router.message(Command("stats"))
async def admin_stats_cmd(message: Message):
    """Admin stats command"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        async with MarzneshinAPI() as api:
            stats = await api.get_system_stats()
            
            text = ADMIN_STATS_MESSAGE.format(
                total=stats.get('total', 0),
                active=stats.get('active', 0),
                online=stats.get('online', 0),
                expired=stats.get('expired', 0)
            )
            
            await message.answer(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
            
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        await message.answer(f"Ошибка: {str(e)[:50]}")


@admin_router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Admin users management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    text = """<b>Управление пользователями</b>

Выберите действие:"""
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_users_keyboard())


@admin_router.message(Command("users"))
async def admin_users_cmd(message: Message):
    """Admin users command"""
    if not is_admin(message.from_user.id):
        return
    
    text = """<b>Управление пользователями</b>

Выберите действие:"""
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_users_keyboard())


@admin_router.callback_query(F.data == "admin_list_all")
async def admin_list_users(callback: CallbackQuery):
    """List all users"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).limit(20))
            users = result.scalars().all()
            
            text = "<b>Последние 20 пользователей:</b>\n\n"
            for u in users:
                text += f"ID: <code>{u.telegram_id}</code> | Баланс: <code>{u.balance}Б</code>\n"
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_users_keyboard())
            
    except Exception as e:
        logger.error(f"List users error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@admin_router.callback_query(F.data == "admin_search_user")
async def admin_search_user(callback: CallbackQuery, state: FSMContext):
    """Search user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.wait_user_id)
    await callback.message.answer("<b>Отправьте Telegram ID пользователя:</b>", parse_mode="HTML")


@admin_router.message(AdminStates.wait_user_id)
async def admin_search_result(message: Message, state: FSMContext):
    """Search result"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        user_id = int(message.text)
        
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await message.answer("Пользователь не найден.")
                await state.clear()
                return
            
            sub = await get_active_subscription(session, user_id)
            
            text = f"""<b>Информация о пользователе</b>

ID: <code>{user.telegram_id}</code>
Username: {user.username or "—"}
Баланс: <code>{user.balance}Б</code>
Присоединился: <code>{user.created_at.strftime('%d.%m.%Y')}</code>"""
            
            if sub:
                days_left = (sub.expired_at - datetime.utcnow()).days
                text += f"""
Подписка: <b>Активна</b>
Username в системе: <code>{sub.marzneshin_username}</code>
Дней осталось: <code>{max(0, days_left)}</code>"""
            
            await message.answer(text, parse_mode="HTML", reply_markup=get_admin_user_actions_keyboard(user.telegram_id))
            await state.clear()
            
    except ValueError:
        await message.answer("Введите корректный числовой ID")
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer(f"Ошибка: {str(e)[:50]}")
        await state.clear()


@admin_router.callback_query(F.data.startswith("admin_extend_"))
async def admin_extend_user(callback: CallbackQuery, state: FSMContext):
    """Extend subscription"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    await state.update_data(extend_user_id=user_id)
    await state.set_state(AdminStates.wait_extend_days)
    
    await callback.message.answer(
        f"<b>На сколько дней продлить подписку пользователю <code>{user_id}</code>?</b>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.wait_extend_days)
async def admin_extend_confirm(message: Message, state: FSMContext):
    """Extend confirmation"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        days = int(message.text)
        data = await state.get_data()
        user_id = data.get('extend_user_id')
        
        async with AsyncSessionLocal() as session:
            sub = await get_active_subscription(session, user_id)
            
            if not sub:
                await message.answer("Активная подписка не найдена")
                await state.clear()
                return
            
            async with MarzneshinAPI() as api:
                await api.modify_user(sub.marzneshin_username, days)
            
            sub.expired_at = sub.expired_at + timedelta(days=days)
            await session.commit()
            
            await message.answer(
                f"<b>Подписка продлена на <code>{days} дней</code></b>\n\n"
                f"Новая дата истечения: <code>{sub.expired_at.strftime('%d.%m.%Y')}</code>",
                parse_mode="HTML"
            )
            await state.clear()
            
    except ValueError:
        await message.answer("Введите число")
    except Exception as e:
        logger.error(f"Extend error: {e}")
        await message.answer(f"Ошибка: {str(e)[:50]}")
        await state.clear()


@admin_router.callback_query(F.data.startswith("admin_revoke_"))
async def admin_revoke_user(callback: CallbackQuery):
    """Revoke subscription"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"<b>Вы уверены, что хотите аннулировать подписку пользователя <code>{user_id}</code>?</b>",
        parse_mode="HTML",
        reply_markup=get_admin_confirm_keyboard("revoke", user_id)
    )


@admin_router.callback_query(F.data.startswith("admin_confirm_revoke_"))
async def admin_revoke_confirm(callback: CallbackQuery):
    """Confirm revoke"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            sub = await get_active_subscription(session, user_id)
            
            if sub:
                async with MarzneshinAPI() as api:
                    await api.delete_user(sub.marzneshin_username)
                
                sub.status = "revoked"
                await session.commit()
            
            await callback.message.edit_text("Подписка аннулирована", parse_mode="HTML", reply_markup=get_admin_users_keyboard())
            
    except Exception as e:
        logger.error(f"Revoke error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)


@admin_router.callback_query(F.data.startswith("admin_add_points_"))
async def admin_add_points(callback: CallbackQuery, state: FSMContext):
    """Add points"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[3])
    await state.update_data(points_user_id=user_id)
    await state.set_state(AdminStates.wait_points_amount)
    
    await callback.message.answer(
        f"<b>Сколько баллов добавить пользователю <code>{user_id}</code>?</b>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.wait_points_amount)
async def admin_points_confirm(message: Message, state: FSMContext):
    """Add points confirmation"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data.get('points_user_id')
        
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await message.answer("Пользователь не найден")
                await state.clear()
                return
            
            user.balance += amount
            await session.commit()
            
            await message.answer(
                f"<b>Пользователю <code>{user_id}</code> добавлено <code>{amount}</code> баллов</b>\n\n"
                f"Новый баланс: <code>{user.balance}Б</code>",
                parse_mode="HTML"
            )
            await state.clear()
            
    except ValueError:
        await message.answer("Введите число")
    except Exception as e:
        logger.error(f"Add points error: {e}")
        await message.answer(f"Ошибка: {str(e)[:50]}")
        await state.clear()


@admin_router.callback_query(F.data == "admin_notify")
async def admin_notify_menu(callback: CallbackQuery, state: FSMContext):
    """Notify menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.wait_notification_text)
    await callback.message.answer("<b>Отправьте текст уведомления для всех пользователей:</b>", parse_mode="HTML")


@admin_router.message(AdminStates.wait_notification_text)
async def admin_send_notification(message: Message, state: FSMContext):
    """Send notification"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            sent = 0
            failed = 0
            
            for user in users:
                try:
                    await message.bot.send_message(
                        user.telegram_id,
                        f"<b>Уведомление от администрации:</b>\n\n{message.text}",
                        parse_mode="HTML"
                    )
                    sent += 1
                except Exception as e:
                    logger.warning(f"Failed to send to {user.telegram_id}: {e}")
                    failed += 1
            
            await message.answer(
                f"<b>Уведомление отправлено</b>\n\n"
                f"Успешно: <code>{sent}</code>\n"
                f"Ошибок: <code>{failed}</code>",
                parse_mode="HTML"
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Notification error: {e}")
        await message.answer(f"Ошибка: {str(e)[:50]}")
        await state.clear()


@admin_router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    """Close admin panel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.message.delete()
