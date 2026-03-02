"""
webhook_bot.py - Версия бота для PythonAnywhere с вебхуками
"""

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from flask import Flask, request, jsonify

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN') or "твой_токен_сюда"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://твой-логин.pythonanywhere.com{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Flask приложение
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает!", 200

@app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": "running"}), 200

@app.route(WEBHOOK_PATH, methods=['POST'])
async def webhook():
    """Обработка вебхуков от Telegram"""
    try:
        update = types.Update(**request.json)
        await dp.feed_update(bot, update)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return 'error', 500

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("✅ Бот работает на PythonAnywhere!")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Доступные команды:\n/start - Приветствие\n/help - Эта справка")

async def on_startup():
    """Действия при запуске"""
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Вебхук установлен на {WEBHOOK_URL}")

async def on_shutdown():
    """Действия при остановке"""
    await bot.delete_webhook()
    logger.info("❌ Вебхук удалён")

def run_flask():
    """Запуск Flask приложения"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(on_startup())
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))

if __name__ == "__main__":
    run_flask()