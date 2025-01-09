from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from .common import planner_router


@planner_router.message(Command("viewingredient"))
async def handle_view_ingredients(message: Message):
    # Получаем все добавленные ингредиенты для текущего пользователя
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT name, weight, protein, fat, carbohydrates 
            FROM ingredients 
            WHERE telegram_id = %s
            """,
            (message.from_user.id,)
        )
        ingredients = cursor.fetchall()

    if not ingredients:
        await message.answer("У вас еще нет добавленных ингредиентов.")
        return

    # Формируем список всех добавленных ингредиентов с БЖУ в столбик
    ingredient_list = "\n".join(
        [
            f"Название: {ingredient[0]}\n"
            f"Вес: {ingredient[1]} г\n"
            f"Белки: {ingredient[2]} г\n"
            f"Жиры: {ingredient[3]} г\n"
            f"Углеводы: {ingredient[4]} г\n"
            f"---"
            for ingredient in ingredients]
    )

    await message.answer(f"Все добавленные ингредиенты:\n{ingredient_list}")
