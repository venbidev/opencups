# Олимпиадный Портал: Telegram Бот и API

## 1. Обзор

Этот проект представляет собой систему для управления олимпиадами и их результатами, состоящую из Telegram-бота для взаимодействия с пользователями и администраторами, и API для программного добавления результатов олимпиад. Система использует базу данных SQLite для хранения информации.

## 2. Структура Проекта

Проект находится в директории `/home/ubuntu/olympiad_bot/` и включает следующие основные файлы и директории:

-   `/home/ubuntu/olympiad_bot/src/` - Директория с исходным кодом.
    -   `database_setup.py`: Скрипт для создания таблиц базы данных.
    -   `main_bot.py`: Основной файл Telegram-бота.
    -   `api_server.py`: Файл FastAPI сервера для API.
-   `/home/ubuntu/olympiad_bot/olympiad_portal.db`: Файл базы данных SQLite (создается после запуска `database_setup.py`).
-   `/home/ubuntu/todo.md`: План разработки (чек-лист).
-   `/home/ubuntu/bot_logic_details.md`: Детальное описание логики работы бота и API.
-   `/home/ubuntu/testing_plan.md`: План тестирования системы.
-   `README.md` (этот файл): Инструкция по установке и использованию.

## 3. Предварительные требования

Для запуска проекта вам понадобится:
-   Python 3.8+ (в среде разработки используется Python 3.11).
-   `pip` для установки зависимостей.
-   Доступ в интернет для загрузки библиотек и работы Telegram-бота.

## 4. Установка зависимостей

Откройте терминал и выполните следующие команды для установки необходимых Python библиотек:

```bash
pip3 install python-telegram-bot==20.8
pip3 install fastapi uvicorn[standard]
```

## 5. Настройка Базы Данных

База данных SQLite будет создана автоматически при первом запуске скрипта `database_setup.py`.

1.  Перейдите в директорию с исходным кодом:
    ```bash
    cd /home/ubuntu/olympiad_bot/src
    ```
2.  Запустите скрипт для создания таблиц:
    ```bash
    python3 database_setup.py
    ```
    Это создаст файл `olympiad_portal.db` в директории `/home/ubuntu/olympiad_bot/`.

## 6. Настройка и Запуск Telegram-Бота

### 6.1. Получение Telegram Bot Token

1.  Откройте Telegram и найдите бота @BotFather.
2.  Отправьте ему команду `/newbot`.
3.  Следуйте инструкциям, чтобы задать имя и username для вашего бота. Username должен заканчиваться на "bot" (например, `MyOlympiadPortalBot`).
4.  После создания бота @BotFather предоставит вам **токен доступа (API Token)**. Скопируйте его.

### 6.2. Конфигурация Токена в Боте

1.  Откройте файл `/home/ubuntu/olympiad_bot/src/main_bot.py` в текстовом редакторе.
2.  Найдите строку:
    ```python
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Placeholder
    ```
3.  Замените `"YOUR_TELEGRAM_BOT_TOKEN"` на ваш реальный токен, полученный от @BotFather. Например:
    ```python
    TELEGRAM_BOT_TOKEN = "1234567890:ABCDEFGHIJKLMN0PQRSTUVWXYZ1234567890"
    ```
4.  Сохраните файл.

### 6.3. Назначение Администратора Бота

По умолчанию все пользователи не являются администраторами. Чтобы назначить администратора:

1.  Запустите бота (см. следующий пункт) и отправьте ему команду `/start` с того Telegram-аккаунта, который должен стать администратором. Это добавит ваш `telegram_id` в базу данных.
2.  Вам нужно будет вручную изменить запись в базе данных `olympiad_portal.db`. Вы можете использовать любой SQLite-браузер или командную строку `sqlite3`.
    Пример SQL-запроса (замените `YOUR_ADMIN_TELEGRAM_ID` на реальный ID):
    ```sql
    UPDATE Users SET is_admin = 1 WHERE telegram_id = YOUR_ADMIN_TELEGRAM_ID;
    ```
    Чтобы узнать свой `telegram_id`, вы можете временно добавить в код бота (например, в команду `/start`) вывод `update.effective_user.id`.

### 6.4. Запуск Бота

1.  Убедитесь, что вы находитесь в директории `/home/ubuntu/olympiad_bot/src/`.
2.  Запустите бота командой:
    ```bash
    python3 main_bot.py
    ```
    Если все настроено правильно, в консоли появится сообщение `Bot is starting...`, и бот начнет отвечать на команды в Telegram.

### 6.5. Команды Бота

**Для всех пользователей:**
-   `/start` - Начало работы, приветствие.
-   `/help` - Помощь по командам.
-   `/mydata` - Привязать или изменить ваш СНИЛС (необходим для просмотра результатов).
-   `/myresults` - Посмотреть ваши результаты олимпиад (по привязанному СНИЛС).
-   `/listolympiads` - Посмотреть список всех доступных олимпиад.

**Только для администраторов (после назначения через БД):**
-   `/admin_add_olympiad` - Добавить новую олимпиаду (пошаговый ввод данных).
-   `/admin_add_results` - Добавить результаты для выбранной олимпиады (пошаговый ввод данных по участникам).
-   `/admin_edit_result` - Редактировать результат олимпиады (реализована как заглушка, сообщает о неполной реализации).
-   `/cancel_admin_op` - Отмена текущей административной операции (например, добавления олимпиады).

## 7. Настройка и Запуск API Сервера

API сервер используется для программного добавления результатов олимпиад.

### 7.1. Конфигурация API Ключа

1.  Откройте файл `/home/ubuntu/olympiad_bot/src/api_server.py`.
2.  Найдите строку:
    ```python
    VALID_API_KEY = "your_secret_api_key_here"
    ```
3.  Замените `"your_secret_api_key_here"` на ваш собственный секретный ключ API. Это должен быть сложный и уникальный ключ.
4.  Сохраните файл.

### 7.2. Запуск API Сервера

1.  Убедитесь, что вы находитесь в директории `/home/ubuntu/olympiad_bot/src/`.
2.  Запустите API сервер с помощью Uvicorn:
    ```bash
    uvicorn api_server:app --host 0.0.0.0 --port 8000
    ```
    Сервер будет доступен по адресу `http://localhost:8000` (или IP-адресу машины, если доступен извне).

### 7.3. Использование API

-   **Эндпоинт**: `POST /api/v1/results`
-   **Метод**: `POST`
-   **Аутентификация**: Требуется заголовок `X-API-KEY` с вашим секретным ключом.
-   **Тело запроса (JSON)**:
    ```json
    {
      "olympiad_id": 1, // ID существующей олимпиады
      "results": [
        {
          "full_name": "Иванов Иван Иванович",
          "snils": "123-456-789 00", // Формат XXX-XXX-XXX XX
          "score": 85,
          "place": 1,
          "diploma_link": "http://example.com/diploma/1.pdf" // Опционально
        },
        {
          "full_name": "Петров Петр Петрович",
          "snils": "987-654-321 11",
          "score": 70,
          "place": 2,
          "diploma_link": null
        }
      ]
    }
    ```
-   **Пример запроса с `curl`** (замените `your_actual_api_key` и данные):
    ```bash
    curl -X POST "http://localhost:8000/api/v1/results" \
    -H "X-API-KEY: your_actual_api_key" \
    -H "Content-Type: application/json" \
    -d 
    '{ 
      "olympiad_id": 1, 
      "results": [ 
        { 
          "full_name": "Тестов Тест Тестович API", 
          "snils": "101-202-303 04", 
          "score": 95, 
          "place": 1, 
          "diploma_link": "http://example.com/api_diploma.pdf" 
        } 
      ] 
    }'
    ```

## 8. Список Предоставляемых Файлов

Вам будет предоставлен архив, содержащий следующие файлы и структуру:

```
olympiad_bot/
├── src/
│   ├── api_server.py
│   ├── database_setup.py
│   └── main_bot.py
├── bot_logic_details.md
├── testing_plan.md
├── todo.md
└── README.md  (этот файл)
```

(Файл базы данных `olympiad_portal.db` будет создан после выполнения `database_setup.py`)

---

Если у вас возникнут вопросы по установке или использованию, пожалуйста, обращайтесь.

