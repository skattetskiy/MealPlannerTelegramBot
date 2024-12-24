from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

planner_router = Router()

# Some mock data

@planner_router.message(Command("addmeal"))
async def add_meal_handler(message: Message):
    await message.answer("Введите название блюда, которое хотите добавить в план питания:")

@planner_router.message(Command("viewplan"))
async def view_plan_handler(message: Message):
    await message.answer("Ваш план питания на сегодня:\n1. Завтрак: Овсянка\n2. Обед: Суп\n3. Ужин: Паста")