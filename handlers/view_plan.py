from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import get_db_connection
from handlers.common import user_states, planner_router


def generate_plan_summary(telegram_id):
    """Формирует текстовый отчет плана питания для пользователя, сортируя блюда по времени приёма пищи и сразу выводя суммарные данные для каждого времени."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Изменяем запрос для сортировки по времени приема пищи
        cursor.execute(
            "SELECT name, meal_time, weight, protein, fat, carbohydrates, servings FROM meals WHERE telegram_id = %s ORDER BY meal_time",
            (telegram_id,)
        )
        meals = cursor.fetchall()

    if not meals:
        conn.close()
        return "Ваш план питания пуст. Добавьте блюда с помощью команды /addmeal."

    plan_summary = {}
    response = ""
    current_meal_time = None

    # Перевод meal_time на русский
    meal_time_translation = {
        "breakfast": "Завтрак",
        "lunch": "Обед",
        "dinner": "Ужин"
    }

    for meal in meals:
        meal_name, meal_time, weight, proteins, fats, carbohydrates, servings = meal

        # Если время приема пищи изменилось, выводим его на русском и начинаем список блюд для нового времени
        if meal_time != current_meal_time:
            if current_meal_time is not None:
                # Добавляем общую информацию по предыдущему времени приема пищи
                data = plan_summary[current_meal_time]
                response += f"\n\nОбщий вес приёма пищи ({meal_time_translation[current_meal_time]}): {round(data['total_weight'], 2)} г"
                response += f"\nОбщий вес белков: {round(data['total_proteins'], 2)} г"
                response += f"\nОбщий вес жиров: {round(data['total_fats'], 2)} г"
                response += f"\nОбщий вес углеводов: {round(data['total_carbohydrates'], 2)} г"
                response += f"\nКоличество порций за {meal_time_translation[current_meal_time]}: {data['meal_count']}\n"

            # Обновляем текущий meal_time и добавляем его название
            current_meal_time = meal_time
            response += f"\n\n{meal_time_translation[meal_time]}:\n"
            plan_summary[meal_time] = {
                "total_weight": 0,
                "total_proteins": 0,
                "total_fats": 0,
                "total_carbohydrates": 0,
                "total_servings": 0,
                "meal_count": 0,
            }

        # Формируем ответ по каждому блюду
        meal_details = (
            f"Блюдо: {meal_name}\n\n"
            f"Вес: {round(weight, 2)} г\n"
            f"Белки: {round(proteins, 2)} г\n"
            f"Жиры: {round(fats, 2)} г\n"
            f"Углеводы: {round(carbohydrates, 2)} г\n"
            f"Количество порций: {servings}\n\n"
        )

        response += meal_details

        # Суммируем данные по текущему времени приема пищи
        plan_summary[meal_time]["total_weight"] += weight * servings
        plan_summary[meal_time]["total_proteins"] += proteins * servings
        plan_summary[meal_time]["total_fats"] += fats * servings
        plan_summary[meal_time]["total_carbohydrates"] += carbohydrates * servings
        plan_summary[meal_time]["total_servings"] += servings
        plan_summary[meal_time]["meal_count"] += 1

    # Добавляем общую информацию для последнего времени приема пищи
    if current_meal_time is not None:
        data = plan_summary[current_meal_time]
        response += f"\n\nОбщий вес приёма пищи ({meal_time_translation[current_meal_time]}): {round(data['total_weight'], 2)} г"
        response += f"\nОбщий вес белков: {round(data['total_proteins'], 2)} г"
        response += f"\nОбщий вес жиров: {round(data['total_fats'], 2)} г"
        response += f"\nОбщий вес углеводов: {round(data['total_carbohydrates'], 2)} г"
        response += f"\nКоличество порций за {meal_time_translation[current_meal_time]}: {data['meal_count']}"

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
