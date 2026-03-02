import os
from dotenv import load_dotenv

# Загружаем .env только для локальной разработки
if os.path.exists('.env'):
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан! Добавь его в переменные окружения Railway")

if not WEB_APP_URL:
    raise ValueError("❌ WEB_APP_URL не задан! Добавь его в переменные окружения Railway")
