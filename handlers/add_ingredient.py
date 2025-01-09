from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_db_connection
from external_api import search_product, get_product_nutrition
from .common import user_states, planner_router


@planner_router.message(Command("addingredient"))
async def start_ingredient_addition(message: Message):
    user_states[message.from_user.id] = {"step": "awaiting_ingredient_name"}
    await message.answer("Введите название ингредиента, которое хотите добавить:")


@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "awaiting_ingredient_name")
async def handle_ingredient_name(message: Message):
    user_states[message.from_user.id]["name"] = message.text
    user_states[message.from_user.id]["step"] = "awaiting_ingredient_weight"

    await message.answer("Теперь введите вес ингредиента (в граммах):")


@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "awaiting_ingredient_weight")
async def handle_ingredient_weight(message: Message):
    try:
        weight = float(message.text)
        user_states[message.from_user.id]["weight"] = weight
        user_states[message.from_user.id]["step"] = "awaiting_product_search"
        await message.answer("Введите название продукта для поиска в базе:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный вес (число).")


@planner_router.message(lambda message: user_states.get(message.from_user.id, {}).get("step") == "awaiting_product_search")
async def handle_product_search(message: Message):
    products = search_product(message.text)
    if not products:
        await message.answer("Продукты не найдены. Попробуйте еще раз.")
        return

    user_states[message.from_user.id]["products"] = products
    user_states[message.from_user.id]["step"] = "awaiting_product_selection"

    keyboard = InlineKeyboardBuilder()
    for product in products:
        keyboard.button(text=product["name"], callback_data=f"product:{product['id']}")
    keyboard.adjust(1)

    await message.answer("Выберите продукт из списка:", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data.startswith("product:"))
async def handle_product_selection(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    nutrition = get_product_nutrition(product_id)
    if not nutrition:
        await callback.message.answer("Ошибка при получении данных продукта. Попробуйте снова.")
        return

    user_data = user_states.pop(callback.from_user.id, None)
    if not user_data:
        await callback.message.answer("Ошибка при добавлении ингредиента. Попробуйте снова.")
        return

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingredients (telegram_id, name, weight, proteins, fats, carbohydrates)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                callback.from_user.id,
                user_data["name"],
                user_data["weight"],
                nutrition["proteins"],
                nutrition["fats"],
                nutrition["carbohydrates"],
            )
        )
        conn.commit()
    conn.close()

    await callback.message.answer(
        f"Ингредиент '{user_data['name']}' добавлено с данными:\n"
        f"- Вес: {user_data['weight']} г\n"
        f"- Белки: {nutrition['proteins']} г\n"
        f"- Жиры: {nutrition['fats']} г\n"
        f"- Углеводы: {nutrition['carbohydrates']} г."
    )

    # Предложение добавить еще один ингредиент или просмотреть все добавленные ингредиенты
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить еще один ингредиент", callback_data="add_another_ingredient")
    keyboard.button(text="Просмотреть все добавленные ингредиенты", callback_data="view_ingredients")
    keyboard.adjust(1)

    await callback.message.answer("Что вы хотите сделать дальше?", reply_markup=keyboard.as_markup())


@planner_router.callback_query(lambda callback: callback.data == "add_another_ingredient")
async def handle_another_ingredient_addition(callback: CallbackQuery):
    user_states[callback.from_user.id] = {"step": "awaiting_ingredient_name"}
    await callback.message.answer("Введите название блюда, которое хотите добавить в план питания:")


@planner_router.callback_query(lambda callback: callback.data == "view_ingredients")
async def handle_view_ingredients(callback: CallbackQuery):
    # Получаем все добавленные ингредиенты для текущего пользователя
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT name, weight, proteins, fats, carbohydrates 
            FROM ingredients 
            WHERE telegram_id = %s
            """,
            (callback.from_user.id,)
        )
        ingredients = cursor.fetchall()

    if not ingredients:
        await callback.message.answer("У вас еще нет добавленных ингредиентов.")
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

    await callback.message.answer(f"Все добавленные ингредиенты:\n{ingredient_list}")

