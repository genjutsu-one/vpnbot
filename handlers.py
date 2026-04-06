from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User as TgUser, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import os
import logging

from keyboards import *
from utils import *
from models import User, Subscription, Referral, Payment
from database import AsyncSessionLocal
from marzneshin_api import MarzneshinAPI, MARZNESHIN_API_URL

logger = logging.getLogger(__name__)

# Initialize routers
user_router = Router()
admin_router = Router()

# Note: is_admin is imported from utils

# FSM States for admin operations
class AdminStates(StatesGroup):
    wait_user_id = State()
    wait_extend_days = State()
    wait_points_amount = State()
    wait_notification_text = State()

# ========== USER MESSAGES ==========

START_MESSAGE = """<b>Добро пожаловать в Legit VPN!</b>

Забудь про «недоступно в вашем регионе» и вечные загрузки. Наш VPN работает даже на парковке!
<blockquote>• Безлимитный трафик
• Максимальная анонимность
• Стабильное соединение</blockquote>

Твой интернет — твои правила."""

TRIAL_STARTED = """<b>Твой тест-драйв Legit VPN начался!</b>

Мы активировали для тебя бесплатный доступ на 3 дня.
Теперь весь интернет в твоем распоряжении без ограничений по скорости!

<code>{}</code>

Приятного пользования!"""

SUBSCRIPTION_MENU = """<b>Выбирай свой тариф Legit VPN</b>

Оплачивая подписку, ты получаешь не просто доступ, а гарантию стабильности:
<blockquote>• Высокая скорость: без лагов при просмотре 4K-видео.
• Конфиденциальность: мы не храним логи твоих действий.
• Любые устройства: одна подписка на телефон, планшет и ПК.
• Поддержка 24/7: всегда поможем, если что-то пойдет не так.</blockquote>

Выбери подходящий период и жми кнопку оплаты ниже:"""

SUBSCRIPTION_ACTIVE = """<b>Твоя подписка Legit VPN активирована!</b>

Теперь все ограничения сняты, а скорость на максимуме.

Статус подписки: активна
Срок действия: до <code>{date}</code>

<code>{key_link}</code>

Спасибо, что выбрали нас!"""

ACCOUNT_INFO = """<b>Твой аккаунт Legit VPN</b>

Ваш ID: <code>{user_id}</code>
Баланс: <code>{balance}Б</code>
Подписка активна до: <code>{date}</code>
Дней до конца подписки: <code>{days_left}</code>"""

REFERRAL_MESSAGE = """<b>Приглашай друзей — пользуйся Legit VPN бесплатно!</b>

За каждого активного приглашенного пользователя мы начисляем <code>10 баллов</code> на твой баланс. Копи баллы и оплачивай ими подписку на любой срок.

<b>Твоя ссылка:</b> <code>{referral_link}</code>

За накрутку — блокировка реферальной программы!"""

KEYS_RESET = """<b>Все устройства удалены!</b>

Ваш новый ключ:
<code>{subscription_link}</code>"""

RESET_WARNING = """<b>Внимание</b>

Это действие удалит доступ на всех ваших текущих устройствах. Вам придется настраивать их заново по новой ссылке.

<b>Вы уверены?</b>"""

ADMIN_START_MESSAGE = """<b>Добро пожаловать в админ-панель Legit VPN!</b>

Вы вошли как администратор системы.

Доступные команды:
<blockquote>
/admin - Администраторская панель
/users - Управление пользователями
/stats - Статистика системы
/notify - Отправить уведомление всем
</blockquote>

Для управления используйте кнопки ниже или введите /admin"""

# ========== USER HANDLERS ==========

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandStart):
    """Start command handler with referral support - different for admins and users"""
    async with AsyncSessionLocal() as session:
        try:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username or str(message.from_user.id))
            
            # Handle referral link
            if command.args and command.args.startswith("ref_"):
                try:
                    referrer_id = int(command.args.replace("ref_", ""))
                    await create_referral(session, message.from_user.id, referrer_id)
                except Exception as e:
                    logger.warning(f"Failed to process referral: {e}")
            
            # Check if user is admin
            is_admin_user = is_admin(message.from_user.id)
            greeting_msg = ADMIN_START_MESSAGE if is_admin_user else START_MESSAGE
            keyboard = get_admin_main_keyboard() if is_admin_user else get_main_keyboard()
            
            await message.answer(greeting_msg, parse_mode="HTML", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("Ошибка при запуске. Попробуйте позже.")

@user_router.message(Command("account"))
async def cmd_account(message: Message):
    """Account command handler"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username or str(message.from_user.id))
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
                text = f"""<b>Твой аккаунт Legit VPN</b>

Ваш ID: <code>{message.from_user.id}</code>
Баланс: <code>{user.balance}Б</code>
Подписка: не активна"""
            
            await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())
            
    except Exception as e:
        logger.error(f"Error in account command: {e}")
        await message.answer("Ошибка при получении информации аккаунта.")

@user_router.message(Command("pay"))
async def cmd_pay(message: Message):
    """Pay command handler"""
    await message.answer(SUBSCRIPTION_MENU, parse_mode="HTML", reply_markup=get_subscription_keyboard())

@user_router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command handler"""
    help_text = """<b>Справка - Legit VPN</b>

Для получения помощи выберите опцию ниже:

<b>VPN не работает:</b>
Контакты поддержки и полезные статьи

<b>Тех.поддержка:</b>
Свяжитесь с нашей командой поддержки"""
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_help_keyboard())

@user_router.message(Command("update_keys"))
async def cmd_update_keys(message: Message):
    """Update keys command handler"""
    await message.answer(RESET_WARNING, parse_mode="HTML", reply_markup=get_reset_confirmation_keyboard())

# ========== TRIAL CALLBACKS ==========

@user_router.callback_query(F.data == "trial_vip")
async def trial_vip(callback: CallbackQuery):
    """Trial VIP subscription"""
    async with AsyncSessionLocal() as session:
        try:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
            
            async with MarzneshinAPI() as api:
                user_data = await api.create_user(callback.from_user.id, subscription_days=3)
                username = user_data.get('username')
                
                await create_subscription(session, callback.from_user.id, username, days=3)
                
                key_link = f"{MARZNESHIN_API_URL}/user/{username}"
                await callback.message.answer(
                    TRIAL_STARTED.format(key_link),
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
        except Exception as e:
            error = str(e)[:80]
            logger.error(f"Trial subscription error: {e}")
            await callback.answer(f"Ошибка: {error}", show_alert=True)

@user_router.callback_query(F.data.startswith("buy_"))
async def buy_subscription(callback: CallbackQuery):
    """Buy subscription"""
    try:
        days = int(callback.data.split("_")[1])
        
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
            
            async with MarzneshinAPI() as api:
                user_data = await api.create_user(callback.from_user.id, subscription_days=days)
                username = user_data.get('username')
                logger.info(f"Created Marzneshin user: {username}")
                
                await create_subscription(session, callback.from_user.id, username, days=days)
                logger.info(f"Subscription created for user {callback.from_user.id}")
                
                key_link = f"{MARZNESHIN_API_URL}/sub/{username}"
                await callback.message.answer(
                    SUBSCRIPTION_ACTIVE.format(
                        date=(datetime.utcnow() + timedelta(days=days)).strftime("%d.%m.%Y"),
                        key_link=key_link
                    ),
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
    except ValueError as e:
        logger.error(f"Invalid days value: {e}")
        await callback.answer(f"Ошибка при обработке подписки", show_alert=True)
    except Exception as e:
        error = str(e)[:80]
        logger.error(f"Buy subscription error: {e}")
        await callback.answer(f"Ошибка: {error}", show_alert=True)

@user_router.callback_query(F.data == "reset_keys_confirm")
async def reset_keys_confirm(callback: CallbackQuery):
    """Confirm reset keys"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
            
            async with MarzneshinAPI() as api:
                # Get old subscription (mark ALL old ones as expired)
                old_subs = await session.execute(
                    select(Subscription).where(Subscription.telegram_id == callback.from_user.id)
                )
                all_old_subs = old_subs.scalars().all()
                
                # Delete all old users from Marzneshin
                for old_sub in all_old_subs:
                    try:
                        logger.info(f"Deleting old user: {old_sub.marzneshin_username}")
                        await api.delete_user(old_sub.marzneshin_username)
                        old_sub.status = "revoked"
                    except Exception as e:
                        logger.warning(f"Failed to delete user {old_sub.marzneshin_username}: {e}")
                        old_sub.status = "revoked"
                
                await session.commit()
                
                # Create new subscription
                user_data = await api.create_user(callback.from_user.id, subscription_days=30)
                username = user_data.get('username')
                logger.info(f"Created new Marzneshin user: {username}")
                
                # Create new DB entry
                await create_subscription(session, callback.from_user.id, username, days=30)
                
                key_link = f"{MARZNESHIN_API_URL}/sub/{username}"
                await callback.message.answer(
                    KEYS_RESET.format(subscription_link=key_link),
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
    except Exception as e:
        logger.error(f"Reset keys error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)

@user_router.callback_query(F.data == "buy_menu")
async def buy_menu(callback: CallbackQuery):
    """Show subscription plans"""
    await callback.message.edit_text(
        SUBSCRIPTION_MENU,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
    )

@user_router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    """Go back to main menu"""
    await callback.message.edit_text(
        START_MESSAGE,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

# ========== ADMIN HANDLERS ==========

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel (only for admins)"""
    if not is_admin(message.from_user.id):
        return  # Silently ignore non-admins
    
    admin_text = """<b>Администраторская панель Legit VPN</b>

Выберите действие:"""
    
    await message.answer(admin_text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())

@admin_router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Admin: Statistics command from Marzneshin API"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        async with MarzneshinAPI() as api:
            stats = await api.get_system_stats()
            
            # Extract stats
            total_users = stats.get("total", 0)
            active_users = stats.get("active", 0)
            online_users = stats.get("online", 0)
            expired_users = stats.get("expired", 0)
            
            text = f"""<b>Статистика системы - Marzneshin</b>

<b>Пользователи:</b>
  Всего: <code>{total_users}</code>
  Активных: <code>{active_users}</code>
  Онлайн: <code>{online_users}</code>
  Истекли: <code>{expired_users}</code>"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="admin_main")]
            ])
            
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await message.answer(f"Ошибка: {str(e)[:80]}")

@admin_router.message(Command("users"))
async def cmd_users(message: Message):
    """Admin: Users management command"""
    if not is_admin(message.from_user.id):
        return
    
    text = """<b>Управление пользователями</b>

Выберите действие:"""
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_users_keyboard())

@admin_router.message(Command("notify"))
async def cmd_notify(message: Message, state: FSMContext):
    """Admin: Notify all users command"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.wait_notification_text)
    
    await message.answer(
        "<b>Отправьте текст уведомления для всех пользователей:</b>",
        parse_mode="HTML"
    )

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Admin: System statistics from Marzneshin API"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        async with MarzneshinAPI() as api:
            stats = await api.get_system_stats()
            
            # Extract stats
            total_users = stats.get("total", 0)
            active_users = stats.get("active", 0)
            online_users = stats.get("online", 0)
            expired_users = stats.get("expired", 0)
            
            text = f"""<b>Статистика системы - Marzneshin</b>

<b>Пользователи:</b>
  Всего: <code>{total_users}</code>
  Активных: <code>{active_users}</code>
  Онлайн: <code>{online_users}</code>
  Истекли: <code>{expired_users}</code>"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="admin_main")]
            ])
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:50]}", show_alert=True)

@admin_router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Admin: Users management menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    text = """<b>Управление пользователями</b>

Выберите действие:"""
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_users_keyboard())

@admin_router.callback_query(F.data == "admin_list_all")
async def admin_list_users(callback: CallbackQuery):
    """Admin: List all users"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            query = select(User).limit(20)
            result = await session.execute(query)
            users = result.scalars().all()
            
            text = """<b>Последние 20 пользователей:</b>\n\n"""
            for u in users:
                text += f"ID: <code>{u.telegram_id}</code> | Баланс: <code>{u.balance}Б</code>\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="admin_users")]
            ])
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)[:80]}", show_alert=True)

@admin_router.callback_query(F.data == "admin_search_user")
async def admin_search_user(callback: CallbackQuery, state: FSMContext):
    """Admin: Search user - send new message and wait for response"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.wait_user_id)
    await state.update_data(search_context="search")
    
    await callback.message.answer(
        "<b>Отправьте Telegram ID пользователя для поиска:</b>",
        parse_mode="HTML"
    )
    await callback.answer("")

@admin_router.message(AdminStates.wait_user_id)
async def admin_search_user_result(message: Message, state: FSMContext):
    """Process user search - parse telegram ID only"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    try:
        # Extract first number as telegram ID (ignore 8-digit suffix)
        user_id = int(message.text)
        data = await state.get_data()
        search_context = data.get("search_context")
        
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await message.answer("Пользователь не найден")
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
Подписка: активна
Username в системе: <code>{sub.marzneshin_username}</code>
Дней осталось: <code>{max(0, days_left)}</code>"""
            
            await message.answer(text, parse_mode="HTML", reply_markup=get_admin_user_actions_keyboard(user_id))
            await state.clear()
            
    except ValueError:
        await message.answer("Введите корректный числовой ID")

@admin_router.callback_query(F.data.startswith("admin_extend_"))
async def admin_extend_user(callback: CallbackQuery, state: FSMContext):
    """Admin: Extend subscription"""
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
    await callback.answer("")

@admin_router.message(AdminStates.wait_extend_days)
async def admin_extend_process(message: Message, state: FSMContext):
    """Process extend subscription"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        days = int(message.text)
        data = await state.get_data()
        user_id = data.get("extend_user_id")
        
        async with AsyncSessionLocal() as session:
            sub = await get_active_subscription(session, user_id)
            
            if not sub:
                await message.answer("Активная подписка не найдена")
                await state.clear()
                return
            
            async with MarzneshinAPI() as api:
                new_expire = sub.expired_at + timedelta(days=days)
                await api.modify_user(sub.marzneshin_username, days)
                logger.info(f"Extended subscription for {sub.marzneshin_username} by {days} days")
                
                sub.expired_at = new_expire
                await session.commit()
            
            await message.answer(
                f"Подписка продлена на <code>{days} дней</code>\n\n"
                f"Новая дата истечения: <code>{new_expire.strftime('%d.%m.%Y')}</code>",
                parse_mode="HTML"
            )
            await state.clear()
            
    except ValueError:
        await message.answer("Введите число")
    except Exception as e:
        logger.error(f"Extend subscription error: {e}")
        await message.answer(f"Ошибка: {str(e)[:80]}")
        await state.clear()

@admin_router.callback_query(F.data.startswith("admin_revoke_"))
async def admin_revoke_subscription(callback: CallbackQuery):
    """Admin: Revoke subscription"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"<b>Вы уверены, что хотите аннулировать подписку пользователя <code>{user_id}</code>?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data=f"admin_revoke_confirm_{user_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data="admin_users")]
        ])
    )

@admin_router.callback_query(F.data.startswith("admin_revoke_confirm_"))
async def admin_revoke_confirm(callback: CallbackQuery):
    """Admin: Confirm revoke subscription"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            sub = await get_active_subscription(session, user_id)
            
            if sub:
                async with MarzneshinAPI() as api:
                    logger.info(f"Deleting Marzneshin user: {sub.marzneshin_username}")
                    await api.delete_user(sub.marzneshin_username)
                
                sub.status = "revoked"
                await session.commit()
            
            await callback.message.edit_text("Подписка аннулирована", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Revoke subscription error: {e}")
        await callback.answer(f"Ошибка: {str(e)[:80]}", show_alert=True)

@admin_router.callback_query(F.data == "admin_create_user")
async def admin_create_user(callback: CallbackQuery, state: FSMContext):
    """Admin: Create new user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.wait_user_id)
    await state.update_data(search_context="create")
    
    await callback.message.answer(
        "<b>Отправьте Telegram ID для создания нового аккаунта:</b>",
        parse_mode="HTML"
    )
    await callback.answer("")

@admin_router.callback_query(F.data == "admin_points")
async def admin_points_menu(callback: CallbackQuery):
    """Admin: Points management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    text = """<b>Начисление баллов</b>

Введите ID пользователя:"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="admin_main")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

@admin_router.callback_query(F.data == "admin_notify")
async def admin_notify_menu(callback: CallbackQuery, state: FSMContext):
    """Admin: Notify all users"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.wait_notification_text)
    
    await callback.message.answer(
        "<b>Отправьте текст уведомления для всех пользователей:</b>",
        parse_mode="HTML"
    )
    await callback.answer("")

@admin_router.message(AdminStates.wait_notification_text)
async def admin_notify_send(message: Message, state: FSMContext):
    """Send notification to all users"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        async with AsyncSessionLocal() as session:
            from aiogram import Bot
            bot = Bot(token=os.getenv("BOT_TOKEN"))
            
            query = select(User)
            result = await session.execute(query)
            users = result.scalars().all()
            logger.info(f"Sending notification to {len(users)} users")
            
            sent = 0
            failed = 0
            
            for user in users:
                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"<b>Уведомление от администрации:</b>\n\n{message.text}",
                        parse_mode="HTML"
                    )
                    sent += 1
                except Exception as e:
                    logger.warning(f"Failed to send notification to {user.telegram_id}: {e}")
                    failed += 1
            
            logger.info(f"Notification sent: {sent} success, {failed} failed")
            
            await message.answer(
                f"Уведомление отправлено\n\n"
                f"✓ Успешно: <code>{sent}</code>\n"
                f"✗ Ошибок: <code>{failed}</code>",
                parse_mode="HTML"
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Notify error: {e}")
        await message.answer(f"Ошибка: {str(e)[:80]}")
        await state.clear()

@admin_router.callback_query(F.data == "admin_main")
async def admin_back_main(callback: CallbackQuery):
    """Admin: Back to main menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    admin_text = """<b>Администраторская панель Legit VPN</b>

Выберите действие:"""
    
    await callback.message.edit_text(admin_text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())

# Default handler for unknown commands
@user_router.message()
async def default_handler(message: Message):
    """Default handler for any other message"""
    pass
