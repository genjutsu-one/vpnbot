from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User as TgUser
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import os
import logging

from keyboards import *
from utils import *
from models import User, Subscription, Referral, Payment
from database import AsyncSessionLocal
from marzneshin_api import MarzneshinAPI, MARZNESHIN_API_URL

logger = logging.getLogger(__name__)

# Initialize router
user_router = Router()
admin_router = Router()

# Messages for users
START_MESSAGE = """**Добро пожаловать в Legit VPN!** 🚀

Забудь про «недоступно в вашем регионе» и вечные загрузки. Наш VPN работает даже на парковке!

> ❯ **Безлимитный трафик**
> ❯ **Максимальная анонимность**
> ❯ **Стабильное соединение**

*Твой интернет — твои правила.*"""

TRIAL_STARTED = """**Твой тест-драйв Legit VPN начался!** 🎉

Мы активировали для тебя бесплатный доступ на `3 дня`.

Теперь весь интернет в твоем распоряжении без ограничений по скорости!

`{}`

Приятного пользования!"""

PAYMENT_MENU = """**Выберите способ оплаты:**"""

SUBSCRIPTION_MENU = """**Выбирай свой тариф Legit VPN** ⚜

> Оплачивая подписку, ты получаешь не просто доступ, а гарантию стабильности:
> ❯ **Высокая скорость:** без лагов при просмотре 4K-видео.
> ❯ **Конфиденциальность:** мы не храним логи твоих действий.
> ❯ **Любые устройства:** одна подписка на телефон, планшет и ПК.
> ❯ **Поддержка 24/7:** всегда поможем, если что-то пойдет не так.

**Выбери подходящий период и жми кнопку оплаты ниже:**"""

SUBSCRIPTION_ACTIVATED = """**Твоя подписка Legit VPN активирована.** Теперь все ограничения сняты, а скорость на максимуме.

**Статус подписки:** Активна
**Срок действия:** до `{date}`

`{link}`

Спасибо, что выбрали нас!"""

ACCOUNT_MESSAGE = """**Ваш ID:** `{telegram_id}`

**Баланс:** {balance}Б
**Подписка активна до:** `{expire_date}`
**Дней до конца подписки:** `{days_left}`"""

UPDATE_KEYS_CONFIRM = """**Внимание❗️**

Это действие удалит доступ на всех ваших текущих устройствах. Вам придется настраивать их заново по новой ссылке.

**Вы уверены?**"""

UPDATE_KEYS_SUCCESS = """**Все устройства удалены.** Ваш новый ключ:

`{}`

Приятного пользования!"""

REFERRAL_MESSAGE = """**Приглашай друзей — пользуйся Legit VPN бесплатно!** 

За каждого активного приглашенного пользователя мы начисляем `10 баллов` на твой баланс. Копи баллы и оплачивай ими подписку на любой срок.

**Твоя ссылка:**
`{}`

**За накрутку — блокировка реферальной программы!**"""

HELP_MESSAGE = """**Выберете нужный пункт меню.**"""

# Handlers for user commands
@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandStart):
    """Start command handler with referral support"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username or str(message.from_user.id))
            
            # Handle referral link
            if command.args and command.args.startswith("ref_"):
                try:
                    referrer_id = int(command.args.replace("ref_", ""))
                    if referrer_id != message.from_user.id:
                        # Check if referral already exists
                        existing_ref = await session.execute(
                            select(Referral).where(
                                (Referral.referrer_telegram_id == referrer_id) &
                                (Referral.referred_telegram_id == message.from_user.id)
                            )
                        )
                        if not existing_ref.scalar_one_or_none():
                            await create_referral(session, referrer_id, str(referrer_id), message.from_user.id, str(message.from_user.id))
                except ValueError:
                    pass
        
        await message.answer(START_MESSAGE, parse_mode="Markdown", reply_markup=get_start_keyboard())
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("❌ Ошибка при инициализации бота. Пожалуйста, попробуйте позже.")


@user_router.message(Command("account"))
async def cmd_account(message: Message):
    """Account command handler"""
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username or str(message.from_user.id))
        subscription = await get_active_subscription(session, message.from_user.id)
        
        if subscription:
            days_left = days_until(subscription.expire_date)
            expire_date = format_date(subscription.expire_date)
        else:
            days_left = 0
            expire_date = "Нет активной подписки"
        
        account_text = ACCOUNT_MESSAGE.format(
            telegram_id=message.from_user.id,
            balance=user.balance_points,
            expire_date=expire_date,
            days_left=days_left
        )
        
        keyboard = get_account_keyboard(subscription is not None)
        await message.answer(account_text, parse_mode="Markdown", reply_markup=keyboard)


@user_router.message(Command("pay"))
async def cmd_pay(message: Message):
    """Pay command handler"""
    await message.answer(PAYMENT_MENU, parse_mode="Markdown", reply_markup=get_payment_method_keyboard())


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command handler"""
    await message.answer(HELP_MESSAGE, parse_mode="Markdown", reply_markup=get_help_keyboard())


@user_router.message(Command("update_keys"))
async def cmd_update_keys(message: Message):
    """Update keys command handler"""
    async with AsyncSessionLocal() as session:
        subscription = await get_active_subscription(session, message.from_user.id)
        
        if not subscription:
            await message.answer("❌ У вас нет активной подписки.")
            return
        
        await message.answer(UPDATE_KEYS_CONFIRM, parse_mode="Markdown", reply_markup=get_update_keys_keyboard())


# Callback handlers
@user_router.callback_query(F.data == "trial_start")
async def trial_start(callback: CallbackQuery):
    """Start trial period"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
            
            async with MarzneshinAPI() as api:
                # Create user in Marzneshin
                user_data = await api.create_user(callback.from_user.id, subscription_days=3)
                username = user_data.get('username')
                
                # Create subscription in database
                subscription = await create_subscription(session, callback.from_user.id, username, days=3)
                
                # Update user subscription key
                user.subscription_key = subscription.subscription_key
                await session.commit()
                
                # Get subscription link
                subscription_link = f"{MARZNESHIN_API_URL}/sub/{username}/{subscription.subscription_key}"
                
                trial_text = TRIAL_STARTED.format(subscription_link)
                await callback.message.edit_text(trial_text, parse_mode="Markdown", reply_markup=get_subscription_confirmation_keyboard())
                
    except Exception as e:
        logger.error(f"Error in trial_start: {e}")
        error_msg = str(e)[:100]  # Limit error message length
        await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)


@user_router.callback_query(F.data == "subscribe_menu")
async def subscribe_menu(callback: CallbackQuery):
    """Show payment methods"""
    await callback.message.edit_text(PAYMENT_MENU, parse_mode="Markdown", reply_markup=get_payment_method_keyboard())


@user_router.callback_query(F.data.in_(["pay_points", "pay_card", "pay_sbp", "pay_stars"]))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    """Select payment method and show subscription plans"""
    try:
        method = callback.data
        await state.update_data(payment_method=method)
        
        await callback.message.edit_text(SUBSCRIPTION_MENU, parse_mode="Markdown", reply_markup=get_subscription_plans_keyboard(method))
    except Exception as e:
        logger.error(f"Error in select_payment_method: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@user_router.callback_query(F.data.startswith("sub_"))
async def process_subscription(callback: CallbackQuery, state: FSMContext):
    """Process subscription purchase"""
    try:
        data = await state.get_data()
        payment_method = data.get("payment_method", "pay_card")
        
        # Parse subscription data
        parts = callback.data.split("_")
        duration_str = parts[1]  # 1m, 3m, etc
        
        duration_map = {"1m": 1, "3m": 3, "6m": 6, "12m": 12}
        months = duration_map.get(duration_str, 1)
        days = months * 30
        
        # Get prices based on duration
        price_map = {
            "1m": 99, "3m": 279, "6m": 579, "12m": 999,
        }
        price = price_map.get(duration_str, 99)
        
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
            
            # Special handling for points payment
            if payment_method == "pay_points":
                if user.balance_points < price:
                    await callback.answer(f"❌ Недостаточно баллов. У вас {user.balance_points}, а нужно {price}", show_alert=True)
                    return
                
                # Spend points
                await spend_points(session, callback.from_user.id, price)
            
            try:
                async with MarzneshinAPI() as api:
                    # Create or update user in Marzneshin
                    existing_sub = await get_active_subscription(session, callback.from_user.id)
                    
                    if existing_sub:
                        # Delete old user
                        try:
                            await api.delete_user(existing_sub.username)
                        except:
                            pass
                        # Mark subscription as inactive
                        existing_sub.is_active = False
                        await session.commit()
                    
                    # Create new user
                    user_data = await api.create_user(callback.from_user.id, subscription_days=days)
                    username = user_data.get('username')
                    
                    # Create new subscription
                    subscription = await create_subscription(session, callback.from_user.id, username, days=days)
                    user.subscription_key = subscription.subscription_key
                    await session.commit()
                    
                    # Record payment
                    await record_payment(session, callback.from_user.id, username, float(price), payment_method, days)
                    
                    # Get subscription link
                    subscription_link = f"{MARZNESHIN_API_URL}/sub/{username}/{subscription.subscription_key}"
                    
                    expire_date = format_date(subscription.expire_date)
                    activation_text = SUBSCRIPTION_ACTIVATED.format(date=expire_date, link=subscription_link)
                    
                    await callback.message.edit_text(activation_text, parse_mode="Markdown", reply_markup=get_subscription_confirmation_keyboard())
                    
            except Exception as e:
                logger.error(f"Error creating subscription: {e}")
                error_text = str(e)[:80]
                await callback.answer(f"❌ Ошибка: {error_text}", show_alert=True)
                return
    except Exception as e:
        logger.error(f"Error in process_subscription: {e}")
        error_text = str(e)[:80]
        await callback.answer(f"❌ Ошибка: {error_text}", show_alert=True)


@user_router.callback_query(F.data == "account")
async def account_callback(callback: CallbackQuery):
    """Account button callback"""
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
        subscription = await get_active_subscription(session, callback.from_user.id)
        
        if subscription:
            days_left = days_until(subscription.expire_date)
            expire_date = format_date(subscription.expire_date)
        else:
            days_left = 0
            expire_date = "Нет активной подписки"
        
        account_text = ACCOUNT_MESSAGE.format(
            telegram_id=callback.from_user.id,
            balance=user.balance_points,
            expire_date=expire_date,
            days_left=days_left
        )
        
        keyboard = get_account_keyboard(subscription is not None)
        await callback.message.edit_text(account_text, parse_mode="Markdown", reply_markup=keyboard)


@user_router.callback_query(F.data == "referral")
async def referral_callback(callback: CallbackQuery):
    """Referral program"""
    referral_link = f"https://t.me/your_bot_username?start=ref_{callback.from_user.id}"
    referral_text = REFERRAL_MESSAGE.format(referral_link)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_account")]
    ])
    
    await callback.message.edit_text(referral_text, parse_mode="Markdown", reply_markup=keyboard)


@user_router.callback_query(F.data == "delete_keys")
async def delete_keys_callback(callback: CallbackQuery):
    """Delete keys from devices"""
    await callback.message.edit_text(UPDATE_KEYS_CONFIRM, parse_mode="Markdown", reply_markup=get_update_keys_keyboard())


@user_router.callback_query(F.data == "confirm_update_keys")
async def confirm_update_keys(callback: CallbackQuery):
    """Confirm update keys"""
    try:
        async with AsyncSessionLocal() as session:
            subscription = await get_active_subscription(session, callback.from_user.id)
            
            if not subscription:
                await callback.answer("❌ Подписка не найдена", show_alert=True)
                return
            
            days_remaining = days_until(subscription.expire_date)
            
            async with MarzneshinAPI() as api:
                # Revoke old subscription
                await api.revoke_user_subscription(subscription.username)
                
                # Create new user
                user_data = await api.create_user(callback.from_user.id, subscription_days=max(1, days_remaining))
                new_username = user_data.get('username')
                
                # Create new subscription
                new_subscription = await create_subscription(session, callback.from_user.id, new_username, days=max(1, days_remaining))
                
                # Update user subscription key
                user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username or str(callback.from_user.id))
                user.subscription_key = new_subscription.subscription_key
                
                # Mark old subscription as inactive
                subscription.is_active = False
                await session.commit()
                
                # Get new subscription link
                subscription_link = f"{MARZNESHIN_API_URL}/sub/{new_username}/{new_subscription.subscription_key}"
                
                update_text = UPDATE_KEYS_SUCCESS.format(subscription_link)
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_account")]
                ])
                
                await callback.message.edit_text(update_text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in confirm_update_keys: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@user_router.callback_query(F.data.in_(["back_to_account", "back_to_start"]))
async def back_buttons(callback: CallbackQuery, state: FSMContext):
    """Back buttons navigation"""
    try:
        if callback.data == "back_to_account":
            await account_callback(callback)
        else:
            await callback.message.edit_text(START_MESSAGE, parse_mode="Markdown", reply_markup=get_start_keyboard())
    except Exception as e:
        logger.error(f"Error in back_buttons: {e}")
        await callback.answer("❌ Ошибка навигации", show_alert=True)


@user_router.callback_query(F.data == "help_menu")
async def help_menu_callback(callback: CallbackQuery):
    """Help menu"""
    await callback.message.edit_text(HELP_MESSAGE, parse_mode="Markdown", reply_markup=get_help_keyboard())


@user_router.callback_query(F.data == "instructions")
async def instructions_callback(callback: CallbackQuery):
    """Instructions (placeholder)"""
    instructions_text = """**📖 Инструкция по использованию VPN**

Инструкция будет добавлена позже."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="account")]
    ])
    
    await callback.message.edit_text(instructions_text, parse_mode="Markdown", reply_markup=keyboard)


@user_router.callback_query(F.data == "help_vpn_broken")
async def help_vpn_broken(callback: CallbackQuery):
    """Help: VPN not working"""
    help_text = """**🔗 VPN не работает**

Статья с решением будет добавлена позже.

Если проблема персистирует, обратитесь в техподдержку."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Техподдержка", url="https://t.me/vpnsakura")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="help_menu")]
    ])
    
    await callback.message.edit_text(help_text, parse_mode="Markdown", reply_markup=keyboard)


@user_router.callback_query(F.data == "stars_unavailable")
async def stars_unavailable(callback: CallbackQuery):
    """Telegram Stars unavailable"""
    await callback.answer("⭐ Telegram Stars будут доступны в ближайщем обновлении", show_alert=True)


# Admin handlers
@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel command"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к администраторской панели.")
        return
    
    admin_text = """**🔧 Администраторская панель Legit VPN**

Выберите действие:"""
    
    await message.answer(admin_text, parse_mode="Markdown", reply_markup=get_admin_main_keyboard())


@admin_router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Admin: Users management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text("**👥 Управление пользователями**", parse_mode="Markdown", reply_markup=get_admin_users_keyboard())


@admin_router.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: CallbackQuery):
    """Admin: List all users"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        async with MarzneshinAPI() as api:
            users = await api.get_users_list(page=1, size=10)
            
            users_list = users.get('items', [])[:5]
            text = "**📋 Список пользователей (последние 5):**\n\n"
            
            for user in users_list:
                text += f"👤 {user.get('username')}\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
            ])
            
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Admin: System statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        async with MarzneshinAPI() as api:
            stats = await api.get_system_stats()
            
            users_stats = stats.get('users', {})
            nodes_stats = stats.get('nodes', {})
            
            text = f"""**📈 Статистика системы**

👥 **Пользователи:**
  • Всего: {users_stats.get('total', 0)}
  • Активных: {users_stats.get('active', 0)}
  • Онлайн: {users_stats.get('online', 0)}

🌐 **Ноды:**
  • Всего: {nodes_stats.get('total', 0)}
  • Здоровые: {nodes_stats.get('healthy', 0)}
  • Нездоровые: {nodes_stats.get('unhealthy', 0)}"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
            ])
            
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    """Admin: View payment statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Get recent payments
            result = await session.execute(
                select(Payment).order_by(Payment.created_at.desc()).limit(5)
            )
            payments = result.scalars().all()
            
            text = "**💰 Последние платежи:**\n\n"
            
            for payment in payments:
                text += f"👤 {payment.username}\n"
                text += f"💵 {payment.amount} ({payment.payment_method})\n"
                text += f"📅 {format_datetime(payment.created_at)}\n"
                text += f"✅ {payment.status}\n\n"
            
            if not payments:
                text = "**💰 Платежи**\n\nНет записей"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
            ])
            
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in admin_payments: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "admin_points")
async def admin_points(callback: CallbackQuery):
    """Admin: Points system"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Get users with maximum points
            result = await session.execute(
                select(User).order_by(User.balance_points.desc()).limit(5)
            )
            users = result.scalars().all()
            
            text = "**📊 Система баллов**\n\n**Топ пользователей по баллам:**\n\n"
            
            for i, user in enumerate(users, 1):
                text += f"{i}. 👤 {user.username}: `{user.balance_points}Б`\n"
            
            if not users:
                text = "**📊 Система баллов**\n\nНет пользователей"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
            ])
            
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in admin_points: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "admin_create_user")
async def admin_create_user(callback: CallbackQuery):
    """Admin: Create new user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "**➕ Создание пользователя**\n\nОтправьте username нового пользователя:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]])
    )


@admin_router.callback_query(F.data == "admin_resync_nodes")
async def admin_resync_nodes(callback: CallbackQuery):
    """Admin: Resync nodes"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer("♻️ Пересинхронизация нодов началась...", show_alert=True)
    
    try:
        async with MarzneshinAPI() as api:
            # Get all inbounds
            response = await api.client.get(
                f"{api.api_url}/api/inbounds",
                headers=api._get_headers()
            )
            response.raise_for_status()
            inbounds = response.json().get('items', [])
            
            for inbound in inbounds:
                node_id = inbound.get('node', {}).get('id')
                if node_id:
                    try:
                        resync_response = await api.client.post(
                            f"{api.api_url}/api/nodes/{node_id}/resync",
                            headers=api._get_headers()
                        )
                        resync_response.raise_for_status()
                    except:
                        pass
        
        await callback.message.edit_text(
            "✅ **Ноды успешно пересинхронизированы!**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_service")]])
        )
        
    except Exception as e:
        logger.error(f"Error in admin_resync_nodes: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    """Admin main menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    admin_text = """**🔧 Администраторская панель Legit VPN**

Выберите действие:"""
    
    await callback.message.edit_text(admin_text, parse_mode="Markdown", reply_markup=get_admin_main_keyboard())


@admin_router.callback_query(F.data == "admin_service")
async def admin_service(callback: CallbackQuery):
    """Admin: Service management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text("**🔧 Управление сервисом**", parse_mode="Markdown", reply_markup=get_admin_service_keyboard())


@user_router.message(F.text.startswith("/"))
async def commands_handler(message: Message):
    """Show command suggestions"""
    if message.text == "/:":
        commands_text = get_command_suggestions()
        await message.answer(f"**💡 Доступные команды:**\n{commands_text}", parse_mode="Markdown")
