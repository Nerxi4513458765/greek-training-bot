"""
main.py - Полный греческий бот для Railway
Со всеми хендлерами, базой данных и вебхуками
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from flask import Flask, request, jsonify

# Импортируем свои модули
from database import Database
from config import BOT_TOKEN, WEB_APP_URL
from handlers import start, oracle, chronicles, trials, info

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Конфигурация
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    raise ValueError("BOT_TOKEN must be set in environment variables")

# URL для вебхука
RAILWAY_URL = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if not RAILWAY_URL:
    logger.warning("⚠️ RAILWAY_PUBLIC_DOMAIN не задан, использую localhost")
    RAILWAY_URL = "localhost:8000"

WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"https://{RAILWAY_URL}{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных
db = Database()

# Flask приложение
app = Flask(__name__)

# ============================================
# ПОДКЛЮЧАЕМ ВСЕ ОБРАБОТЧИКИ ИЗ ПАПКИ HANDLERS
# ============================================

dp.include_router(start.router)
dp.include_router(oracle.router)
dp.include_router(chronicles.router)
dp.include_router(trials.router)
dp.include_router(info.router)

# ============================================
# АСИНХРОННЫЙ ЦИКЛ
# ============================================

loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

thread = Thread(target=start_loop, daemon=True)
thread.start()
logger.info("✅ Асинхронный цикл запущен")

# ============================================
# ОБРАБОТЧИК ДАННЫХ ИЗ MINI APP
# ============================================

async def handle_web_app_data(update_data):
    """Обработка данных из Mini App"""
    try:
        # Здесь будет логика сохранения тренировок
        logger.info(f"📦 Данные из Mini App: {update_data}")
        # TODO: реализовать сохранение в БД
    except Exception as e:
        logger.error(f"❌ Ошибка обработки данных Mini App: {e}")

# ============================================
# FLASK МАРШРУТЫ
# ============================================

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "🏛️ Чертог тренировок работает на Railway",
        "webhook": WEBHOOK_URL,
        "version": "full",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "bot": "running",
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    })

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обработка вебхуков от Telegram"""
    try:
        logger.info("📩 Получен webhook запрос")
        update_data = request.get_json()
        
        # Особый тип данных из Mini App
        if update_data and 'web_app_data' in update_data:
            # Это данные из Mini App
            asyncio.run_coroutine_threadsafe(
                handle_web_app_data(update_data),
                loop
            )
        else:
            # Обычное обновление от Telegram
            future = asyncio.run_coroutine_threadsafe(
                process_update(update_data),
                loop
            )
            future.result(timeout=5)
        
        return "ok", 200
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

async def process_update(update_data):
    """Асинхронная обработка обновления"""
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        logger.info(f"✅ Update {update_data.get('update_id')} обработан")
    except Exception as e:
        logger.error(f"❌ Ошибка в process_update: {e}")

async def setup_webhook():
    """Установка вебхука"""
    try:
        await bot.set_webhook(WEBHOOK_URL)
        info = await bot.get_webhook_info()
        logger.info(f"✅ Вебхук установлен: {info.url}")
        return info
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        return None

# ============================================
# ЗАПУСК
# ============================================

# Устанавливаем вебхук
try:
    future = asyncio.run_coroutine_threadsafe(setup_webhook(), loop)
    future.result(timeout=10)
    logger.info("✅ Бот готов к работе!")
    logger.info(f"🌐 WEB_APP_URL: {WEB_APP_URL}")
except Exception as e:
    logger.error(f"❌ Ошибка при запуске: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)
