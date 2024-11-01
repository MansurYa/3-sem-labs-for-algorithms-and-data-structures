import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

file_path = None
phones = None
numbers = None
is_file_loaded = False


def compute_salt(phones, numbers):
    """
    Вычисляет значение соли, используя массивы телефонов и номеров.
    Путем сравнения значений телефонных номеров и заданного номера определяет соль,
    которая затем используется для деобезличивания данных.

    Параметры:
    - phones: список зашифрованных номеров телефонов
    - numbers: список известных незашифрованных номеров

    Возвращает:
    - salt: значение соли, если она найдена, иначе возвращает 0.
    """
    for phone in phones:
        salt = int(phone) - int(numbers[0])
        if salt < 0:
            continue
        i = 1
        while (str(int(numbers[i]) + salt)) in phones:
            i += 1
            if i == 5:
                return salt
    return 0


def sha1(phones):
    """
    Хеширует номера телефонов с использованием SHA-1 и сохраняет результаты в 'sha1.txt'.
    Затем использует hashcat для попытки расшифровки хешей с перебором 11-значных чисел.

    Параметры:
    - phones: список номеров телефонов
    """
    phones_sha1 = [hashlib.sha1(phone.encode()).hexdigest() for phone in phones]
    with open('sha1.txt', 'w') as f:
        for phone in phones_sha1:
            f.write(phone + '\n')

    os.remove('hashcat.potfile')
    os.system("hashcat -a 3 -m 100 -o output_sha1.txt sha1.txt ?d?d?d?d?d?d?d?d?d?d?d")


def sha256(phones):
    """
    Хеширует номера телефонов с использованием SHA-256 и сохраняет результаты в 'sha256.txt'.
    Затем использует hashcat для попытки расшифровки хешей с перебором 11-значных чисел.

    Параметры:
    - phones: список номеров телефонов
    """
    phones_sha256 = [hashlib.sha256(phone.encode()).hexdigest() for phone in phones]
    with open('sha256.txt', 'w') as f:
        for phone in phones_sha256:
            f.write(phone + '\n')

    os.remove('hashcat.potfile')
    os.system("hashcat -a 3 -m 1400 -o output_sha256.txt sha256.txt ?d?d?d?d?d?d?d?d?d?d?d")


def sha512(phones):
    """
    Хеширует номера телефонов с использованием SHA-512 и сохраняет результаты в 'sha512.txt'.
    Затем использует hashcat для попытки расшифровки хешей с перебором 11-значных чисел.

    Параметры:
    - phones: список номеров телефонов
    """
    phones_sha512 = [hashlib.sha512(phone.encode()).hexdigest() for phone in phones]
    with open('sha512.txt', 'w') as f:
        for phone in phones_sha512:
            f.write(phone + '\n')

    os.remove('hashcat.potfile')
    os.system("hashcat -a 3 -m 1700 -o output_sha512.txt sha512.txt ?d?d?d?d?d?d?d?d?d?d?d")


def load_file():
    """
    Загружает файл с данными, выбираемый пользователем, и активирует кнопку для деобезличивания.
    """
    global file_path, is_file_loaded
    file_path = filedialog.askopenfilename()
    if file_path:
        is_file_loaded = True
        button_deidentify["state"] = tk.NORMAL


def identify():
    """
    Загружает данные из Excel-файла, извлекает хеши и первые пять номеров телефонов,
    затем запускает hashcat для расшифровки хешей.
    """
    global file_path, phones, numbers

    if os.path.exists('output.txt'):
        os.remove('output.txt')

    if os.path.exists('hashes.txt'):
        os.remove('hashes.txt')

    if os.path.exists('hashes.txt'):
        os.remove('phones.txt')

    df = pd.read_excel(file_path)
    hashes = df["Номер телефона"]
    numbers = [number[:-2] for number in df["Unnamed: 2"].astype(str).tolist()][:5]

    with open('hashes.txt', 'w') as f:
        for HASH in hashes:
            f.write(HASH + "\n")

    os.system("hashcat -a 3 -m 0 --potfile-path output.txt hashes.txt ?d?d?d?d?d?d?d?d?d?d?d")

    with open('output.txt') as r:
        phones = [line.strip()[33:] for line in r.readlines()]

    # Сохранение расшифрованных номеров в phones.txt
    with open('phones.txt', 'w') as file:
        for phone in phones:
            file.write(phone + '\n')

    messagebox.showinfo("Готово", "Таблица успешно расшифрована. Данные сохранены в файле 'phones.txt'.")


def find_salt():
    """
    Вычисляет значение соли, используя функцию compute_salt, и сохраняет расшифрованные номера в файл.
    Проверяет, существуют ли нужные файлы для работы, и удаляет файл для записи, если он уже существует.
    """
    global phones, numbers
    salt = compute_salt(phones, numbers)
    messagebox.showinfo("Готово", f"Значение соли: {salt}")

    if not os.path.exists('phones.txt'):
        messagebox.showerror("Ошибка", "Файл phones.txt не найден.")
        return

    decrypted_file = 'phones_without_salt.txt'

    if os.path.exists(decrypted_file):
        os.remove(decrypted_file)

    with open('phones.txt', 'r') as f:
        decrypted_numbers = []
        for line in f:
            phone_number = line.strip()
            try:
                decrypted_number = int(phone_number) - salt
                decrypted_numbers.append(str(decrypted_number))
            except ValueError:
                continue

    with open(decrypted_file, 'w') as f:
        for number in decrypted_numbers:
            f.write(number + '\n')

    messagebox.showinfo("Готово", f"Номера без соли сохранены в файле '{decrypted_file}'.")


def encrypt(algorithm):
    """
    Шифрует данные с использованием выбранного алгоритма (SHA-1, SHA-256 или SHA-512)
    и сохраняет результат в соответствующем файле.

    Параметры:
    - algorithm: строка, обозначающая алгоритм ("sha1", "sha256", "sha512").
    """
    global is_file_loaded, phones
    if not is_file_loaded:
        return
    if algorithm == "sha1":
        sha1(phones)
        messagebox.showinfo("Готово", "Результат сохранен в файле output_sha1.")
    elif algorithm == "sha256":
        sha256(phones)
        messagebox.showinfo("Готово", "Результат сохранен в файле output_sha256.")
    else:
        sha512(phones)
        messagebox.showinfo("Готово", "Результат сохранен в файле output_sha512.")


root = tk.Tk()
root.title("Шифрование данных")
root.geometry("350x400")  # Фиксированный размер окна
root.resizable(False, False)  # Запрет на изменение размеров окна
root.configure(bg="#fff8dc")  # Пастельный цвет фона

# Заголовок
label_title = tk.Label(root, text="Шифрование данных", font=("Helvetica", 16, "bold"), fg="black", bg="#fff8dc")
label_title.pack(pady=(10, 20))

# Функция для создания цветных кнопок
def create_button(text, command, color, state=tk.NORMAL):
    return tk.Button(root, text=text, command=command, bg=color, fg="black", font=("Helvetica", 12), bd=0, padx=10, pady=5, activebackground="#ffeb99", state=state)

# Кнопки с реальной функциональностью
button_load = create_button("Загрузить таблицу", load_file, "#ffeb99")
button_load.pack(pady=5)

button_deidentify = create_button("Расшифровать", identify, "#ffd699", state=tk.DISABLED)
button_deidentify.pack(pady=5)

button_compute_salt = create_button("Вычислить соль", find_salt, "#ffcc99")
button_compute_salt.pack(pady=5)

button_encrypt_sha1 = create_button("Зашифровать SHA-1", lambda: encrypt("SHA-1"), "#ffb380")
button_encrypt_sha1.pack(pady=5)

button_encrypt_sha256 = create_button("Зашифровать SHA-256", lambda: encrypt("SHA-256"), "#ffb380")
button_encrypt_sha256.pack(pady=5)

button_encrypt_sha512 = create_button("Зашифровать SHA-512", lambda: encrypt("SHA-512"), "#ffb380")
button_encrypt_sha512.pack(pady=5)

# Запуск основного цикла приложения
root.mainloop()
