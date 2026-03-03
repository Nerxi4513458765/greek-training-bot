"""
main.py - Полный код бота с удалением тренировок по дате
"""

import asyncio
import logging
import os
import sys
import json
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
    logger.warning(f"⚠️ RAILWAY_PUBLIC_DOMAIN не задан, использую {RAILWAY_URL}")

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
# АСИНХРОННЫЙ ЦИКЛ
# ============================================

loop = asyncio.new_event_loop()


def run_async_loop():
    """Запускает и держит асинхронный цикл"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


# Запускаем цикл в отдельном потоке
thread = Thread(target=run_async_loop, daemon=True)
thread.start()
logger.info("✅ Асинхронный цикл запущен")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def process_update(update_data):
    """Обработка обновления от Telegram"""
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"❌ Ошибка process_update: {e}")


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
    logger.info(f"🌐 WEB_APP_URL: {WEB_APP_URL}")
except Exception as e:
    logger.error(f"❌ Ошибка при запуске: {e}")


# ============================================
# ОБРАБОТЧИК ВЕБХУКОВ
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
        logger.info("=" * 60)

        # Проверяем данные от Mini App
        if 'message' in update_data and 'web_app_data' in update_data['message']:
            web_app_data = update_data['message']['web_app_data']
            user_id = update_data['message']['from']['id']
            user_name = update_data['message']['from'].get('first_name', 'Герой')

            try:
                data = json.loads(web_app_data['data'])
                logger.info(f"📦 Тип: {data.get('type')} от {user_name}")

                # ===== СОХРАНЕНИЕ ТРЕНИРОВКИ =====
                if data.get('type') == 'new_workout':
                    workout = data.get('workout', {})

                    logger.info(f"💾 Сохранение: {workout.get('name')}")

                    workout_id = db.save_workout(
                        user_id=user_id,
                        workout_name=workout.get('name', 'Тренировка'),
                        exercises=workout.get('exercises', [])
                    )

                    if workout_id:
                        logger.info(f"✅ Сохранено с ID {workout_id}")

                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id=user_id,
                                text=f"✅ <b>Тренировка сохранена!</b>",
                                parse_mode="HTML"
                            ),
                            loop
                        )

                # ===== УДАЛЕНИЕ ТРЕНИРОВКИ ПО ДАТЕ =====
                elif data.get('type') == 'delete_workout_by_date':
                    iso_date = data.get('date')
                    logger.info(f"🗑️ Удаление тренировки от {iso_date}")

                    # Конвертируем ISO дату в формат SQLite
                    try:
                        # Из "2026-03-03T18:28:37.277Z" в "2026-03-03 18:28:37"
                        date_obj = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
                        sqlite_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f"🔄 Конвертировано: {sqlite_date}")

                        with db.get_connection() as conn:
                            cursor = conn.cursor()

                            # Находим тренировку
                            cursor.execute('''
                                SELECT id, workout_name FROM workouts 
                                WHERE user_id = ? AND workout_date = ?
                            ''', (user_id, sqlite_date))

                            workout = cursor.fetchone()

                            if workout:
                                logger.info(f"✅ Найдена: {workout[1]}")

                                cursor.execute('''
                                    DELETE FROM workouts 
                                    WHERE user_id = ? AND workout_date = ?
                                ''', (user_id, sqlite_date))

                                conn.commit()
                                logger.info(f"✅ Тренировка удалена")

                                asyncio.run_coroutine_threadsafe(
                                    bot.send_message(
                                        chat_id=user_id,
                                        text=f"🗑️ Тренировка удалена",
                                        parse_mode="HTML"
                                    ),
                                    loop
                                )
                            else:
                                logger.warning(f"⚠️ Тренировка не найдена")

                                asyncio.run_coroutine_threadsafe(
                                    bot.send_message(
                                        chat_id=user_id,
                                        text=f"❌ Тренировка от {iso_date[:16]} не найдена",
                                        parse_mode="HTML"
                                    ),
                                    loop
                                )

                    except Exception as e:
                        logger.error(f"❌ Ошибка конвертации даты: {e}")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки: {e}")

        # Отправляем в основной обработчик
        asyncio.run_coroutine_threadsafe(process_update(update_data), loop)

        return "ok", 200

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск на порту {port}")
    app.run(host='0.0.0.0', port=port)
