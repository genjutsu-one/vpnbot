from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ========== USER KEYBOARDS ==========

def get_main_keyboard():
    """Main menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎉 Пробный период", callback_data="trial_vip"),
            InlineKeyboardButton(text="💳 Подписка", callback_data="buy_menu")
        ],
        [
            InlineKeyboardButton(text="👤 Аккаунт", callback_data="account_menu"),
            InlineKeyboardButton(text="🎁 Реферралы", callback_data="referral_menu")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить ключи", callback_data="reset_keys"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help_menu")
        ]
    ])
    return keyboard

def get_subscription_keyboard():
    """Subscription plans keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 99₽", callback_data="buy_30")],
        [InlineKeyboardButton(text="3 месяца - 279₽", callback_data="buy_90")],
        [InlineKeyboardButton(text="6 месяцев - 579₽", callback_data="buy_180")],
        [InlineKeyboardButton(text="12 месяцев - 999₽", callback_data="buy_365")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
    ])
    return keyboard

def get_reset_confirmation_keyboard():
    """Reset keys confirmation keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, обновить", callback_data="reset_keys_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])
    return keyboard

# ========== ADMIN KEYBOARDS ==========

def get_admin_main_keyboard():
    """Admin main menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Управление юзерами", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Баллы", callback_data="admin_points")],
        [InlineKeyboardButton(text="📢 Уведомление", callback_data="admin_notify")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])
    return keyboard

def get_admin_users_keyboard():
    """Admin users management keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="📋 Все юзеры", callback_data="admin_list_all")],
        [InlineKeyboardButton(text="➕ Создать", callback_data="admin_create_user")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
    ])
    return keyboard

def get_admin_user_actions_keyboard(user_id: int):
    """Admin actions for specific user"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱️ Продлить", callback_data=f"admin_extend_{user_id}")],
        [InlineKeyboardButton(text="🚫 Аннулировать", callback_data=f"admin_revoke_{user_id}")],
        [InlineKeyboardButton(text="💰 Добавить баллы", callback_data=f"admin_add_points_{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
    ])
    return keyboard
