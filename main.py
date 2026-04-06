import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from handlers import user_router, admin_router
from database import init_db
from utils import is_admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

# Get admin IDs
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []


async def set_commands(bot: Bot):
    """Set commands for users and admins with different scopes"""
    
    # Commands for regular users (without /admin)
    user_commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="account", description="Мой аккаунт"),
        BotCommand(command="pay", description="Оплата подписки"),
        BotCommand(command="update_keys", description="Обновить ключи"),
        BotCommand(command="help", description="Справка"),
    ]
    
    # Set commands for regular users (default scope)
    await bot.set_my_commands(user_commands, BotCommandScopeDefault())
    logger.info("User commands set")
    
    # Commands for admins (with additional admin commands)
    admin_commands = [
        BotCommand(command="start", description="Главное меню / Админ-панель"),
        BotCommand(command="admin", description="Администраторская панель"),
        BotCommand(command="stats", description="Статистика системы"),
        BotCommand(command="users", description="Управление пользователями"),
        BotCommand(command="notify", description="Отправить уведомление"),
        BotCommand(command="account", description="Мой аккаунт"),
        BotCommand(command="pay", description="Оплата подписки"),
        BotCommand(command="update_keys", description="Обновить ключи"),
        BotCommand(command="help", description="Справка"),
    ]
    
    # Set commands for each admin individually (overrides default scope)
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, BotCommandScopeChat(chat_id=admin_id))
            logger.info(f"Admin commands set for user {admin_id}")
        except Exception as e:
            logger.warning(f"Failed to set admin commands for {admin_id}: {e}")


async def main():
    """Main bot function"""
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Create bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Include routers
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    # Set commands for users and admins
    await set_commands(bot)
    logger.info("Commands configured")
    
    try:
        logger.info("Bot started polling")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
