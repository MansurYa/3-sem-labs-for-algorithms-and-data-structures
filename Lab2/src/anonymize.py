import pandas as pd
import numpy as np
import sys
import json
import os


def read_dataset(file_path):
    """
    Чтение входного файла с данными
    :param file_path: путь к файлу с данными
    :return: DataFrame, содержащий данные из входного файла
    """
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        if df.empty:
            print(f"Файл '{file_path}' не содержит данных. Проверьте файл и попробуйте снова.")
            sys.exit(1)
        return df
    except FileNotFoundError:
        print(f"Файл по пути '{file_path}' не найден. Проверьте путь и попробуйте снова.")
        sys.exit(1)
    except Exception as e:
        print(f"Произошла ошибка при чтении файла: {e}")
        sys.exit(1)


def get_quasi_identifiers(df):
    """
    Получение квази-идентификаторов от пользователя
    :param df: DataFrame, содержащий данные
    :return: список квази-идентификаторов, выбранных пользователем
    """
    print("Доступные столбцы в наборе данных:")
    for i, column in enumerate(df.columns):
        print(f"{i + 1}: {column}")

    selected_columns = []
    while True:
        try:
            user_input = input("Введите номера столбцов, которые вы хотите использовать в качестве квази-идентификаторов (через запятую), или 'q' для завершения: ")
            # user_input = "1,2,3,4,5,6,7,8,9"
            if user_input.lower() == 'q':
                break
            selected_indices = [int(idx.strip()) - 1 for idx in user_input.split(',')]
            for idx in selected_indices:
                if idx < 0 or idx >= len(df.columns):
                    raise ValueError("Неверный номер столбца.")
                selected_columns.append(df.columns[idx])
            break
        except ValueError as e:
            print(f"Ошибка: {e}. Пожалуйста, попробуйте снова.")

    return list(set(selected_columns))


def calculate_row_uniqueness(df):
    """
    Рассчитывает уникальность каждой строки в DataFrame.
    Добавляет новый столбец 'uniqueness' с количеством одинаковых строк.
    Возвращает k-анонимность, максимальное, среднее и медианное значения уникальности.
    """
    # Группируем по всем столбцам и считаем размер групп
    df['uniqueness'] = df.groupby(df.columns.tolist(), observed=False).transform('size')

    # Вычисляем статистики
    k_anonymity = df['uniqueness'].min()
    max_uniqueness = df['uniqueness'].max()
    avg_uniqueness = df['uniqueness'].mean()
    median_uniqueness = df['uniqueness'].median()

    return {
        'k_anonymity': k_anonymity,
        'max_uniqueness': max_uniqueness,
        'avg_uniqueness': avg_uniqueness,
        'median_uniqueness': median_uniqueness
    }


def anonymize_shop_names(df):
    """
    Anonymizes the 'Название магазина' column by replacing shop names with their categories from settings.json.
    """
    # Load settings.json
    try:
        with open('../settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("Error: '../settings.json' file not found.")
        return df
    except json.JSONDecodeError:
        print("Error: Could not parse 'settings.json'.")
        return df

    # Build the mapping from shop names to shop categories
    shop_name_to_category = {}
    shop_categories = settings.get('shop_categories', {})

    for category_name, category_info in shop_categories.items():
        chains_of_stores = category_info.get('chains_of_stores', {})
        for shop_name in chains_of_stores.keys():
            shop_name_to_category[shop_name] = category_name

    # Ensure all values in 'Название магазина' are strings
    df['Название магазина'] = df['Название магазина'].astype(str)

    # Map shop names to shop categories
    df['Название магазина'] = df['Название магазина'].map(shop_name_to_category)

    # Handle shop names not found in the mapping
    missing_shops = df['Название магазина'].isnull()
    if missing_shops.any():
        print("Warning: Some shop names were not found in 'settings.json'.")
        print(f"Number of unmatched shop names: {missing_shops.sum()}")
        df['Название магазина'] = df['Название магазина'].fillna('Unknown Category')

    return df


def anonymize_location(df):
    """
    Анонимизация данных о местоположении путем вычисления расстояния от центра и категоризации.
    """
    # Координаты центра (Дворцовая площадь)
    CENTER_LAT = 59.938784
    CENTER_LON = 30.314997

    # Преобразуем широту и долготу в числовой формат
    df['Широта'] = pd.to_numeric(df['Широта'], errors='coerce')
    df['Долгота'] = pd.to_numeric(df['Долгота'], errors='coerce')

    # Функция для вычисления расстояния с использованием формулы гаверсинусов
    def calculate_distance(row):
        lat1 = np.radians(CENTER_LAT)
        lon1 = np.radians(CENTER_LON)
        lat2 = np.radians(row['Широта'])
        lon2 = np.radians(row['Долгота'])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        R = 6371  # Радиус Земли в километрах
        distance = R * c
        return distance

    # Вычисляем расстояния
    df['Расстояние'] = df.apply(calculate_distance, axis=1)

    # Категоризируем расстояния
    def categorize_distance(distance):
        if pd.isnull(distance):
            return 'Неизвестно'
        elif distance <= 6:
            return 'До 4 км от Дворцовой площади (Санкт-Петербург)'
        elif distance <= 6:
            return 'Более 4 км, но до 8 км от Дворцовой площади (Санкт-Петербург)'
        else:
            return 'Более 8 км от Дворцовой площади (Санкт-Петербург)'

    df['Расположение'] = df['Расстояние'].apply(categorize_distance)

    # Удаляем исходные столбцы
    df = df.drop(columns=['Долгота', 'Широта', 'Расстояние'])

    return df


def anonymize_datetime(df):
    """
    Обобщает 'Дата и время' до Года + Сезон.
    """
    df['Дата и время'] = pd.to_datetime(df['Дата и время'], errors='coerce')

    def get_season(month):
        if month in [12, 1, 2]:
            return 'зима'
        elif month in [3, 4, 5]:
            return 'весна'
        elif month in [6, 7, 8]:
            return 'лето'
        elif month in [9, 10, 11]:
            return 'осень'
        else:
            return 'Неизвестно'

    df['Дата и время'] = df['Дата и время'].apply(
        lambda x: f" {x.year}, {get_season(x.month)}" if pd.notnull(x) else 'Неизвестно'
    )
    return df


def mask(df, column_name):
    """
    Полностью маскирует указанный столбец.
    """
    df[column_name] = '******'
    return df


def anonymize_card_number(df):
    """
    Заменяет номер карты на платежную систему, использованную при генерации данных.
    """
    df['Номер карты'] = df['Номер карты'].astype(str)

    # Загрузка BIN-листа
    try:
        binlist_df = pd.read_csv('../binlist-data-narrower-and-only-russians.csv', sep=';')
    except FileNotFoundError:
        print("Error: '../binlist-data-narrower-and-only-russians.csv' file not found.")
        df['Номер карты'] = 'Неизвестно'
        return df

    # Создание словаря BIN-кодов и соответствующих платежных систем
    bin_to_brand = binlist_df.set_index('bin')['brand'].to_dict()

    # Функция для определения платежной системы по BIN-коду
    def get_payment_system(card_number):
        if not card_number.isdigit() or len(card_number) < 6:
            return 'Неизвестно'
        bin_code = int(card_number[:6])
        return bin_to_brand.get(bin_code, 'Неизвестно')

    df['Номер карты'] = df['Номер карты'].apply(get_payment_system)

    return df


def generalize_column(df, column_name, num_categories):
    """
    Применяет локальное обобщение к указанному столбцу, разбивая его на заданное число категорий.

    :param df: DataFrame с данными
    :param column_name: Название столбца для обобщения
    :param num_categories: Число категорий для разбиения
    :return: DataFrame с обновленным столбцом
    """
    # Преобразуем столбец в числовой формат
    df[column_name] = pd.to_numeric(df[column_name], errors='coerce')

    # Отбрасываем NaN значения
    valid_values = df[column_name].dropna()

    if len(valid_values) == 0:
        # Нет данных для обработки
        return df

    # Вычисляем квантильные точки для разбиения
    quantiles = [i / num_categories for i in range(num_categories + 1)]
    boundaries = valid_values.quantile(quantiles).values

    # Применяем функцию для округления границ
    boundaries = beautify_boundaries(boundaries)

    # Обеспечиваем уникальность и возрастающий порядок границ
    boundaries = ensure_increasing(sorted(set(boundaries)))

    # Проверяем, что границы покрывают весь диапазон данных
    min_value = valid_values.min()
    max_value = valid_values.max()
    if boundaries[0] > min_value:
        boundaries[0] = min_value
    if boundaries[-1] < max_value:
        boundaries[-1] = max_value

    # Создаем метки для категорий
    labels = []
    for i in range(len(boundaries) - 1):
        lower = boundaries[i]
        upper = boundaries[i + 1]
        labels.append(f"{lower}-{upper}")

    # Разбиваем данные на категории
    df[column_name] = pd.cut(df[column_name], bins=boundaries, labels=labels, include_lowest=True)

    return df


def beautify_boundaries(boundaries):
    """
    Округляет границы категорий до "красивых" чисел, учитывая порядок величины.

    :param boundaries: Список исходных границ
    :return: Список округленных границ
    """
    beautified = []
    for b in boundaries:
        if b == 0:
            beautified.append(0)
            continue
        elif b < 1:
            # Округляем до 1 знака после запятой
            b_rounded = round(b, 1)
        elif b < 10:
            # Округляем до ближайшего целого числа
            b_rounded = round(b)
        elif b < 100:
            # Округляем до ближайшего кратного 5
            b_rounded = round(b / 5) * 5
        elif b < 1000:
            # Округляем до ближайшего кратного 50
            b_rounded = round(b / 50) * 50
        else:
            # Округляем до ближайшего кратного 500
            b_rounded = round(b / 500) * 500
        beautified.append(b_rounded)
    return beautified


def ensure_increasing(boundaries):
    """
    Обеспечивает, что границы строго возрастают и являются уникальными.

    :param boundaries: Список границ
    :return: Список корректированных границ
    """
    for i in range(1, len(boundaries)):
        if boundaries[i] <= boundaries[i - 1]:
            boundaries[i] = boundaries[i - 1] + 1e-6  # Добавляем маленькое число для обеспечения возрастания
    return boundaries


def remove_rows_by_uniqueness(df, percentage=10):
    """
    Удаляет строки по возрастанию уникальности на основе заданного процента от общего числа строк.

    :param df: DataFrame с данными
    :param percentage: Процент строк, которые необходимо удалить
    :return: Обновленный DataFrame с удаленными строками
    """
    total_rows = len(df)
    rows_to_remove = int(total_rows * (percentage / 100))

    # Убедимся, что столбец 'uniqueness' существует
    if 'uniqueness' not in df.columns:
        raise ValueError("Столбец 'uniqueness' не найден. Пожалуйста, сначала рассчитайте уникальность строк.")

    # Сортируем строки по возрастанию уникальности
    df_sorted = df.sort_values(by='uniqueness')

    # Отбираем строки для удаления по одной, начиная с минимальной уникальности
    df_to_remove = df_sorted.head(rows_to_remove)

    # Удаляем отобранные строки из исходного DataFrame
    df_remaining = df.drop(df_to_remove.index)

    print(f"Удалено {rows_to_remove} строк с наименьшей уникальностью.")

    # Возвращаем оставшиеся строки
    return df_remaining


def identify_bad_k_values(df, quasi_identifiers, max_rows=5):
    """
    Поиск и вывод "плохих" значений K-анонимности.

    :param df: DataFrame, содержащий данные
    :param quasi_identifiers: список квази-идентификаторов
    :param max_rows: максимальное количество выводимых строк
    :return: None
    """
    total_rows = len(df)
    grouped = df.groupby(quasi_identifiers, observed=False).size().reset_index(name='counts')
    grouped = grouped.sort_values('counts')

    # Убираем группы, где количество записей равно нулю
    grouped = grouped[grouped['counts'] > 0]

    # Выбираем группы с наименьшей K-анонимностью
    bad_groups = grouped.head(max_rows)

    if bad_groups.empty:
        print("Не найдено групп с низкой K-анонимностью.")
        return

    print(f"\nТоп {len(bad_groups)} групп с наименьшей K-анонимностью:")
    for index, row in bad_groups.iterrows():
        k_value = row['counts']
        percentage = (k_value / total_rows) * 100
        group_values = ', '.join([f"{col}={row[col]}" for col in quasi_identifiers])
        print(f"Группа: {group_values} | K-анонимность: {k_value} записей ({percentage:.2f}% от общего числа записей)")


def perform_anonymization(df, quasi_identifiers, remove_rows=True):
    df = df.copy()

    df = anonymize_shop_names(df)
    df = anonymize_datetime(df)
    df = anonymize_location(df)
    df = mask(df, "Категория")
    df = mask(df, "Бренд")
    df = anonymize_card_number(df)
    df = generalize_column(df, "Количество товаров", 5)
    df = generalize_column(df, "Стоимость", 15)

    # Обновляем список квази-идентификаторов
    quasi_identifiers = [col for col in quasi_identifiers if col in df.columns]
    if not quasi_identifiers:
        print("Ошибка: После анонимизации не осталось квази-идентификаторов для обработки.")
        sys.exit(1)

    # Удаляем строки, если это необходимо
    if remove_rows:
        df = remove_rows_by_uniqueness(df, quasi_identifiers, percentage=5)

    return df, quasi_identifiers


def print_uniqueness_metrics(uniqueness_metrics):
    print(f"Минимальная уникальность (K-анонимность): {uniqueness_metrics['k_anonymity']}")
    print(f"Максимальная уникальность: {uniqueness_metrics['max_uniqueness']}")
    print(f"Средняя уникальность: {uniqueness_metrics['avg_uniqueness']:.2f}")
    print(f"Медианная уникальность: {uniqueness_metrics['median_uniqueness']}")


def main():
    # Ввод пути к файлу с данными
    # file_path = "../purchases_data_1000000.xlsx"
    file_path = input("Введите путь к файлу с данными: ")

    # Чтение файла с данными
    df = read_dataset(file_path)

    # Получение квази-идентификаторов от пользователя
    quasi_identifiers = get_quasi_identifiers(df)

    # Анонимизация данных без удаления строк
    anonymized_df, quasi_identifiers = perform_anonymization(df, quasi_identifiers, remove_rows=False)

    # Расчет уникальности перед удалением строк
    print("\nСтатистика уникальности строк после анонимизации (до удаления строк):")
    uniqueness_metrics = calculate_row_uniqueness(anonymized_df)
    print_uniqueness_metrics(uniqueness_metrics)

    # Удаление строк
    anonymized_df = remove_rows_by_uniqueness(anonymized_df, percentage=5)

    # Расчет уникальности после удаления строк
    print("\nСтатистика уникальности строк после анонимизации (после удаления строк):")
    uniqueness_metrics = calculate_row_uniqueness(anonymized_df)
    print_uniqueness_metrics(uniqueness_metrics)

    # Выводим 5 "плохих" значений K-анонимности
    identify_bad_k_values(anonymized_df, quasi_identifiers, max_rows=5)

    # Спрашиваем пользователя, хочет ли он сохранить файл
    save_choice = input("\nВы хотите сохранить анонимизированные данные? (да/нет): ").strip().lower()
    if save_choice == 'да':
        # Определяем новый путь для сохранения файла
        dir_name, base_name = os.path.split(file_path)
        file_root, file_ext = os.path.splitext(base_name)
        new_file_name = f"{file_root}_anonymized{file_ext}"
        new_file_path = os.path.join(dir_name, new_file_name)

        # Сохраняем DataFrame в XLSX
        anonymized_df.to_excel(new_file_path, index=False)
        print(f"\nАнонимизированные данные сохранены в файл '{new_file_path}'")
    else:
        print("\nАнонимизированные данные не были сохранены.")


if __name__ == "__main__":
    main()
