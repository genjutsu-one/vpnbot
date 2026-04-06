from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# User keyboards
def get_start_keyboard():
    """Main start keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎉 Пробный период", callback_data="trial_start"),
            InlineKeyboardButton(text="💳 Оформить подписку", callback_data="subscribe_menu")
        ]
    ])
    return keyboard


def get_payment_method_keyboard():
    """Payment method selection"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Баллы", callback_data="pay_points")],
        [InlineKeyboardButton(text="🏦 Банковские карты", callback_data="pay_card")],
        [InlineKeyboardButton(text="⚡ СБП", callback_data="pay_sbp")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars")]
    ])
    return keyboard


def get_subscription_plans_keyboard(payment_method: str):
    """Subscription plans based on payment method"""
    if payment_method == "pay_points":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц - 99 Б", callback_data="sub_1m_points")],
            [InlineKeyboardButton(text="3 месяца - 279 Б", callback_data="sub_3m_points")],
            [InlineKeyboardButton(text="6 месяцев - 579 Б", callback_data="sub_6m_points")],
            [InlineKeyboardButton(text="12 месяцев - 999 Б", callback_data="sub_12m_points")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="subscribe_menu")]
        ])
    elif payment_method == "pay_card":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц - 99₽", callback_data="sub_1m_card")],
            [InlineKeyboardButton(text="3 месяца - 279₽", callback_data="sub_3m_card")],
            [InlineKeyboardButton(text="6 месяцев - 579₽", callback_data="sub_6m_card")],
            [InlineKeyboardButton(text="12 месяцев - 999₽", callback_data="sub_12m_card")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="subscribe_menu")]
        ])
    elif payment_method == "pay_sbp":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц - 99₽", callback_data="sub_1m_sbp")],
            [InlineKeyboardButton(text="3 месяца - 279₽", callback_data="sub_3m_sbp")],
            [InlineKeyboardButton(text="6 месяцев - 579₽", callback_data="sub_6m_sbp")],
            [InlineKeyboardButton(text="12 месяцев - 999₽", callback_data="sub_12m_sbp")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="subscribe_menu")]
        ])
    else:  # stars
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Пока недоступно", callback_data="stars_unavailable")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="subscribe_menu")]
        ])
    
    return keyboard


def get_account_keyboard(has_active_sub: bool):
    """Account menu keyboard"""
    buttons = [
        InlineKeyboardButton(text="Реферальная система", callback_data="referral"),
    ]
    
    if has_active_sub:
        buttons.append(InlineKeyboardButton(text="📥 Удалить ключи с устройств", callback_data="delete_keys"))
    else:
        buttons.append(InlineKeyboardButton(text="💳 Оформить подписку", callback_data="subscribe_menu"))
    
    buttons.append(InlineKeyboardButton(text="❓Помощь", callback_data="help_menu"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [buttons[0]],
        [buttons[1]],
        [buttons[2]]
    ])
    return keyboard


def get_help_keyboard():
    """Help menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 VPN не работает", callback_data="help_vpn_broken")],
        [InlineKeyboardButton(text="📞 Техподдержка", url="https://t.me/vpnsakura")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_account")]
    ])
    return keyboard


def get_subscription_confirmation_keyboard():
    """After subscription activation"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="account")]
    ])
    return keyboard


def get_update_keys_keyboard():
    """Update keys confirmation"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_update_keys"),
            InlineKeyboardButton(text="❌ Нет", callback_data="back_to_account")
        ]
    ])
    return keyboard


def get_extend_subscription_keyboard():
    """Extend subscription"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscribe_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="start")]
    ])
    return keyboard


def get_trial_keyboard():
    """Trial confirmation keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Активировать", callback_data="confirm_trial"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_start")
        ]
    ])
    return keyboard


# Admin keyboards
def get_admin_main_keyboard():
    """Admin main menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Статистика платежей", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📊 Система баллов", callback_data="admin_points")],
        [InlineKeyboardButton(text="🔧 Сервис", callback_data="admin_service")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")]
    ])
    return keyboard


def get_admin_users_keyboard():
    """Admin users management"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать пользователя", callback_data="admin_create_user")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])
    return keyboard


def get_admin_service_keyboard():
    """Admin service management"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать сервис", callback_data="admin_create_service")],
        [InlineKeyboardButton(text="📋 Список сервисов", callback_data="admin_list_services")],
        [InlineKeyboardButton(text="♻️ Пересинхронизировать ноды", callback_data="admin_resync_nodes")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])
    return keyboard


def get_command_suggestions():
    """Command suggestions for /<"""
    return "/start - Главное меню\n/pay - Оплата\n/update_keys - Обновить ключи\n/account - Аккаунт\n/help - Помощь"
