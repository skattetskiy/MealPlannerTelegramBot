from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from external_api import search_product, get_product_nutrition

planner_router = Router()
user_states = {}  # Хранение состояний пользователей

@planner_router.message(Command("addmeal"))
async def add_meal_start(message: Message):
    user_states[message.from_user.id] = {"step": "waiting_for_name"}
    await message.answer("Введите название блюда, которое хотите добавить в план питания:")

@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_name")
async def add_meal_name_handler(message: Message):
    user_states[message.from_user.id]["name"] = message.text
    user_states[message.from_user.id]["step"] = "waiting_for_weight"
    await message.answer("Введите вес блюда (в граммах):")

@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_weight")
async def add_meal_weight_handler(message: Message):
    try:
        weight = float(message.text)
        user_states[message.from_user.id]["weight"] = weight
        user_states[message.from_user.id]["step"] = "waiting_for_servings"
        await message.answer("Введите количество приемов пищи:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный вес (число).")

@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_servings")
async def add_meal_servings_handler(message: Message):
    try:
        servings = int(message.text)
        user_states[message.from_user.id]["servings"] = servings
        user_states[message.from_user.id]["step"] = "waiting_for_product"
        await message.answer("Введите название продукта для поиска в базе (например, 'макароны'):")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество (число).")

@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_product")
async def search_product_handler(message: Message):
    products = search_product(message.text)
    if not products:
        await message.answer("Продукты не найдены. Попробуйте еще раз.")
        return

    user_states[message.from_user.id]["products"] = products
    user_states[message.from_user.id]["step"] = "choosing_product"

    keyboard = InlineKeyboardBuilder()
    for product in products:
        keyboard.button(text=product["name"], callback_data=f"product:{product['id']}")
    keyboard.adjust(1)

    await message.answer("Выберите продукт из списка:", reply_markup=keyboard.as_markup())

@planner_router.callback_query(lambda callback: callback.data.startswith("product:"))
async def choose_product_handler(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    nutrition = get_product_nutrition(product_id)
    if not nutrition:
        await callback.message.answer("Ошибка при получении данных продукта. Попробуйте снова.")
        return

    user_data = user_states.pop(callback.from_user.id, None)
    if not user_data:
        await callback.message.answer("Ошибка при добавлении блюда. Попробуйте снова.")
        return

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO meals (telegram_id, name, meal_time, weight, proteins, fats, carbohydrates, servings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                callback.from_user.id,
                user_data["name"],
                user_data.get("meal_time", "breakfast"),
                user_data["weight"],
                nutrition["proteins"],
                nutrition["fats"],
                nutrition["carbohydrates"],
                user_data["servings"],
            )
        )
        conn.commit()
    conn.close()

    await callback.message.answer(
        f"Блюдо '{user_data['name']}' добавлено с данными:\n"
        f"- Вес: {user_data['weight']} г\n"
        f"- Белки: {nutrition['proteins']} г\n"
        f"- Жиры: {nutrition['fats']} г\n"
        f"- Углеводы: {nutrition['carbohydrates']} г\n"
        f"- Количество приемов пищи: {user_data['servings']}."
    )

# Добавление команды для просмотра плана питания
@planner_router.message(Command("viewplan"))
async def view_plan(message: Message):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time, weight, proteins, fats, carbohydrates, servings FROM meals WHERE telegram_id = %s",
            (message.from_user.id,)
        )
        meals = cursor.fetchall()

    if not meals:
        await message.answer("Ваш план питания пуст. Добавьте блюда с помощью команды /addmeal.")
        return

    plan_message = "Ваш план питания:\n"
    for meal in meals:
        plan_message += (
            f"\nБлюдо: {meal[0]}\n"
            f"Время приема пищи: {meal[1]}\n"
            f"Вес: {meal[2]} г\n"
            f"Белки: {meal[3]} г\n"
            f"Жиры: {meal[4]} г\n"
            f"Углеводы: {meal[5]} г\n"
            f"Количество приемов пищи: {meal[6]}\n"
        )

    await message.answer(plan_message)
