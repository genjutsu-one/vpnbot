from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ========== USER KEYBOARDS ==========

def get_main_keyboard():
    """Main menu - 2 buttons only: Trial + Buy subscription"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пробный период (3 дня)", callback_data="trial_vip")],
        [InlineKeyboardButton(text="Оформить подписку", callback_data="buy_menu")],
    ])


def get_payment_method_keyboard():
    """Payment method selection"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data="pay_sbp")],
        [InlineKeyboardButton(text="Банковские карты", callback_data="pay_card")],
        [InlineKeyboardButton(text="Телеграм Звезды", callback_data="pay_stars")],
        [InlineKeyboardButton(text="Баллы", callback_data="pay_points")],
    ])


def get_subscription_keyboard():
    """Subscription plans for purchase"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц – 99₽", callback_data="buy_sbp_30")],
        [InlineKeyboardButton(text="3 месяца – 279₽", callback_data="buy_sbp_90")],
        [InlineKeyboardButton(text="6 месяцев – 579₽", callback_data="buy_sbp_180")],
        [InlineKeyboardButton(text="12 месяцев – 999₽", callback_data="buy_sbp_365")],
        [InlineKeyboardButton(text="Назад", callback_data="back_payment")],
    ])


def get_subscription_keyboard_points():
    """Subscription plans for purchase with points"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц – 99 Баллов", callback_data="buy_points_30")],
        [InlineKeyboardButton(text="3 месяца – 279 Баллов", callback_data="buy_points_90")],
        [InlineKeyboardButton(text="6 месяцев – 579 Баллов", callback_data="buy_points_180")],
        [InlineKeyboardButton(text="12 месяцев – 999 Баллов", callback_data="buy_points_365")],
        [InlineKeyboardButton(text="Назад", callback_data="back_payment")],
    ])


def get_profile_keyboard(has_active_sub: bool):
    """Profile menu buttons"""
    buttons = [
        [InlineKeyboardButton(text="Продлить подписку" if has_active_sub else "Оформить подписку", 
                            callback_data="buy_menu")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_menu")],
        [InlineKeyboardButton(text="Реферальная система", callback_data="referral_menu")],
    ]
    if has_active_sub:
        buttons.append([InlineKeyboardButton(text="Удалить ключи с устройств", callback_data="reset_keys")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_help_keyboard():
    """Help menu buttons"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="VPN не работает", url="https://t.me/vpnsakura")],
        [InlineKeyboardButton(text="Тех.поддержка", url="https://t.me/vpnsakura")],
        [InlineKeyboardButton(text="Назад", callback_data="back_profile")],
    ])


def get_reset_keys_confirmation_keyboard():
    """Reset keys confirmation"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, удалить", callback_data="reset_keys_confirm")],
        [InlineKeyboardButton(text="Отмена", callback_data="back_profile")],
    ])


def get_subscription_active_keyboard():
    """After subscription is activated"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Инструкция", callback_data="instruction")],
        [InlineKeyboardButton(text="Профиль", callback_data="cmd_account")],
    ])


# ========== ADMIN KEYBOARDS ==========

def get_admin_main_keyboard():
    """Admin main menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="Баллы", callback_data="admin_points")],
        [InlineKeyboardButton(text="Уведомление", callback_data="admin_notify")],
        [InlineKeyboardButton(text="Закрыть", callback_data="admin_close")],
    ])


def get_admin_users_keyboard():
    """Admin users management"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поиск", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="Все пользователи", callback_data="admin_list_all")],
        [InlineKeyboardButton(text="Создать", callback_data="admin_create_user")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_main")],
    ])


def get_admin_user_actions_keyboard(user_id: int):
    """Admin actions for specific user"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продлить", callback_data=f"admin_extend_{user_id}")],
        [InlineKeyboardButton(text="Аннулировать", callback_data=f"admin_revoke_{user_id}")],
        [InlineKeyboardButton(text="Добавить баллы", callback_data=f"admin_add_points_{user_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_users")],
    ])


def get_admin_confirm_keyboard(action: str, user_id: int):
    """Confirmation for admin actions"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"admin_confirm_{action}_{user_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_users")],
    ])
