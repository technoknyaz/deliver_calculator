import requests
import json
import string


# Подключение API (Компания ПЭК)
# Расчет стоимости перевозки/доставки
class NoDeliveryToThisCity(Exception):
    def __init__(self, name):
        self.city_name = name

    def __str__(self):
        return f'Компания ПЭК еще не работает в городе "{self.city_name}"'


# Получение кода города
def get_city_code(city):
    town_list_url = 'http://www.pecom.ru/ru/calc/towns.php'
    town_list = json.loads(bytes(requests.get(town_list_url).content).decode('utf-8'))
    if city in town_list.keys():
        return list(town_list[city].keys())[0]
    return False


# Получение информации о доставке по заданным пользователем параметрам
def get_info_delivery(city_from: string, city_to: string, weight: int, width: int, long: int,
                    height: int, volume: int, is_negabarit=False, need_protected_package=False, places=1):
    calculator_url = 'http://calc.pecom.ru/bitrix/components/pecom/calc/ajax.php'
    code_city_from = get_city_code(city_from)
    code_city_to = get_city_code(city_to)
    if not code_city_from:
        raise NoDeliveryToThisCity(city_from)
    if not code_city_to:
        raise NoDeliveryToThisCity(city_to)
    params = {}
    for i in range(places):
        params[f'places[{i}]'] = [width, long, height, volume, weight, is_negabarit, need_protected_package]
    params[f'take[town]'] = code_city_from
    params[f'deliver[town]'] = code_city_to
    params['take[tent]'] = 0
    params['take[gidro]'] = 0
    params['take[manip]'] = 0
    params['take[speed]'] = 0
    params['deliver[tent]'] = 0
    params['deliver[gidro]'] = 0
    params['deliver[manip]'] = 0
    params['deliver[speed]'] = 0
    params['plombir'] = 0
    params['strah'] = 0
    params['ashan'] = 0
    params['night'] = 0
    params['pal'] = 0
    params['pallets'] = 0
    return json.loads(bytes(requests.get(calculator_url, params=params).content).decode('utf-8'))