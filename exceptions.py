"""
Exceptions and error handling for the bot
"""

import logging

logger = logging.getLogger(__name__)


class BotException(Exception):
    """Base exception for the bot"""
    pass


class APIException(BotException):
    """API related exceptions"""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class MarzneshinAPIError(APIException):
    """Marzneshin API specific errors"""
    pass


class AuthenticationError(BotException):
    """Authentication errors"""
    pass


class UserNotFoundError(BotException):
    """User not found in database or Marzneshin"""
    pass


class SubscriptionError(BotException):
    """Subscription related errors"""
    pass


class PaymentError(BotException):
    """Payment related errors"""
    pass


def handle_api_error(error: Exception) -> str:
    """
    Handle API errors and return user-friendly message
    """
    error_str = str(error).lower()
    
    if "connection" in error_str or "timeout" in error_str:
        return "Ошибка соединения с сервером. Попробуйте позже."
    
    if "unauthorized" in error_str or "403" in error_str:
        return "Ошибка аутентификации. Проверьте учетные данные."
    
    if "not found" in error_str or "404" in error_str:
        return "Ресурс не найден на сервере."
    
    if "invalid" in error_str:
        return "Неверные данные. Проверьте введенную информацию."
    
    return f"Ошибка: {error_str[:100]}"


def log_error(context: str, error: Exception):
    """
    Log error with context
    """
    logger.error(f"[{context}] {type(error).__name__}: {str(error)}")
