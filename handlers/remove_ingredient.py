from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from . import help_command_handler
from .common import planner_router


@planner_router.message(Command("removeingredient"))
async def handle_remove_ingredient(message: Message):
    # Получаем все добавленные ингредиенты для текущего пользователя
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name FROM ingredients
            WHERE telegram_id = %s
            """,
            (message.from_user.id,)
        )
        ingredients = cursor.fetchall()

    if not ingredients:
        await message.answer("Список ингредиентов пуст")
        return

    # Формируем список для выбора ингредиента
    keyboard = InlineKeyboardBuilder()
    for ingredient in ingredients:
        keyboard.button(text=ingredient[1], callback_data=f"remove:{ingredient[0]}")
    keyboard.adjust(1)

    await message.answer("Выберите ингредиент для удаления:", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data.startswith("remove:"))
async def handle_ingredient_removal(callback: CallbackQuery):
    ingredient_id = callback.data.split(":")[1]

    # Удаляем выбранный ингредиент из базы данных
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM ingredients WHERE id = %s AND telegram_id = %s
            """,
            (ingredient_id, callback.from_user.id)
        )
        conn.commit()

    conn.close()

    # Запрос о повторном удалении или переходе в /help
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Удалить еще один ингредиент", callback_data="remove_another")
    keyboard.button(text="Перейти в помощь", callback_data="go_to_help")
    keyboard.adjust(1)

    await callback.message.answer(
        f"Ингредиент был успешно удален.\n\nЧто вы хотите сделать дальше?",
        reply_markup=keyboard.as_markup()
    )


@planner_router.callback_query(lambda callback: callback.data == "remove_another")
async def handle_remove_another(callback: CallbackQuery):
    await handle_remove_ingredient(callback.message)


@planner_router.callback_query(lambda callback: callback.data == "go_to_help")
async def handle_go_to_help(callback: CallbackQuery):
    # Отправляем сообщение с инструкциями по использованию бота
    await help_command_handler(callback.message)
