Документация к файлу settings (Python):

---

# Summary

Этот модуль загружает переменные окружения из файла .env в корне проекта с помощью библиотеки python-dotenv. Предназначен для централизованного доступа к параметрам внешних сервисов (OpenAI, Telegram) в проекте на Python/Django.

---

# Структура и назначение

- BASE_DIR: Абсолютный путь к корню проекта, определяется через pathlib.
- load_dotenv(...): Загружает переменные окружения из файла .env, расположенного в BASE_DIR проекта.
- OPENAI_API_KEY: Ключ API OpenAI (str).
- OPENAI_ASSISTANT_ID: ID ассистента OpenAI (str).
- OPENAI_MODEL: Название используемой модели OpenAI (str, по умолчанию 'gpt-4o').
- TELEGRAM_BOT_TOKEN: Токен Telegram-бота (str).
- TELEGRAM_CHAT_ID: Telegram chat ID (str/int).
- TELEGRAM_CHANNEL_ID: Telegram channel ID (str/int).

---

# Использование
- Все параметры автоматически подтягиваются из .env после импорта модуля, доступны как переменные модуля Python.
- Настоятельно рекомендуется добавить .env в .gitignore для безопасности.

---

# Пример .env-файла
OPENAI_API_KEY=sk-...
OPENAI_ASSISTANT_ID=asst-...
OPENAI_MODEL=gpt-4o
TELEGRAM_BOT_TOKEN=123:AA...
TELEGRAM_CHAT_ID=12345678
TELEGRAM_CHANNEL_ID=@your_channel

# Рекомендации
- Для изменения конфигурации достаточно поправить .env без пересборки проекта.
- Проверяй, что переменные окружения присутствуют перед их использованием (особенно для ключей).