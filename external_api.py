from googletrans import Translator
import requests

API_KEY = "d7afd59487d34946be091094e448601c"
API_PRODUCTS_URL = "https://api.spoonacular.com/food/ingredients/search"
API_MEALS_URL = "https://api.spoonacular.com/recipes/complexSearch"
API_MEAL_DETAILS_URL = "https://api.spoonacular.com/recipes/{id}/information"
API_MEAL_NUTRITION_URL = "https://api.spoonacular.com/recipes/{id}/nutritionWidget.json"

# Инициализация переводчика
translator = Translator()


def search_product(query):
    translated_query = translator.translate(query, src='ru', dest='en').text
    response = requests.get(API_PRODUCTS_URL, params={"query": translated_query, "apiKey": API_KEY})

    if response.status_code == 200:
        products = response.json().get("results", [])
        for product in products:
            product['name'] = translator.translate(product['name'], src='en', dest='ru').text
        return products
    return []


def get_product_nutrition(product_id):
    nutrition_url = f"https://api.spoonacular.com/food/ingredients/{product_id}/information"
    response = requests.get(nutrition_url, params={"apiKey": API_KEY, "amount": 100})
    if response.status_code == 200:
        data = response.json()
        return {
            "name": data["name"],
            "proteins": data["nutrition"]["nutrients"][0]["amount"],  # Белки
            "fats": data["nutrition"]["nutrients"][1]["amount"],  # Жиры
            "carbohydrates": data["nutrition"]["nutrients"][2]["amount"],  # Углеводы
        }
    return {}


def search_meals(query):
    translated_query = translator.translate(query, src='ru', dest='en').text
    response = requests.get(API_MEALS_URL, params={"query": translated_query, "apiKey": API_KEY})

    if response.status_code == 200:
        meals = response.json().get("results", [])
        for meal in meals:
            meal['title'] = translator.translate(meal['title'], src='en', dest='ru').text
            meal['image'] = meal.get('image', None)
        return meals
    return []


def get_meal_details(meal_id):
    """Получение полной информации о блюде, включая ингредиенты и БЖУ."""
    response = requests.get(API_MEAL_DETAILS_URL.format(id=meal_id), params={"apiKey": API_KEY})
    if response.status_code == 200:
        data = response.json()
        ingredients = [
            {"name": ingredient["name"], "amount": ingredient["amount"], "unit": ingredient["unit"]}
            for ingredient in data.get("extendedIngredients", [])
        ]
        return {
            "title": data["title"],
            "image": data["image"],
            "ingredients": ingredients,
        }
    return {}


def get_meal_nutrition(meal_id):
    """Получение данных о нутриентах и весе порции для блюда по его ID."""
    response = requests.get(API_MEAL_NUTRITION_URL.format(id=meal_id), params={"apiKey": API_KEY})
    if response.status_code == 200:
        data = response.json()
        nutrients = data.get("nutrients", [])
        weight_per_serving = data.get("weightPerServing", {}).get("amount", 100)  # Вес порции (по умолчанию 100 г)

        # Функция для поиска значения нутриента по его имени
        def find_nutrient_value(nutrient_name):
            for nutrient in nutrients:
                if nutrient.get("name") == nutrient_name:
                    return nutrient.get("amount", 0.0)  # Возвращаем значение или 0.0, если его нет
            return 0.0

        return {
            "proteins": find_nutrient_value("Protein"),
            "fats": find_nutrient_value("Fat"),
            "carbohydrates": find_nutrient_value("Carbohydrates"),
            "weight_per_serving": weight_per_serving
        }
    return {"proteins": 0.0, "fats": 0.0, "carbohydrates": 0.0, "weight_per_serving": 100}
