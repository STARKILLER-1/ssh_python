import re  # Импорт модуля регулярных выражений для обработки текста.
from ssh2.session import Session  # Импорт класса Session из модуля ssh2 для работы с SSH.
from socket import socket, AF_INET, SOCK_STREAM  # Импорт необходимых компонентов для создания сетевого соединения.

# Определение класса SSHClient, который будет управлять SSH-соединениями.
class SSHClient:
    # Конструктор класса, инициализация с основными параметрами для подключения.
    def __init__(self, hostname, username, password=None, port=None, key=None):
        self.hostname = hostname  # Адрес хоста для подключения.
        self.username = username  # Имя пользователя для аутентификации.
        self.password = password  # Пароль для аутентификации, может быть None, если используется ключ.
        self.port = port if port else 22  # Порт для подключения, по умолчанию 22.
        self.key = key  # Путь к файлу с приватным ключом, если используется аутентификация по ключу.
        self.cwd = '/'  # Текущая рабочая директория на удаленном сервере.
        self.session = self._create_session()  # Создание SSH-сессии.
        # Словарь с регулярными выражениями для раскраски вывода.
        self.color_patterns = {
            r"error": "\033[31m",  # Красный цвет для сообщений об ошибках.
            r"command not found": "\033[31m",  # Красный цвет для сообщения "command not found".
            # Добавьте другие паттерны по необходимости.
        }

    # Метод для создания сетевого соединения и инициализации SSH-сессии.
    def _create_session(self):
        sock = socket(AF_INET, SOCK_STREAM)  # Создание сетевого сокета.
        sock.connect((self.hostname, self.port))  # Установка соединения с хостом и портом.
        session = Session()  # Создание объекта сессии SSH.
        session.handshake(sock)  # Инициализация SSH-сессии с помощью рукопожатия.
        # Аутентификация с использованием ключа или пароля.
        if self.key:
            session.userauth_publickey_fromfile(self.username, self.key)
        else:
            session.userauth_password(self.username, self.password)
        print("Создал сессию")  # Вывод сообщения о создании сессии.
        return session  # Возврат объекта сессии.

    # Метод для выполнения команды на удаленном сервере.
    def execute_command(self, command):
        # Открытие канала для отправки команды.
        channel = self.session.open_session()
        # Формирование команды с учетом текущей рабочей директории.
        command_to_execute = f"cd {self.cwd} && {command}"
        if command.startswith('cd '):
            # Для команды 'cd' добавляем 'pwd' для получения новой рабочей директории.
            command_to_execute += " && pwd"
            
        channel.execute(command_to_execute)  # Выполнение сформированной команды.
        output = ''  # Строка для сбора вывода команды.
        # Чтение данных из канала до достижения конца файла (EOF).
        while not channel.eof():
            size, data = channel.read()
            output += data.decode()
            error_size, error_data = channel.read_stderr()
            output += error_data.decode()

        exit_status = channel.get_exit_status()  # Получение статуса завершения команды.
        channel.close()  # Закрытие канала.

        # Обновление текущей рабочей директории после выполнения 'cd'.
        if command.startswith('cd ') and exit_status == 0:
            new_path = output.strip().split('\n')[-1]
            if new_path:
                self.cwd = new_path  # Обновление рабочей директории.
                return ''  # Возвращаем пустую строку, чтобы не выводить результат 'pwd'.

        # Распарсивание и возвращение вывода команды, если он не пустой.
        parsed_output = self._parse_output(output, exit_status) if output.strip() else ''
        return parsed_output

    # Метод для раскраски и обработки вывода команды.
    def _parse_output(self, output, exit_status):
        # Применение регулярных выражений для раскраски текста.
        for pattern, color in self.color_patterns.items():
            output = re.sub(pattern, f"{color}\\g<0>\033[0m", output)
        
        # Добавление зеленого цвета для успешного вывода.
        if exit_status == 0 and output.strip():
            output = f"\033[32m{output}\033[0m"
        return output  # Возвращение обработанного вывода.

    # Метод для закрытия SSH-сессии.
    def close(self):
        self.session.disconnect()  # Отключение от SSH-сессии.

# Функция main для запуска клиента и взаимодействия с пользователем.
def main():
    hostname = input("Введите IP-адрес: ")  # Запрос IP-адреса сервера.
    username = input("Введите имя пользователя: ")  # Запрос имени пользователя.
    password = input("Введите пароль: ")  # Запрос пароля.
    port = int(input("Введите порт (стандартный SSH порт 22): ") or 22)  # Запрос порта с дефолтным значением 22.
    print("Начал подключаться к серверу")  # Информационное сообщение о начале подключения.
    try:
        # Создание объекта клиента и выполнение команд в цикле.
        client = SSHClient(hostname=hostname, username=username, password=password, port=port)
        while True:
            # Формирование и вывод приглашения для ввода команды.
            prompt = f"{username}@{hostname}:{client.cwd}# "
            command = input(prompt)  # Ввод команды пользователем.
            if command.lower() == 'exit':  # Проверка на команду выхода.
                break  # Выход из цикла.
            output = client.execute_command(command)  # Выполнение команды.
            print(output)  # Вывод результата команды.
    except Exception as e:
        print(f"Ошибка подключения: {e}")  # Вывод сообщения об ошибке.
    finally:
        client.close()  # Закрытие соединения при выходе из программы.

# Точка входа в программу.
if __name__ == "__main__":
    main()