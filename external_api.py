from googletrans import Translator
import requests

API_KEY = "d7afd59487d34946be091094e448601c"
API_URL = "https://api.spoonacular.com/food/ingredients/search"

# Инициализация переводчика
translator = Translator()


def search_product(query):
    # Переводим запрос на английский
    translated_query = translator.translate(query, src='ru', dest='en').text
    response = requests.get(API_URL, params={"query": translated_query, "apiKey": API_KEY})

    if response.status_code == 200:
        # Получаем результаты
        products = response.json().get("results", [])

        # Переводим названия продуктов на русский
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
            "fats": data["nutrition"]["nutrients"][1]["amount"],      # Жиры
            "carbohydrates": data["nutrition"]["nutrients"][2]["amount"],  # Углеводы
        }
    return {}