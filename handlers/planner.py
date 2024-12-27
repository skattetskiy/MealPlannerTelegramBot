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
    user_states[message.from_user.id]["step"] = "waiting_for_meal_time"

    # Создаём клавиатуру для выбора времени приёма пищи
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Завтрак", callback_data="meal_time:breakfast")
    keyboard.button(text="Обед", callback_data="meal_time:lunch")
    keyboard.button(text="Ужин", callback_data="meal_time:dinner")
    keyboard.adjust(1)

    await message.answer("Выберите время приёма пищи:", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data.startswith("meal_time:"))
async def choose_meal_time_handler(callback: CallbackQuery):
    meal_time = callback.data.split(":")[1]
    user_states[callback.from_user.id]["meal_time"] = meal_time
    user_states[callback.from_user.id]["step"] = "waiting_for_weight"

    await callback.message.answer(f"Вы выбрали {meal_time}. Теперь введите вес блюда (в граммах):")


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
                user_data.get("meal_time"),
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

    # Предложение добавить еще одно блюдо или просмотреть план
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить еще одно блюдо", callback_data="add_another_meal")
    keyboard.button(text="Просмотреть план питания", callback_data="view_plan")
    keyboard.adjust(1)

    await callback.message.answer("Что вы хотите сделать дальше?", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data == "add_another_meal")
async def add_another_meal_handler(callback: CallbackQuery):
    user_states[callback.from_user.id] = {"step": "waiting_for_name"}
    await callback.message.answer("Введите название блюда, которое хотите добавить в план питания:")


# Добавление команды для удаления блюда из плана питания
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

    plan_summary = {}
    response = ""

    for meal in meals:
        meal_name, meal_time, weight, proteins, fats, carbohydrates, servings = meal

        # Формируем ответ по каждому блюду
        meal_details = (
            f"Время приёма пищи: {meal_time}\n"
            f"Блюдо: {meal_name}\n\n"
            f"Вес: {weight} г\n"
            f"Белки: {proteins} г\n"
            f"Жиры: {fats} г\n"
            f"Углеводы: {carbohydrates} г\n"
            f"Количество приемов пищи: {servings}\n\n"
        )

        response += meal_details

        # Суммируем данные по каждому времени приема пищи
        if meal_time not in plan_summary:
            plan_summary[meal_time] = {
                "total_weight": 0,
                "total_proteins": 0,
                "total_fats": 0,
                "total_carbohydrates": 0,
                "total_servings": 0,
                "meal_count": 0,
            }

        plan_summary[meal_time]["total_weight"] += weight * servings
        plan_summary[meal_time]["total_proteins"] += proteins * servings
        plan_summary[meal_time]["total_fats"] += fats * servings
        plan_summary[meal_time]["total_carbohydrates"] += carbohydrates * servings
        plan_summary[meal_time]["total_servings"] += servings
        plan_summary[meal_time]["meal_count"] += 1

    # Добавляем общую информацию по каждому времени приема пищи
    for meal_time, data in plan_summary.items():
        response += f"\n\nОбщий вес приёма пищи ({meal_time}): {data['total_weight']} г"
        response += f"\nОбщий вес белков: {data['total_proteins']} г"
        response += f"\nОбщий вес жиров: {data['total_fats']} г"
        response += f"\nОбщий вес углеводов: {data['total_carbohydrates']} г"
        response += f"\nКоличество приёмов пищи за {meal_time}: {data['meal_count']}"

    await message.answer(response)


@planner_router.callback_query(lambda callback: callback.data == "view_plan")
async def view_plan(callback: CallbackQuery):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time, weight, proteins, fats, carbohydrates, servings FROM meals WHERE telegram_id = %s",
            (callback.from_user.id,)
        )
        meals = cursor.fetchall()

    if not meals:
        await callback.message.answer("Ваш план питания пуст. Добавьте блюда с помощью команды /addmeal.")
        return

    plan_summary = {}
    response = ""

    for meal in meals:
        meal_name, meal_time, weight, proteins, fats, carbohydrates, servings = meal

        # Формируем ответ по каждому блюду
        meal_details = (
            f"Время приёма пищи: {meal_time}\n"
            f"Блюдо: {meal_name}\n\n"
            f"Вес: {weight} г\n"
            f"Белки: {proteins} г\n"
            f"Жиры: {fats} г\n"
            f"Углеводы: {carbohydrates} г\n"
            f"Количество приемов пищи: {servings}\n"
        )

        response += meal_details

        # Суммируем данные по каждому времени приема пищи
        if meal_time not in plan_summary:
            plan_summary[meal_time] = {
                "total_weight": 0,
                "total_proteins": 0,
                "total_fats": 0,
                "total_carbohydrates": 0,
                "total_servings": 0,
                "meal_count": 0,
            }

        plan_summary[meal_time]["total_weight"] += weight * servings
        plan_summary[meal_time]["total_proteins"] += proteins * servings
        plan_summary[meal_time]["total_fats"] += fats * servings
        plan_summary[meal_time]["total_carbohydrates"] += carbohydrates * servings
        plan_summary[meal_time]["total_servings"] += servings
        plan_summary[meal_time]["meal_count"] += 1

    # Добавляем общую информацию по каждому времени приема пищи
    for meal_time, data in plan_summary.items():
        response += f"\n\nОбщий вес приёма пищи ({meal_time}): {data['total_weight']} г"
        response += f"\nОбщий вес белков: {data['total_proteins']} г"
        response += f"\nОбщий вес жиров: {data['total_fats']} г"
        response += f"\nОбщий вес углеводов: {data['total_carbohydrates']} г"
        response += f"\nКоличество приёмов пищи за {meal_time}: {data['meal_count']}"

    await callback.message.answer(response)
