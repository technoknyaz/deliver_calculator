import requests


# Проверка на существование города, который ввел пользователь
def get_city_name(city):
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={city}&format=json"
    response = requests.get(geocoder_request)
    try:
        if response:
            json_response = response.json()
            city_name = json_response['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['name']
            return city_name
    except:
        return False