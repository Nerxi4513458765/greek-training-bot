"""
main.py - Полный греческий бот для Railway с сохранением тренировок
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
logger.info("✅ Асинхронный цикл запущен и работает постоянно")


# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@dp.message(Command("check_db"))
async def cmd_check_db(message: Message):
    """Проверить содержимое базы данных"""
    user_id = message.from_user.id
    logger.info(f"📊 {message.from_user.first_name} проверяет БД")

    try:
        workouts = db.get_user_workouts(user_id)

        text = f"📊 <b>База данных для {message.from_user.first_name}</b>\n\n"
        text += f"👤 User ID: <code>{user_id}</code>\n"
        text += f"📚 Всего тренировок: {len(workouts)}\n\n"

        if workouts:
            text += "<b>Последние тренировки:</b>\n"
            for w in workouts[-5:][::-1]:  # последние 5 в обратном порядке
                date = w.get('date', '')[:10] if w.get('date') else 'неизвестно'
                text += f"• {w.get('name', 'Без названия')} ({date}) — {len(w.get('exercises', []))} упр.\n"
        else:
            text += "❌ Тренировок пока нет!\n"
            text += "\n💡 Создай тренировку в Mini App и проверь снова."

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"❌ Ошибка в check_db: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("clear_my_workouts"))
async def cmd_clear_workouts(message: Message):
    """Очистить свои тренировки (для тестов)"""
    user_id = message.from_user.id

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workouts WHERE user_id = ?", (user_id,))
            conn.commit()
            deleted = cursor.rowcount

        await message.answer(f"✅ Удалено {deleted} тренировок")
        logger.info(f"🧹 {message.from_user.first_name} очистил свои тренировки")
    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {e}")
        await message.answer(f"❌ Ошибка: {e}")


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
    logger.info(f"🌐 WEB_APP_URL: {WEB_APP_URL}")
except Exception as e:
    logger.error(f"❌ Ошибка при запуске: {e}")


# ============================================
# FLASK МАРШРУТЫ (С ОБРАБОТКОЙ ДАННЫХ ИЗ MINI APP)
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
    """Обработка вебхуков от Telegram с сохранением тренировок"""
    try:
        update_data = request.get_json()
        logger.info("=" * 50)
        logger.info("📩 ПОЛУЧЕН WEBHOOK ЗАПРОС")

        # Проверяем, есть ли данные от Mini App
        if 'message' in update_data:
            message = update_data['message']

            # Проверяем наличие web_app_data
            if 'web_app_data' in message:
                web_app_data = message['web_app_data']
                logger.info("🎯 НАЙДЕНЫ ДАННЫЕ ИЗ MINI APP!")
                logger.info(f"📄 Сырые данные: {web_app_data}")

                try:
                    # Парсим JSON из Mini App
                    data = json.loads(web_app_data['data'])
                    logger.info(f"🔍 Распарсенные данные: {json.dumps(data, indent=2, ensure_ascii=False)}")

                    # Проверяем тип данных
                    if data.get('type') == 'new_workout':
                        workout = data.get('workout', {})
                        user_id = message['from']['id']
                        user_name = message['from'].get('first_name', 'Герой')

                        logger.info(f"👤 Пользователь: {user_name} (ID: {user_id})")
                        logger.info(f"💪 Название тренировки: {workout.get('name')}")
                        logger.info(f"📊 Количество упражнений: {len(workout.get('exercises', []))}")

                        # Сохраняем в базу данных
                        try:
                            workout_id = db.save_workout(
                                user_id=user_id,
                                workout_name=workout.get('name', 'Тренировка'),
                                exercises=workout.get('exercises', [])
                            )

                            if workout_id:
                                logger.info(f"✅ ТРЕНИРОВКА УСПЕШНО СОХРАНЕНА! ID: {workout_id}")

                                # Отправляем подтверждение пользователю
                                asyncio.run_coroutine_threadsafe(
                                    bot.send_message(
                                        chat_id=user_id,
                                        text=f"✅ <b>Тренировка сохранена!</b>\n\n"
                                             f"🏛️ <b>{workout.get('name', 'Тренировка')}</b>\n"
                                             f"📋 Упражнений: {len(workout.get('exercises', []))}\n"
                                             f"🆔 ID: {workout_id}",
                                        parse_mode="HTML"
                                    ),
                                    loop
                                )
                            else:
                                logger.error("❌ Не удалось сохранить тренировку")

                        except Exception as e:
                            logger.error(f"❌ Ошибка сохранения в БД: {e}", exc_info=True)

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка парсинга JSON: {e}")
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки данных Mini App: {e}", exc_info=True)

        # Отправляем обработку в асинхронный цикл для обычных сообщений
        asyncio.run_coroutine_threadsafe(
            process_update(update_data),
            loop
        )

        logger.info("✅ Webhook обработан успешно")
        logger.info("=" * 50)
        return "ok", 200

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================
# ЗАПУСК FLASK
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)

