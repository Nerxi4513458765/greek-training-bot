"""
webhook_bot.py - Рабочая версия для PythonAnywhere
Использует Flask + aiogram с правильной обработкой вебхуков
"""

import logging
import os
import sys
from flask import Flask, request, jsonify
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    # Для теста можно указать временно
    BOT_TOKEN = "твой_токен_сюда"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://nerxi.pythonanywhere.com{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Flask приложение
app = Flask(__name__)


# Регистрируем обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("✅ Бот работает на PythonAnywhere!")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Приветствие\n"
        "/help - Эта справка"
    )


@dp.message()
async def echo(message: Message):
    await message.answer(f"Ты написал: {message.text}")


# Flask маршруты
@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Бот работает",
        "webhook": WEBHOOK_URL
    })


@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "bot": "running",
        "webhook_set": webhook_status
    })


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обработка вебхуков от Telegram"""
    try:
        logger.info(f"📩 Получен webhook запрос")

        # Получаем обновление от Telegram
        update_data = request.get_json()
        logger.info(f"📄 Данные: {update_data}")

        # Создаем событие для асинхронной обработки
        asyncio.run(handle_update(update_data))

        return 'ok', 200
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


async def handle_update(update_data):
    """Асинхронная обработка обновления"""
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_update: {e}", exc_info=True)


# Функция для установки вебхука
def setup_webhook():
    """Устанавливает вебхук при запуске"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def set_webhook():
            await bot.set_webhook(WEBHOOK_URL)
            info = await bot.get_webhook_info()
            logger.info(f"✅ Вебхук установлен: {info.url}")
            return info

        webhook_info = loop.run_until_complete(set_webhook())
        logger.info(f"✅ Вебхук активен: {webhook_info.url}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        return False


# Устанавливаем вебхук при запуске
webhook_status = setup_webhook()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))