import asyncio
from aiogram import Bot, Dispatcher
from config import API_TOKEN
from handlers.planner import planner_router
from handlers.start import start_router, set_bot_commands
from database import init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(planner_router)

async def main():
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("База данных инициализирована.")

    logger.info("Установка команд бота...")
    await set_bot_commands(bot)
    logger.info("Команды установлены.")

    logger.info("Запуск бота...")
    await dp.start_polling(bot)
    logger.info("Бот запущен и начинает обработку сообщений.")

if __name__ == "__main__":
    asyncio.run(main())
