import pandas as pd
import numpy as np
import sys

# Функции, которые мы будем реализовывать позже:

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

def calculate_k_anonymity(df, quasi_identifiers):
    """
    Расчет K-анонимности для дата-сета
    :param df: DataFrame, содержащий данные
    :param quasi_identifiers: список квази-идентификаторов
    :return: словарь с метриками K-анонимности, средним размером группы и медианой размера группы
    """
    grouped = df.groupby(quasi_identifiers).size()
    k_anonymity = grouped.min()
    avg_group_size = len(df) / len(grouped)
    median_group_size = grouped.median()

    return {
        "k_anonymity": k_anonymity,
        "avg_group_size": avg_group_size,
        "median_group_size": median_group_size
    }

def perform_anonymization(df, quasi_identifiers):
    """
    Выполнение анонимизации данных
    :param df: DataFrame, содержащий данные
    :param quasi_identifiers: список квази-идентификаторов
    :return: анонимизированный DataFrame
    """
    # Пока не реализовано, возвращаем исходный DataFrame
    return df

def identify_bad_k_values(df, quasi_identifiers, k_threshold, max_rows):
    """
    Поиск "плохих" значений K-анонимности
    :param df: DataFrame, содержащий данные
    :param quasi_identifiers: список квази-идентификаторов
    :param k_threshold: порог K-анонимности
    :param max_rows: максимальное количество выводимых строк
    :return: None
    """
    grouped = df.groupby(quasi_identifiers).size()
    bad_groups = grouped[grouped < k_threshold]
    bad_groups = bad_groups.nsmallest(max_rows)
    print(f"Найдено {len(bad_groups)} групп с K-анонимностью ниже порога {k_threshold}:\n{bad_groups}")

def assess_utility(original_df, anonymized_df):
    """
    Оценка полезности данных после анонимизации
    :param original_df: исходный DataFrame с данными
    :param anonymized_df: анонимизированный DataFrame
    :return: None
    """
    if original_df.equals(anonymized_df):
        print("Анонимизированные данные идентичны исходным. Не было выполнено никаких изменений.")
    else:
        print("Анонимизированные данные отличаются от исходных. Оценка полезности требует дальнейшего анализа.")

def main():
    """
    Основная функция программы для выполнения всех этапов анонимизации данных
    """
    # Ввод пути к файлу с данными
    file_path = input("Введите путь к файлу с данными: ")

    # Чтение файла с данными
    df = read_dataset(file_path)

    # Получение квази-идентификаторов от пользователя
    quasi_identifiers = get_quasi_identifiers(df)

    # Анонимизация данных
    anonymized_df = perform_anonymization(df, quasi_identifiers)

    # Расчет K-анонимности для анонимизированного дата-сета
    k_anonymity_metrics = calculate_k_anonymity(anonymized_df, quasi_identifiers)
    print(f"K-анонимность после анонимизации: {k_anonymity_metrics['k_anonymity']}")
    print(f"Средний размер группы (способ 1): {k_anonymity_metrics['avg_group_size']}")
    print(f"Медианный размер группы (способ 2): {k_anonymity_metrics['median_group_size']}")

    # Поиск и вывод "плохих" значений K-анонимности
    k_threshold = int(input("Введите порог K-анонимности: "))
    max_rows = int(input("Введите максимальное количество выводимых строк: "))
    identify_bad_k_values(anonymized_df, quasi_identifiers, k_threshold, max_rows)

    # Оценка полезности данных
    assess_utility(df, anonymized_df)

    # Сохранение анонимизированного набора данных
    anonymized_df.to_csv("anonymized_dataset.csv", index=False)
    print("Анонимизированные данные сохранены в файл 'anonymized_dataset.csv'")

if __name__ == "__main__":
    main()
