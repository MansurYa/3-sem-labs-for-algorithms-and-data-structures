# -*- coding: utf-8 -*-
import os
import re
import requests
import pandas as pd
from openai import OpenAI
import json


def chat_GPT_response(prompt: str):
    """
    Получение ответа от Chat GPT.

    :param prompt: Инструкция/сообщение - что нужно сделать?
    :return: Строка - ответ от Chat GPT
    """

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_API_ORGANIZATION_KEY = os.environ.get("OPENAI_API_ORGANIZATION_KEY")

    if not OPENAI_API_KEY or not OPENAI_API_ORGANIZATION_KEY:
        raise ValueError("API ключи не найдены. Проверьте переменные окружения.")

    client = OpenAI(
        organization=OPENAI_API_ORGANIZATION_KEY,
        api_key=OPENAI_API_KEY
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=4096,
        stream=False,
    )

    return response.choices[0].message.content


def get_organizations_locations(organizations_name: str, location_for_search: str, search_center_longitude: float,
                                search_center_latitude: float, search_radius: float):
    """
    Используя API Поиска по организациям от Yandex,
    находит координаты организаций по её имени
    в некоторой области, например, в некотором городе.

    :param organizations_name: Название сети организаций для поиска
    :param location_for_search: Локация для поиска, например, название города
    :param search_center_longitude: долгота точки центра поиска в градусах
    :param search_center_latitude: широта точки центра поиска в градусах
    :param search_radius: Радиус поиска организаций от центра
    :return: Возвращает список словарей. Каждый словарь - это координаты магазина в следующем формате:
                {
                    "longitude": долгота магазина,
                    "latitude": широта магазина
                }
    """

    YANDEX_ORGANIZATION_SEARCH_API_KEY = os.environ.get("YANDEX_ORGANIZATION_SEARCH_API_KEY")

    if not YANDEX_ORGANIZATION_SEARCH_API_KEY:
        raise ValueError("API key not found. Set it as an environment variable YANDEX_ORGANIZATION_SEARCH_API_KEY")

    base_url = "https://search-maps.yandex.ru/v1/"

    params = {
        "text": f"{location_for_search}, {organizations_name}",
        "type": "biz",
        "lang": "ru_RU",
        "ll": f"{search_center_longitude},{search_center_latitude}",
        "spn": f"{search_radius},{search_radius}",
        "results": 50,  # Максимальное количество результатов на запрос
        "apikey": YANDEX_ORGANIZATION_SEARCH_API_KEY
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}")

    data = response.json()

    organizations_locations = []
    for feature in data.get("features", []):
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) == 2:
            longitude, latitude = coordinates
            organizations_locations.append({
                "longitude": longitude,
                "latitude": latitude
            })

    return organizations_locations


def get_input(message_text: str, expected_type: type):
    """
    Выводит message_text в консоль, получает ввод от пользователя,
    преобразует его в указанный тип (str, int, float) и возвращает результат.
    Если тип некорректен, повторяет запрос до тех пор, пока не получит верный ввод.

    :param message_text: Сообщение, которое будет отображаться пользователю
    :param expected_type: Ожидаемый тип данных (str, int, float)
    :return: Значение, преобразованное в указанный тип
    """

    if expected_type not in [str, int, float]:
        raise ValueError("Допустимы только типы: str, int, float")

    while True:
        user_input = input(message_text)
        try:
            if expected_type == str:
                return user_input
            elif expected_type == int:
                return int(user_input)
            elif expected_type == float:
                return float(user_input)
        except ValueError:
            print(f"Ошибка: введите корректное значение типа {expected_type.__name__}.")


def is_valid_file_path(file_path: str, expected_extension: str) -> bool:
    """
    Проверяет, корректен ли путь к файлу и соответствует ли расширение файла ожидаемому.

    :param file_path: Путь к файлу вместе с именем и расширением
    :param expected_extension: Ожидаемое расширение файла (например, 'png')
    :return: True, если путь корректен и файл имеет правильное расширение, иначе False
    """

    if not expected_extension.startswith('.'):
        expected_extension = f".{expected_extension}"

    _, file_extension = os.path.splitext(file_path)

    if file_extension.lower() != expected_extension.lower():
        return False

    try:
        if not os.path.isabs(file_path):
            return False

        os.path.normpath(file_path)

        return True
    except Exception:
        return False


def get_list_of_strings_or_ints_from_chat_gpt_response(prompt_for_list_generation: str, expected_type: type):
    """
    Используя форматирование с помощью ввода в нужном формате списка в консоль,
    который является ответом на ответ от chat GPT, возвращает список строк или целых чисел.

    :param prompt_for_list_generation: Промпт для chat GPT для генерации списка
    :param expected_type: Ожидаемый тип данных (str или int)
    :return: Список строк или целых чисел
    """

    list_of_values = []

    string_list_regex = r'^\[\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\]$'
    int_list_regex = r'^\[\s*\d+(?:\s*,\s*\d+)*\s*\]$'

    while True:
        GPT_response = chat_GPT_response(prompt_for_list_generation)

        str_list_of_values = get_input(f"""
        
        user: {prompt_for_list_generation}
        
        chat_GPT: {GPT_response}
        
        Введите список в следующем формате:
        "[\"Наименование1\", \"Наименование2\", ...]\" если ожидается список строк, или \"[1, 2, 3, ...]\" для списка чисел
        
        Ввод: """, str)

        if expected_type == str and re.match(string_list_regex, str_list_of_values.strip()):
            list_of_values = re.findall(r'"([^"]*)"', str_list_of_values)

        elif expected_type == int and re.match(int_list_regex, str_list_of_values.strip()):
            list_of_values = [int(x) for x in re.findall(r'\d+', str_list_of_values)]

        else:
            print(f"Некорректный ввод. Проверьте формат списка для {expected_type.__name__} и попробуйте снова.")
            continue

        if list_of_values:
            print("Список успешно получен!")
            break
        else:
            print("Список пустой, попробуйте снова.")

    return list_of_values


def main():
    while True:
        path_to_settings_file = get_input("Введите путь до settings.json вместе с именем и расширением файла: ", str)

        if is_valid_file_path(path_to_settings_file, "json"): break

    if os.path.isfile(path_to_settings_file):
        raise Exception("Такой файл уже существует! Введите другой путь")

    directory_path_to_settings_file = os.path.dirname(path_to_settings_file)
    if not os.path.exists(directory_path_to_settings_file):
        os.makedirs(directory_path_to_settings_file)

    settings = {}  # Запишем в setting.json в конце функции (после заполнения settings)

    shop_categories_list = [
        "Продуктовые магазины",
        "Магазины электроники",
        "Строительные магазины",
        "Магазины одежды",
        "Магазины автозапчастей и автотоваров"
    ]

    settings["shop_categories"] = {}

    for shop_category in shop_categories_list:
        settings["shop_categories"][shop_category] = {}

        chain_of_stores_list = []

        while True:
            count_of_stores_to_add = get_input(
                f"Введите количество магазинов, которые вы хотите добавить для магазинов типа \"{shop_category}\" (> 0): ",
                int)

            if count_of_stores_to_add < 1:
                print("Вы ввели целое числи < 1.\n")
            else:
                break

        for count in range(count_of_stores_to_add):
            chain_of_stores_list.append(get_input(
                f"Введите название {count + 1} из {count_of_stores_to_add} сети магазинов типа \"{shop_category}\": ",
                str))

        settings["shop_categories"][shop_category]["chains_of_stores"] = {}

        for name_of_store in chain_of_stores_list:
            settings["shop_categories"][shop_category]["chains_of_stores"][name_of_store] = {}

            settings["shop_categories"][shop_category]["chains_of_stores"][name_of_store]["locations"] \
                = get_organizations_locations(name_of_store, "Санкт-Петербург", 59.938784, 30.314997, 0.2)

        print(f"\nsettings: {settings}\n\n")

        settings["shop_categories"][shop_category]["categories"] = {}

        product_category_list = get_list_of_strings_or_ints_from_chat_gpt_response(f"""
        Напиши список категорий, которые могут встречаться в магазинах с тематикой "{shop_category}".

        В ответном сообщении не указывай никакой дополнительной информации! Все категории должны быть перечислены через запятую с одним примером, а в конце предложения не должно стоять знака окончания предложения. Перед началом перечисления нужно написать `\start`, а после завершения — `\end`, каждое наименование записывать в фигурные кавычки `"name"` и обёрнуто в [] (как массив).. Соблюдай шаблон точно, только с другими названиями категорий для указанной тематики магазина, не добавляй и не убирай никаких символов и слов.

        Пример для магазина с тематикой "Магазины электроники":
        ```
        \start
        ["Смартфоны и мобильные телефоны", "Планшеты", "Ноутбуки", "Настольные компьютеры", "Мониторы", "Компьютерные периферийные устройства", "Принтеры и сканеры", "Сетевое оборудование", "Телевизоры", "Аудиооборудование", "Фото- и видеокамеры", "Игровые консоли и аксессуары", "Устройства умного дома", "Носимая электроника", "Программное обеспечение", "Накопители данных", "Кабели и адаптеры", "Батарейки и зарядные устройства", "Аксессуары для мобильных устройств", "Дроны и робототехника", "Автоэлектроника", "Офисная техника", "Мелкая бытовая техника", "Устройства виртуальной и дополненной реальности", "Системы безопасности", "Программируемые устройства", "3D-принтеры и аксессуары", "Электронные книги", "Телефоны и оборудование для стационарной связи", "Сетевые сервисы и подписки"]
        \end
        ```
        """, str)

        for product_category in product_category_list:
            settings["shop_categories"][shop_category]["categories"][product_category] = {}
            settings["shop_categories"][shop_category]["categories"][product_category]["brands"] = {}

            brands_list = get_list_of_strings_or_ints_from_chat_gpt_response(f"""
            Представь, что мы находимся в {shop_category}.
            Напиши список брендов, которые могут встречаться в этом магазине и которые ПРОИЗВОДЯТ ТОВАР В категории товаров {product_category}, то есть, у них есть продукция из категории {product_category}!

            В ответном сообщении не указывай никакой дополнительной информации! Все бренды должны быть перечислены через запятую с одним примером, а в конце предложения не должно стоять знака окончания предложения. Перед началом перечисления нужно написать `\start`, а после завершения — `\end`, каждое наименование записывать в фигурные кавычки `"name"` и обёрнуто в [] (как массив). Соблюдай шаблон точно, только с другими названиями брендов для указанной категории товаров, не добавляй и не убирай никаких символов и слов.

            Пример для магазина с тематикой "Магазины электроники" и категорией "Смартфоны и мобильные телефоны":
            ```
            \start
            ["Apple", "Samsung", "Huawei", "Xiaomi", "OPPO", "Vivo", "Sony", "Google", "OnePlus", "Nokia", "Motorola", "Asus", "Lenovo", "Realme", "ZTE", "Nothing", "Honor", "Infinix", "Tecno", "Ulefone", "Prestigio", "UMIDIGI"]
            \end
            ```
            """, str)

            price_fot_brands_list = get_list_of_strings_or_ints_from_chat_gpt_response(f"""
            Представь, что мы находимся в {shop_category}.
            В категории товаров {product_category}!
            Вот список брендов, которые продают товар из категории {product_category} в магазине типа {shop_category}:
            {", ".join(brands_list)}.
            Оцени сколько будут стоить продукты категории {product_category} в {shop_category} от каждого из данных брендов

            В ответном сообщении не указывай никакой дополнительной информации! В примере показан шаблон ответа, ни в коем случае не откланяйся от него!

            Пример для магазина с тематикой "{shop_category}" и категории {product_category}:
            ```
            \start
            “Apple”: 80000
            “Samsung”: 45000
            “Huawei”: 35000
            “Xiaomi”: 25000
            “OPPO”: 30000
            “Vivo”: 28000
            “Sony”: 50000
            “Google”: 55000
            “OnePlus”: 40000
            “Nokia”: 20000
            “Motorola”: 22000
            “Asus”: 35000
            “Lenovo”: 18000
            “Realme”: 20000
            “ZTE”: 16000
            “Nothing”: 37000
            “Honor”: 27000
            “Infinix”: 15000
            “Tecno”: 14000
            “Ulefone”: 12000
            “Prestigio”: 11000
            “UMIDIGI”: 13000
            \end
            \start_of_array
            [80000, 45000, 35000, 25000, 30000, 28000, 50000, 55000, 40000, 20000, 22000, 35000, 18000, 20000, 16000, 37000, 27000, 15000, 14000, 12000, 11000, 13000]
            \end_of_array
            ```

            Давай правильную оценку цены! Например, для смартфонов нормально, что они стоят 80000, но молоко должно стоить в районе 80, а новая машина может стоить 5000000!
            """, int)

            for brand, price in zip(brands_list, price_fot_brands_list):
                settings["shop_categories"][shop_category]["categories"][product_category]["brands"][brand] = price

        while True:
            weight = get_input(
                f"Укажите вероятность того, что магазины типа {shop_category} работают круглосуточно, где 0.0 означает, что такие магазины никогда не работают 24 часа в сутки, а 1.0 — что они всегда работают 24 часа в сутки",
                float)
            if weight < 0.0 or weight > 1.0:
                print(f"\nВы ввели некоректное значенеие - {weight}\n")
            else:
                break
        settings["shop_categories"][shop_category]["is_open_24_hours"] = weight

        print(settings)

    settings["opening_time_distribution"] = {}
    for opening_time in ["7:00", "8:00", "9:00", "10:00", "11:00"]:
        while True:
            weight = get_input(
                f"Введите вес (натуральное число или 0) для расчёта вероятности того, что магазин откроется в{opening_time} ",
                int)
            if weight < 0:
                print(f"\nВы ввели отрицательное значение - {weight}\n")
            else:
                break

        settings["opening_time_distribution"][opening_time] = weight

    settings["closing_time_distribution"] = {}
    for closing_time in ["20:00", "21:00", "22:00", "23:00", "24:00"]:
        while True:
            weight = get_input(
                f"Введите вес (натуральное число или 0) для расчёта вероятности того, что магазин закроется в{closing_time} ",
                int)
            if weight < 0:
                print(f"\nВы ввели отрицательное значение - {weight}\n")
            else:
                break

        settings["closing_time_distribution"][closing_time] = weight

    settings["purchase_quantity_distribution"] = {}

    while True:
        mean = get_input(
            f"Введите значения \"mean\"(натуральное число >= 5) для определения функции нормального распределения вероятностей количества покупок в одном чеке.",
            int)
        if mean < 5:
            print(f"\nВы ввели значение < 5 - {mean}\n")
        else:
            break
    settings["purchase_quantity_distribution"]["mean"] = mean

    while True:
        standard_deviation = get_input(
            f"Введите значения стандартного отклонения \"standard_deviation\"(натуральное число) для определения функции нормального распределения вероятностей количества покупок в одном чеке.",
            int)
        if standard_deviation < 1:
            print(f"\nВы ввели значение < 1 - {standard_deviation}\n")
        else:
            break
    settings["purchase_quantity_distribution"]["standard_deviation"] = standard_deviation

    while True:
        bin_list_path = get_input("Введите путь до файла BIN-кодов (.csv): ", str)
        if os.path.exists(bin_list_path) and bin_list_path.endswith('.csv'):
            break
        else:
            print("Файл не существует или расширение некорректное. Попробуйте снова.")
    bin_list_path = "../BINs/binlist-data-narrower-and-only-russians.csv"

    bin_list = pd.read_csv(bin_list_path, sep=';')

    required_columns = ['bin', 'brand', 'issuer']
    if not all(col in bin_list.columns for col in required_columns):
        raise ValueError("Файл не содержит всех необходимых данных.")

    settings["payment_systems_distribution"] = {}

    payment_systems_stack = bin_list['brand'].unique().tolist()

    for payment_system in payment_systems_stack:
        weight = get_input(f"Введите вероятность для системы {payment_system} (натуральное число или 0): ", int)

        if weight > 0:
            settings["payment_systems_distribution"][payment_system] = weight

    print(settings)

    settings["banks_distribution"] = {}

    bank_list = bin_list['issuer'].unique().tolist()

    bank_stack = ["SBER", "VTB", "ALFA", "GAZPROM", "RAIFFEISEN", "UNICREDIT", "TINKOFF", "PROMSVYAZ",
                  "RUSSIAN AGRICULTURAL", "ROSBANK", "OTKRITIE", "SOVCOM", "MOSCOW INDUSTRIAL",
                  "SAINT PETERSBURG", "RENESANS", "URALSIB", "CREDIT BANK OF MOSCOW", "ZENTI", "BIN"]

    for bank in bank_stack:
        weight = get_input(f"Введите вероятность для банка {bank} (натуральное число или 0): ", int)

        if weight > 0:
            active_bank_list = [b for b in bank_list if isinstance(b, str) and bank in b]

            for active_bank in active_bank_list:
                bank_list.remove(active_bank)
                settings["banks_distribution"][active_bank] = weight

    settings["bin_list_path"] = bin_list_path

    print(f"\nSettings сформирован: \n{settings}")

    try:
        with open(path_to_settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f"Настройки успешно сохранены в {path_to_settings_file}")
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")


if __name__ == "__main__":
    main()
