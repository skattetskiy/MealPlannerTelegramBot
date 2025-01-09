from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from external_api import search_meals, get_meal_nutrition, get_meal_details
from .common import user_states, planner_router


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
async def add_meal_time_handler(callback: CallbackQuery):
    meal_time = callback.data.split(":")[1]
    user_states[callback.from_user.id]["meal_time"] = meal_time
    user_states[callback.from_user.id]["step"] = "waiting_for_meal_type"

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить блюдо из базы", callback_data="meal_type:full_meal")
    keyboard.button(text="Составить блюдо из ингредиентов", callback_data="meal_type:ingredients")
    keyboard.adjust(1)

    await callback.message.answer("Выберите тип блюда:", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data.startswith("meal_type:"))
async def choose_meal_type(callback: CallbackQuery):
    meal_type = callback.data.split(":")[1]
    if meal_type == "full_meal":
        user_states[callback.from_user.id]["step"] = "waiting_for_full_meal_name"
        await callback.message.answer("Введите название блюда для поиска в базе (например, 'суп'): ")
    elif meal_type == "ingredients":
        user_states[callback.from_user.id]["step"] = "waiting_for_ingredient_name"
        await choose_ingredient_handler(callback.message)


@planner_router.message(
    lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_full_meal_name")
async def search_full_meal_handler(message: Message):
    meals = search_meals(message.text)
    if not meals:
        await message.answer("Блюда не найдены. Попробуйте еще раз.")
        return

    user_states[message.from_user.id]["meals"] = meals
    user_states[message.from_user.id]["step"] = "choosing_full_meal"

    keyboard = InlineKeyboardBuilder()
    for meal in meals:
        keyboard.button(text=meal["title"], callback_data=f"full_meal:{meal['id']}")
    keyboard.adjust(1)

    await message.answer("Выберите блюдо из списка:", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data.startswith("full_meal:"))
async def choose_full_meal_handler(callback: CallbackQuery):
    meal_id = callback.data.split(":")[1]

    # Получаем данные о БЖУ блюда
    nutrition_data = get_meal_nutrition(meal_id)
    meal_details = get_meal_details(meal_id)

    if not nutrition_data:
        await callback.message.answer("Не удалось получить данные о блюде. Попробуйте снова.")
        return

    # Сохраняем данные о блюде и запрашиваем вес
    user_states[callback.from_user.id]["meal_details"] = {
        "title": meal_details["title"],
        "image": meal_details["image"],
        "proteins": nutrition_data["proteins"],
        "fats": nutrition_data["fats"],
        "carbohydrates": nutrition_data["carbohydrates"],
        "weight_per_serving": nutrition_data["weight_per_serving"],
    }
    user_states[callback.from_user.id]["step"] = "waiting_for_weight"
    await callback.message.answer("Введите вес блюда (в граммах):")


@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_weight")
async def add_meal_weight_handler(message: Message):
    try:
        weight = float(message.text)
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректный вес блюда (в граммах).")
        return

    user_states[message.from_user.id]["weight"] = weight
    user_states[message.from_user.id]["step"] = "waiting_for_servings"
    await message.answer("Введите количество приёмов пищи (например, 1):")


@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_servings")
async def add_meal_servings_handler(message: Message):
    try:
        servings = int(message.text)
        if servings <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество приёмов пищи.")
        return

    user_data = user_states[message.from_user.id]
    meal_details = user_data["meal_details"]
    weight = user_data["weight"]
    servings = servings


    # Рассчитываем БЖУ на основе веса
    proteins = meal_details["proteins"] * (weight / meal_details["weight_per_serving"])
    fats = meal_details["fats"] * (weight / meal_details["weight_per_serving"])
    carbohydrates = meal_details["carbohydrates"] * (weight / meal_details["weight_per_serving"])

    # Сохраняем данные блюда в базу
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO meals (telegram_id, name, meal_time, image_url, protein, fat, carbohydrates, servings, weight)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                message.from_user.id,
                user_data["name"],
                user_data["meal_time"],
                meal_details["image"],
                proteins,
                fats,
                carbohydrates,
                servings,
                weight
            )
        )
        conn.commit()
    conn.close()

    # Сообщение пользователю
    await message.answer(
        f"Блюдо добавлено в ваш план питания.\n"
        f"Белки: {proteins:.2f} г, Жиры: {fats:.2f} г, Углеводы: {carbohydrates:.2f} г, Вес: {weight} г."
    )

    # Клавиатура для следующего действия
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить еще одно блюдо", callback_data="add_another_meal")
    keyboard.button(text="Просмотреть план питания", callback_data="view_plan")
    keyboard.adjust(1)

    await message.answer("Что вы хотите сделать дальше?", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data == "add_another_meal")
async def add_another_meal_handler(callback: CallbackQuery):
    user_states[callback.from_user.id] = {"step": "waiting_for_name"}
    await callback.message.answer("Введите название блюда, которое хотите добавить в план питания:")


# Обработка ввода ингредиента
# Обработка ввода ингредиента
@planner_router.message(
    lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_ingredient_name")
async def choose_ingredient_handler(message: Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем все ингредиенты из базы
    cursor.execute("SELECT name FROM ingredients")
    ingredients = cursor.fetchall()
    conn.close()

    # Выводим список ингредиентов
    if not ingredients:
        await message.answer("Ингредиенты не найдены в базе.")
        return

    keyboard = InlineKeyboardBuilder()
    for ingredient in ingredients:
        keyboard.button(text=ingredient[0], callback_data=f"ingredient:{ingredient[0]}")
    keyboard.button(text="Прекратить составление блюда", callback_data="stop_ingredient_selection")
    keyboard.adjust(1)

    await message.answer("Выберите ингредиент из списка:", reply_markup=keyboard.as_markup())


# Обработка выбора ингредиента
@planner_router.callback_query(lambda callback: callback.data.startswith("ingredient:"))
async def add_ingredient_to_meal(callback: CallbackQuery):
    ingredient_name = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_states[user_id].setdefault("selected_ingredients", []).append(ingredient_name)

    # Создаём клавиатуру для продолжения выбора или прекращения
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Продолжить выбор ингредиентов", callback_data="continue_ingredient_selection")
    keyboard.button(text="Прекратить составление блюда", callback_data="stop_ingredient_selection")
    keyboard.adjust(1)

    await callback.message.answer(f"Ингредиент '{ingredient_name}' добавлен в блюдо.",
                                  reply_markup=keyboard.as_markup())


# Обработка прекращения составления блюда
@planner_router.callback_query(lambda callback: callback.data == "stop_ingredient_selection")
async def stop_ingredient_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    selected_ingredients = user_states[user_id].get("selected_ingredients", [])

    if not selected_ingredients:
        await callback.message.answer("Вы не выбрали ни одного ингредиента.")
        return

    # Запрашиваем количество порций
    user_states[user_id]["step"] = "waiting_for_servings_count"
    await callback.message.answer("Введите количество порций для блюда:")


# Обработка ввода количества порций
@planner_router.message(
    lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_servings_count")
async def enter_servings_count(message: Message):
    user_id = message.from_user.id
    servings_count = message.text.strip()

    # Проверка на валидность ввода
    if not servings_count.isdigit() or int(servings_count) <= 0:
        await message.answer("Пожалуйста, введите корректное количество порций (целое положительное число).")
        return

    user_states[user_id]["servings_count"] = int(servings_count)

    # Расчёт БЖУ и веса на основе выбранных ингредиентов
    selected_ingredients = user_states[user_id].get("selected_ingredients", [])
    total_proteins, total_fats, total_carbs, total_weight = 0, 0, 0, 0
    conn = get_db_connection()
    cursor = conn.cursor()

    for ingredient_name in selected_ingredients:
        cursor.execute("SELECT proteins, fats, carbohydrates, weight FROM ingredients WHERE name = %s", (ingredient_name,))
        ingredient_data = cursor.fetchone()
        if ingredient_data:
            proteins, fats, carbohydrates, weight = ingredient_data
            total_proteins += proteins
            total_fats += fats
            total_carbs += carbohydrates
            total_weight += weight  # Суммируем вес каждого ингредиента

    conn.close()

    # Выводим итоговые данные
    await message.answer(
        f"Ваше блюдо состоит из:\n"
        f"Общий вес (для одной порции): {total_weight:.2f} г\n"
        f"Белки: {total_proteins:.2f} г\n"
        f"Жиры: {total_fats:.2f} г\n"
        f"Углеводы: {total_carbs:.2f} г"
    )

    # Сохраняем блюдо в базе
    meal_name = user_states[user_id]["name"]
    meal_time = user_states[user_id]["meal_time"]
    servings = user_states[user_id]["servings_count"]

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO meals (telegram_id, name, meal_time, protein, fat, carbohydrates, weight, servings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                meal_name,
                meal_time,
                total_proteins,
                total_fats,
                total_carbs,
                total_weight,  # Храним вес одной порции
                servings  # Добавляем количество порций
            )
        )
        conn.commit()
    conn.close()

    # Сообщение об успешном добавлении блюда
    await message.answer(f"Блюдо '{meal_name}' успешно добавлено в план питания.")

    # Клавиатура для следующего действия
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить еще одно блюдо", callback_data="add_another_meal")
    keyboard.button(text="Просмотреть план питания", callback_data="view_plan")
    keyboard.adjust(1)

    await message.answer("Что вы хотите сделать дальше?", reply_markup=keyboard.as_markup())


# Обработка продолжения выбора ингредиентов
@planner_router.callback_query(lambda callback: callback.data == "continue_ingredient_selection")
async def continue_ingredient_selection(callback: CallbackQuery):
    await choose_ingredient_handler(callback.message)

