from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram import Bot

from database import get_db_connection

start_router = Router()


@start_router.message(Command("start"))
async def start_handler(message: Message):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Регистрируем пользователя, если его еще нет
        cursor.execute(
            "INSERT INTO users (telegram_id, name) VALUES (%s, %s) ON CONFLICT (telegram_id) DO NOTHING",
            (message.from_user.id, message.from_user.first_name),
        )
        conn.commit()
    conn.close()
    await message.answer("Добро пожаловать в Meal Planner Bot! Введите /help для просмотра доступных команд.")


@start_router.message(Command("help"))
async def help_command_handler(message: Message):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Список доступных команд\n"
        "/addmeal - Добавить блюдо в план питания\n"
        "/viewplan - Посмотреть текущий план питания\n"
    )
    await message.answer(help_text)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Список доступных команд"),
        BotCommand(command="addmeal", description="Добавить блюдо в план питания"),
        BotCommand(command="deletemeal", description="Удалить блюдо из плана питания"),
        BotCommand(command="viewplan", description="Посмотреть текущий план питания"),

    ]
    await bot.set_my_commands(commands)
