from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import get_db_connection
from .common import user_states, planner_router


def generate_plan_summary(telegram_id):
    """Формирует текстовый отчет плана питания для пользователя."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT name, meal_time, weight, proteins, fats, carbohydrates, servings FROM meals WHERE telegram_id = %s",
            (telegram_id,)
        )
        meals = cursor.fetchall()

    if not meals:
        conn.close()
        return "Ваш план питания пуст. Добавьте блюда с помощью команды /addmeal."

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

    conn.close()
    return response


@planner_router.message(Command("viewplan"))
async def view_plan_message_handler(message: Message):
    response = generate_plan_summary(message.from_user.id)
    await message.answer(response)


@planner_router.callback_query(lambda callback: callback.data == "view_plan")
async def view_plan_callback_handler(callback: CallbackQuery):
    response = generate_plan_summary(callback.from_user.id)
    await callback.message.answer(response)
