from aiogram.types import Message
from aiogram.filters import Command
from database import get_db_connection
from .common import user_states, planner_router


@planner_router.message(Command("removemeal"))
async def remove_meal_start(message: Message):
    user_states[message.from_user.id] = {"step": "waiting_for_meal_name_to_remove"}
    await message.answer("Введите название блюда, которое хотите удалить из плана питания:")


@planner_router.message(
    lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_meal_name_to_remove")
async def remove_meal_handler(message: Message):
    meal_name = message.text
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM meals WHERE telegram_id = %s AND name = %s",
            (message.from_user.id, meal_name)
        )
        conn.commit()
    conn.close()
    await message.answer(f"Блюдо '{meal_name}' удалено из плана питания.")
