from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection

planner_router = Router()

# Шаги для добавления блюда
user_states = {}  # Хранение состояний пользователей

@planner_router.message(Command("addmeal"))
async def add_meal_start(message: Message):
    user_states[message.from_user.id] = {"step": "waiting_for_name"}
    await message.answer("Введите название блюда, которое хотите добавить в план питания:")

@planner_router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["step"] == "waiting_for_name")
async def add_meal_name_handler(message: Message):
    user_states[message.from_user.id]["name"] = message.text
    user_states[message.from_user.id]["step"] = "waiting_for_time"

    # Отправляем клавиатуру для выбора времени приема пищи
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Завтрак", callback_data="meal_time:breakfast")
    keyboard.button(text="Обед", callback_data="meal_time:lunch")
    keyboard.button(text="Ужин", callback_data="meal_time:dinner")
    keyboard.adjust(1)
    await message.answer("Выберите время приема пищи:", reply_markup=keyboard.as_markup())

@planner_router.callback_query(lambda callback: callback.data.startswith("meal_time"))
async def add_meal_time_handler(callback: CallbackQuery):
    meal_time = callback.data.split(":")[1]
    user_data = user_states.pop(callback.from_user.id, None)

    if not user_data:
        await callback.message.answer("Ошибка при добавлении блюда. Попробуйте снова.")
        return

    # Сохраняем данные в базу
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO meals (telegram_id, name, meal_time) VALUES (%s, %s, %s)",
            (callback.from_user.id, user_data["name"], meal_time),
        )
        conn.commit()
    conn.close()

    # Вопрос о повторном добавлении блюда
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Да", callback_data="add_meal_again:yes")
    keyboard.button(text="Нет", callback_data="add_meal_again:no")
    keyboard.adjust(2)
    await callback.message.answer(
        f"Блюдо '{user_data['name']}' добавлено в {meal_time}.\nХотите добавить еще блюдо?",
        reply_markup=keyboard.as_markup()
    )

@planner_router.callback_query(lambda callback: callback.data.startswith("add_meal_again"))
async def add_meal_again_handler(callback: CallbackQuery):
    choice = callback.data.split(":")[1]
    if choice == "yes":
        user_states[callback.from_user.id] = {"step": "waiting_for_name"}
        await callback.message.answer("Введите название следующего блюда:")
    else:
        await callback.message.answer("Добавление блюд завершено. Вы можете просмотреть свой план с помощью команды /viewplan.")

@planner_router.message(Command("viewplan"))
async def view_plan_handler(message: Message):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time FROM meals WHERE telegram_id = %s ORDER BY meal_time",
            (message.from_user.id,),
        )
        meals = cursor.fetchall()
    conn.close()

    if not meals:
        await message.answer("Ваш план питания пока пуст. Используйте /addmeal, чтобы добавить блюда.")
        return

    # Группируем блюда по времени приема пищи
    plan = "Ваш план питания:\n\n"
    grouped_meals = {"breakfast": [], "lunch": [], "dinner": []}
    times = {"breakfast": "Завтрак", "lunch": "Обед", "dinner": "Ужин"}

    for meal_name, meal_time in meals:
        grouped_meals[meal_time].append(meal_name)

    # Формируем сообщение с планом питания
    for time_key, meals_list in grouped_meals.items():
        if meals_list:
            plan += f"{times[time_key]}:\n" + ", ".join(meals_list) + "\n\n"

    await message.answer(plan.strip())
