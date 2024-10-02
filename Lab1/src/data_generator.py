import os
import json
import random
import pandas as pd
import csv
from datetime import datetime, timedelta
from tqdm import tqdm


def read_settings(settings_path: str) -> dict:
    """
    Читает и проверяет настройки из файла settings.json.

    :param settings_path: Путь к файлу settings.json
    :return: Возвращает словарь настроек, загруженный из settings.json
    :raises FileNotFoundError: Если файл settings.json не найден
    :raises ValueError: Если структура файла settings.json некорректна
    :raises json.JSONDecodeError: Если возникает ошибка при декодировании JSON
    """
    try:
        if not os.path.exists(settings_path):
            raise FileNotFoundError(f"Файл {settings_path} не найден.")

        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Проверка наличия ключевых полей
        required_keys = ['shop_categories', 'bin_list_path', 'opening_time_distribution',
                         'closing_time_distribution', 'purchase_quantity_distribution']
        for key in required_keys:
            if key not in settings:
                raise ValueError(f"Ключ {key} отсутствует в settings.json")

        validate_settings(settings)  # Дополнительная проверка типов
        return settings
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка при чтении JSON-файла {settings_path}: {e}")


def validate_settings(settings: dict) -> None:
    """
    Проверяет корректность данных в settings.json, включая типы значений.

    :param settings: Словарь с настройками, загруженный из settings.json
    :raises ValueError: Если структура или типы данных в settings.json некорректны
    """
    if not isinstance(settings['shop_categories'], dict):
        raise ValueError("shop_categories должен быть словарём.")

    if not isinstance(settings['bin_list_path'], str):
        raise ValueError("bin_list_path должен быть строкой.")

    if not isinstance(settings['opening_time_distribution'], dict) or \
       not all(isinstance(k, str) and isinstance(v, int) for k, v in settings['opening_time_distribution'].items()):
        raise ValueError("opening_time_distribution должен быть словарём с временем (строка) и весами (целые числа).")

    if not isinstance(settings['closing_time_distribution'], dict) or \
       not all(isinstance(k, str) and isinstance(v, int) for k, v in settings['closing_time_distribution'].items()):
        raise ValueError("closing_time_distribution должен быть словарём с временем (строка) и весами (целые числа).")

    if not isinstance(settings['purchase_quantity_distribution']['mean'], (int, float)) or \
       not isinstance(settings['purchase_quantity_distribution']['standard_deviation'], (int, float)):
        raise ValueError("purchase_quantity_distribution должен содержать числовые значения для mean и standard_deviation.")


def load_bin_list(bin_list_path: str) -> list:
    """
    Загружает BIN-коды из CSV файла.

    :param bin_list_path: Путь к файлу с BIN-кодами в формате CSV
    :return: Возвращает список BIN-кодов, загруженных из файла
    :raises FileNotFoundError: Если файл bin_list_path не найден
    :raises ValueError: Если структура файла bin_list_path некорректна или файл пуст
    """
    bin_list = []
    try:
        with open(bin_list_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if 'bin' in row:
                    bin_list.append(row['bin'])
                else:
                    raise ValueError("Отсутствует столбец 'bin' в файле bin_list_path.")
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл {bin_list_path} не найден.")
    except Exception as e:
        raise ValueError(f"Ошибка при чтении файла {bin_list_path}: {e}")

    if not bin_list:
        raise ValueError(f"Список BIN-кодов пуст. Проверьте файл {bin_list_path}.")

    return bin_list


def initialize_output_file(output_path: str) -> int:
    """
    Проверяет, существует ли файл Excel. Если да — подсчитывает строки, если нет — создаёт новый файл.
    Возвращает количество строк, которые уже находятся в файле (если файл существует).

    :param output_path: Путь к выходному файлу Excel
    :return: Количество строк, содержащихся в файле Excel, если файл существует, иначе 0
    """
    if (os.path.exists(output_path)):
        df_existing = pd.read_excel(output_path)
        existing_row_count = len(df_existing)
        print(f"Файл {output_path} существует. Найдено {existing_row_count} строк.")
        return existing_row_count
    else:
        # Изменены названия столбцов на русском языке в соответствии с ТЗ
        df_new = pd.DataFrame(columns=['Название магазина', 'Дата и время', 'Долгота', 'Широта',
                                       'Категория', 'Бренд', 'Номер карты', 'Количество товаров', 'Стоимость'])
        df_new.to_excel(output_path, index=False)
        print(f"Создан новый файл {output_path}.")
        return 0


def generate_card_number(bin_code: str, set_card_numbers: set) -> str:
    """
    Генерирует уникальный номер карты на основе BIN-кода и случайного суффикса.

    :param bin_code: BIN-код карты (первые 6 цифр)
    :param set_card_numbers: Множество уже сгенерированных номеров карт для проверки уникальности
    :return: Возвращает уникальный номер карты в формате строки
    """
    while True:
        card_suffix = ''.join([str(random.randint(0, 9)) for _ in range(10)])  # Генерация 10-значного суффикса
        card_number = bin_code + card_suffix

        if card_number not in set_card_numbers:
            set_card_numbers.add(card_number)  # Добавляем уникальный номер в множество
            return card_number


def generate_datetime(opening_time: str, closing_time: str) -> str:
    """
    Генерирует случайное время покупки в пределах работы магазина.

    :param opening_time: Время открытия магазина (в формате 'HH:MM')
    :param closing_time: Время закрытия магазина (в формате 'HH:MM')
    :return: Возвращает строку с датой и временем покупки в формате 'YYYY-MM-DD HH:MM'
    :raises ValueError: Если время закрытия меньше времени открытия
    """
    open_hour, open_minute = map(int, opening_time.split(':'))
    close_hour, close_minute = map(int, closing_time.split(':'))

    # Проверка, что время закрытия не раньше открытия и магазин открыт хотя бы на 1 час
    if close_hour < open_hour or (close_hour == open_hour and close_minute <= open_minute):
        raise ValueError("Время закрытия не может быть раньше времени открытия.")

    if close_hour == open_hour and abs(close_minute - open_minute) < 60:
        raise ValueError("Магазин должен быть открыт хотя бы 1 час.")

    # Генерация случайной даты с 2012 года
    start_date = datetime(2012, 1, 1)
    random_days = random.randint(0, (datetime.now() - start_date).days)
    random_date = start_date + timedelta(days=random_days)

    hour = random.randint(open_hour, close_hour)
    minute = random.randint(0, 59)

    # Добавляем случайное время
    random_datetime = random_date.replace(hour=hour, minute=minute)
    return random_datetime.strftime("%Y-%m-%d %H:%M")


def generate_purchase(settings: dict, card_number: str) -> list:
    """
    Генерирует строку данных о покупке. Выбирает магазин, товар, время, стоимость.

    :param settings: Словарь с настройками, загруженный из settings.json
    :param card_number: Уникальный номер карты для этой покупки
    :return: Возвращает список данных о покупке: сеть магазинов, время покупки, координаты, категория, бренд, количество покупок и цена
    :raises ValueError: Если нет доступных магазинов, категорий или брендов для выбранного магазина
    """
    shop_category = random.choice(list(settings['shop_categories'].keys()))
    shop_info = settings['shop_categories'][shop_category]

    if not shop_info['chains_of_stores']:
        raise ValueError(f"Нет доступных магазинов в категории {shop_category}.")

    chain_of_stores = random.choice(list(shop_info['chains_of_stores'].keys()))

    store_locations = shop_info['chains_of_stores'][chain_of_stores]['locations']
    if not store_locations:
        raise ValueError(f"Для сети магазинов {chain_of_stores} нет доступных локаций.")

    store_location = random.choice(store_locations)
    store_longitude = round(store_location['longitude'], 8)
    store_latitude = round(store_location['latitude'], 8)

    if random.random() < shop_info['is_open_24_hours']:
        opening_time = "00:00"
        closing_time = "23:59"
    else:
        opening_time = random.choices(list(settings['opening_time_distribution'].keys()),
                                      weights=list(settings['opening_time_distribution'].values()))[0]
        closing_time = random.choices(list(settings['closing_time_distribution'].keys()),
                                      weights=list(settings['closing_time_distribution'].values()))[0]

    purchase_datetime = generate_datetime(opening_time, closing_time)

    if not shop_info['categories']:
        raise ValueError(f"Нет доступных категорий товаров для {chain_of_stores}.")
    product_category = random.choice(list(shop_info['categories'].keys()))  # Теперь добавляем категорию
    product_brands = shop_info['categories'][product_category]['brands']

    if not product_brands:
        raise ValueError(f"Нет доступных брендов для категории {product_category}.")

    product_brand = random.choice(list(product_brands.keys()))
    product_price = product_brands[product_brand]

    number_of_purchases = max(5, min(100, int(random.gauss(settings['purchase_quantity_distribution']['mean'],
                                        settings['purchase_quantity_distribution']['standard_deviation']))))

    return [chain_of_stores, purchase_datetime, store_longitude, store_latitude,
            product_category, product_brand, card_number, number_of_purchases, product_price]


def write_to_file(output_path: str, rows: list, sheet_name: str = "Sheet1") -> None:
    """
    Записывает список строк в файл Excel по пути output_path. Если количество строк превышает лимит,
    создаёт новый лист.

    :param output_path: Путь к выходному файлу Excel
    :param rows: Список строк, которые нужно записать в Excel
    :param sheet_name: Имя листа Excel (по умолчанию "Sheet1")
    :raises PermissionError: Если недостаточно прав для записи в файл
    :raises IOError: Если возникает ошибка при записи в файл
    """
    df_new = pd.DataFrame(rows, columns=['Название магазина', 'Дата и время', 'Долгота', 'Широта',
                                         'Категория', 'Бренд', 'Номер карты', 'Количество товаров', 'Стоимость'])
    max_rows_per_sheet = 1_000_000

    try:
        if os.path.exists(output_path):
            # Используем openpyxl для дозаписи данных
            with pd.ExcelWriter(output_path, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                # Получаем существующее количество строк на листе
                if sheet_name in writer.sheets:
                    existing_rows = writer.sheets[sheet_name].max_row
                else:
                    existing_rows = 0

                # Проверяем лимит строк, если превышен, создаём новый лист
                if existing_rows + len(df_new) > max_rows_per_sheet:
                    sheet_name = f"{sheet_name}_part2"  # Создаём новый лист

                # Записываем данные на существующий или новый лист
                df_new.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=existing_rows)
        else:
            # Если файла нет, создаём новый
            df_new.to_excel(output_path, sheet_name=sheet_name, index=False)
    except PermissionError:
        raise PermissionError(f"Недостаточно прав для записи в файл {output_path}. Проверьте доступ.")
    except Exception as e:
        raise IOError(f"Ошибка при записи в файл {output_path}: {e}")


def generate_data(output_path: str, target_row_count: int, settings: dict, bin_list: list) -> None:
    """
    Основной процесс генерации данных. Управляет количеством сгенерированных строк и записью в файл,
    отображая прогресс с помощью tqdm.

    :param output_path: Путь к выходному файлу Excel
    :param target_row_count: Целевое количество строк для генерации
    :param settings: Словарь с настройками, загруженный из settings.json
    :param bin_list: Список BIN-кодов для генерации номеров карт
    """
    set_card_numbers = set()
    buffer = []
    buffer_size = 100000

    existing_row_count = initialize_output_file(output_path)
    total_count_of_generated_rows = existing_row_count

    # Инициализация прогресс-бара
    with tqdm(total=target_row_count, initial=existing_row_count, unit=" строк") as pbar:
        while total_count_of_generated_rows < target_row_count:
            bin_code = random.choice(bin_list)

            card_number = generate_card_number(bin_code, set_card_numbers)

            max_purchases_for_processed_card = random.randint(1, 5)
            for _ in range(max_purchases_for_processed_card):
                purchase = generate_purchase(settings, card_number)
                buffer.append(purchase)
                total_count_of_generated_rows += 1
                pbar.update(1)

                if len(buffer) >= buffer_size:
                    write_to_file(output_path, buffer)
                    buffer.clear()

            if total_count_of_generated_rows >= target_row_count:
                break

        if buffer:
            write_to_file(output_path, buffer)


def main() -> None:
    settings_path = '../settings.json'
    output_path = '../purchases_data.xlsx'
    target_row_count = 500000

    settings = read_settings(settings_path)

    bin_list = load_bin_list(settings['bin_list_path'])

    generate_data(output_path, target_row_count, settings, bin_list)


if __name__ == "__main__":
    main()
