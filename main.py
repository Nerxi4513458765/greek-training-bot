"""
main.py - Исправленная версия для Railway
С постоянным циклом asyncio
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
    raise ValueError("❌ BOT_TOKEN не задан!")

# URL для вебхука
RAILWAY_URL = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if not RAILWAY_URL:
    RAILWAY_URL = "greek-training-bot-production-2cc5.up.railway.app"

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
# ПОДКЛЮЧАЕМ ВСЕ ОБРАБОТЧИКИ
# ============================================

dp.include_router(start.router)
dp.include_router(oracle.router)
dp.include_router(chronicles.router)
dp.include_router(trials.router)
dp.include_router(info.router)

# ============================================
# АСИНХРОННЫЙ ЦИКЛ (ПРАВИЛЬНАЯ ВЕРСИЯ)
# ============================================

loop = asyncio.new_event_loop()


def run_async_loop():
    """Запускает и держит асинхронный цикл"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


# Запускаем цикл в отдельном потоке
thread = Thread(target=run_async_loop, daemon=True)
thread.start()
logger.info("✅ Асинхронный цикл запущен и работает постоянно")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def process_update(update_data):
    """Обработка обновления от Telegram"""
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        logger.info(f"✅ Update {update_data.get('update_id', '?')} обработан")
    except Exception as e:
        logger.error(f"❌ Ошибка process_update: {e}", exc_info=True)


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


# Устанавливаем вебхук
try:
    future = asyncio.run_coroutine_threadsafe(setup_webhook(), loop)
    future.result(timeout=10)
    logger.info("✅ Бот готов к работе!")
except Exception as e:
    logger.error(f"❌ Ошибка при запуске: {e}")


# ============================================
# FLASK МАРШРУТЫ
# ============================================

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "🏛️ Чертог тренировок работает",
        "webhook": WEBHOOK_URL
    })


@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "bot": "running",
        "timestamp": datetime.now().isoformat()
    })


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обработка вебхуков от Telegram"""
    try:
        update_data = request.get_json()
        logger.info(f"📩 Webhook received, update_id: {update_data.get('update_id', '?')}")

        # Отправляем обработку в асинхронный цикл
        asyncio.run_coroutine_threadsafe(
            process_update(update_data),
            loop
        )

        return "ok", 200
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# ЗАПУСК FLASK
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)