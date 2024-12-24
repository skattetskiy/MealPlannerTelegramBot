from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram import Bot

start_router = Router()

@start_router.message(Command("start"))
async def start_command_handler(message: Message):
    await message.answer("Добро пожаловать в Meal Planner Bot! Введите /help для просмотра доступных команд.")

@start_router.message(Command("help"))
async def help_command_handler(message: Message):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Список доступных команд\n"
        "/addmeal - Добавить блюдо в план питания\n" # TODO: Implement this command
        "/viewplan - Посмотреть текущий план питания" # TODO: Implement this command
    )
    await message.answer(help_text)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Список доступных команд"),
        BotCommand(command="addmeal", description="Добавить блюдо в план питания"),
        BotCommand(command="viewplan", description="Посмотреть текущий план питания"),
    ]
    await bot.set_my_commands(commands)
