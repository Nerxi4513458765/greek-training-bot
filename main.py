"""
main.py - Основной файл бота для Railway
"""

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from flask import Flask, request, jsonify
from threading import Thread

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
    raise ValueError("BOT_TOKEN must be set in environment variables")

# URL для вебхука
RAILWAY_URL = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'greek-training-bot-production-2cc5.up.railway.app')
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"https://{RAILWAY_URL}{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Flask приложение
app = Flask(__name__)

# === ВСЕ ОБРАБОТЧИКИ ЗДЕСЬ ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Команда /start от {message.from_user.id}")
    await message.answer(
        "✅ <b>Бот работает на Railway!</b>\n\n"
        "Доступные команды:\n"
        "/help - помощь\n"
        "/test - тест\n"
        "/stats - статистика",
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"Команда /help от {message.from_user.id}")
    await message.answer(
        "📋 <b>Доступные команды:</b>\n\n"
        "/start - Приветствие\n"
        "/help - Эта справка\n"
        "/test - Тестовая команда\n"
        "/stats - Статистика",
        parse_mode="HTML"
    )

@dp.message(Command("test"))
async def cmd_test(message: Message):
    logger.info(f"Команда /test от {message.from_user.id}")
    await message.answer("✅ Тест пройден успешно!")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    logger.info(f"Команда /stats от {message.from_user.id}")
    # Заглушка для статистики
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "Пока в разработке...",
        parse_mode="HTML"
    )

@dp.message()
async def echo(message: Message):
    """Обработчик всех остальных сообщений"""
    logger.info(f"Сообщение от {message.from_user.id}: {message.text}")
    await message.answer(f"Ты написал: {message.text}")

# === АСИНХРОННЫЙ ЦИКЛ ===
loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

thread = Thread(target=start_loop, daemon=True)
thread.start()
logger.info("✅ Асинхронный цикл запущен")

# === FLASK МАРШРУТЫ ===
@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Бот работает на Railway",
        "webhook": WEBHOOK_URL
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": "running"})

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    try:
        logger.info("📩 Получен webhook запрос")
        update_data = request.get_json()
        logger.info(f"📄 Update ID: {update_data.get('update_id')}")
        
        future = asyncio.run_coroutine_threadsafe(
            handle_update(update_data), 
            loop
        )
        future.result(timeout=5)
        
        return "ok", 200
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return jsonify({"error": str(e)}), 500

async def handle_update(update_data):
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        logger.info(f"✅ Update {update_data.get('update_id')} обработан")
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_update: {e}")

async def setup_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        info = await bot.get_webhook_info()
        logger.info(f"✅ Вебхук установлен: {info.url}")
        return info
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        return None

# Устанавливаем вебхук
try:
    future = asyncio.run_coroutine_threadsafe(setup_webhook(), loop)
    future.result(timeout=10)
    logger.info("✅ Бот готов к работе!")
except Exception as e:
    logger.error(f"❌ Ошибка при запуске: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)ическая ошибка: {e}", exc_info=True)
