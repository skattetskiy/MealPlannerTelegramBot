from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from database import get_db_connection
from .common import user_states, planner_router

# Перевод времени приема пищи
meal_time_translation = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин"
}


@planner_router.message(Command("removemeal"))
async def remove_meal_start(message: Message):
    user_states[message.from_user.id] = {"step": "waiting_for_meal_choice"}

    # Получаем список всех добавленных блюд пользователя с их временем приема пищи
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time FROM meals WHERE telegram_id = %s ORDER BY meal_time",
            (message.from_user.id,)
        )
        meals = cursor.fetchall()

    conn.close()

    if not meals:
        await message.answer("У вас нет добавленных блюд в плане питания.")
        return

    # Формируем список блюд для удаления
    meal_list = "\n".join([f"{meal_time_translation.get(meal[1], meal[1]).capitalize()}: {meal[0]}" for meal in meals])

    # Сохраняем список блюд в состояние
    user_states[message.from_user.id]["meal_list"] = meals

    # Создаем inline клавиатуру с кнопками для удаления блюда
    keyboard = InlineKeyboardMarkup(row_width=1)
    for meal in meals:
        meal_button = InlineKeyboardButton(
            text=f"{meal_time_translation.get(meal[1], meal[1]).capitalize()}: {meal[0]}",
            callback_data=f"remove_meal_{meal[0]}"
        )
        keyboard.add(meal_button)

    await message.answer(
        f"Вот ваши добавленные блюда и их время приема пищи:\n\n{meal_list}\n\nВыберите блюдо для удаления:",
        reply_markup=keyboard
    )


@planner_router.callback_query(lambda callback: callback.data.startswith("remove_meal_"))
async def remove_meal_handler(callback: CallbackQuery):
    meal_name = callback.data[len("remove_meal_"):]

    # Находим соответствующее блюдо в списке
    meals = user_states.get(callback.from_user.id, {}).get("meal_list", [])
    selected_meal = next((meal for meal in meals if meal[0].lower() == meal_name.lower()), None)

    if not selected_meal:
        await callback.message.answer(f"Блюдо с названием '{meal_name}' не найдено. Пожалуйста, выберите из списка.")
        return

    # Удаляем выбранное блюдо из базы данных
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM meals WHERE telegram_id = %s AND name = %s",
            (callback.from_user.id, meal_name)
        )
        conn.commit()
    conn.close()

    await callback.message.answer(f"Блюдо '{meal_name}' удалено из плана питания.")

    # Предложим пользователю удалить еще одно блюдо или вернуться к командам
    keyboard = InlineKeyboardMarkup(row_width=2)
    remove_another_button = InlineKeyboardButton(text="Удалить еще одно блюдо", callback_data="remove_another")
    back_to_commands_button = InlineKeyboardButton(text="Вернуться к командам", callback_data="back_to_commands")
    keyboard.add(remove_another_button, back_to_commands_button)

    await callback.message.answer(
        "Хотите удалить еще одно блюдо?",
        reply_markup=keyboard
    )


@planner_router.callback_query(lambda callback: callback.data == "remove_another")
async def remove_another_meal(callback: CallbackQuery):
    await remove_meal_start(callback.message)


@planner_router.callback_query(lambda callback: callback.data == "back_to_commands")
async def back_to_commands(callback: CallbackQuery):
    await callback.message.answer("Вернулись к доступным командам. Напишите /help для списка доступных команд.")
