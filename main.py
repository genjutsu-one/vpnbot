import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from handlers import user_router, admin_router
from database import init_db

# Load environment variables
load_dotenv()

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


async def set_default_commands(bot: Bot):
    """Set default commands for the bot"""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="account", description="Мой аккаунт"),
        BotCommand(command="pay", description="Оплата"),
        BotCommand(command="update_keys", description="Обновить ключи"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="admin", description="Админ-панель"),
    ]
    
    await bot.set_my_commands(commands, BotCommandScopeDefault())


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
    
    # Set default commands
    await set_default_commands(bot)
    logger.info("Default commands set")
    
    try:
        logger.info("Bot started polling")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
