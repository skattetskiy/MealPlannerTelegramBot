from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from .common import user_states, planner_router
from handlers.start import help_command_handler


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

    # Сохраняем список блюд в состояние
    user_states[message.from_user.id]["meal_list"] = meals

    # Создаем InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки с блюдами
    for meal in meals:
        meal_name = meal[0]
        meal_time = meal_time_translation.get(meal[1], meal[1]).capitalize()
        builder.add(InlineKeyboardButton(text=f"{meal_time}: {meal_name}", callback_data=f"remove_meal:{meal_name}"))

    # Разделяем кнопки на строки
    builder.adjust(1)

    # Получаем клавиатуру
    keyboard = builder.as_markup()

    await message.answer(
        "Вот ваши добавленные блюда и их время приема пищи:\n\nВыберите блюдо для удаления:",
        reply_markup=keyboard
    )


@planner_router.callback_query(lambda callback: callback.data.startswith("remove_meal:"))
async def remove_meal_handler(callback: CallbackQuery):
    meal_name = callback.data.split(":")[1]
    meals = user_states.get(callback.from_user.id, {}).get("meal_list", [])

    # Проверка на наличие выбранного блюда
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

    # Перепроверяем, есть ли оставшиеся блюда
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time FROM meals WHERE telegram_id = %s ORDER BY meal_time",
            (callback.from_user.id,)
        )
        meals = cursor.fetchall()

    conn.close()

    # Обновляем список блюд в состоянии
    user_states[callback.from_user.id]["meal_list"] = meals

    # Если блюда остались, предложим удалить еще одно
    if meals:
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="Удалить еще одно блюдо", callback_data="remove_more_meals"),
            InlineKeyboardButton(text="Перейти в помощь", callback_data="go_to_help")
        )
        builder.adjust(1)  # Разделение кнопок на строки

        keyboard = builder.as_markup()

        await callback.message.answer(
            f"Блюдо было успешно удалено.\n\nЧто вы хотите сделать дальше?",
            reply_markup=keyboard
        )
    else:
        # Если блюд больше нет, сообщаем об этом
        await callback.message.answer("У вас больше нет добавленных блюд в плане питания.")

    # Сброс шага состояния, чтобы предотвратить дальнейшие действия с текущим шагом
    user_states[callback.from_user.id]["step"] = "waiting_for_meal_choice"


@planner_router.callback_query(lambda callback: callback.data == "remove_more_meals")
async def remove_more_meals_handler(callback: CallbackQuery):
    # Перезапускаем процесс удаления блюд, выводя список снова
    await remove_meal_start(callback.message)


@planner_router.callback_query(lambda callback: callback.data == "go_to_help")
async def go_to_help_handler(callback: CallbackQuery):
    # Возвращаем пользователя к основным командам
    await help_command_handler(callback.message)


# Перевод времени приема пищи
meal_time_translation = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин"
}
