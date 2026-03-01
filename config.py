import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

if not BOT_TOKEN:
    raise ValueError("Нет токена! Создай файл .env и добавь BOT_TOKEN=твой_токен")
if not WEB_APP_URL:
    raise ValueError("Нет ссылки на Mini App! Добавь WEB_APP_URL=твоя_ссылка")
