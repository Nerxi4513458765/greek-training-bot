"""
main.py - Полный код бота с сохранением и удалением тренировок по ID
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
# ОБРАБОТЧИК ВЕБХУКОВ (ПОЛНАЯ ВЕРСИЯ)
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
    """Обработка вебхуков от Telegram с сохранением и удалением тренировок"""
    try:
        update_data = request.get_json()
        logger.info("=" * 60)
        logger.info("📩 ПОЛУЧЕН WEBHOOK")

        # Проверяем данные от Mini App
        if 'message' in update_data and 'web_app_data' in update_data['message']:
            web_app_data = update_data['message']['web_app_data']
            user_id = update_data['message']['from']['id']
            user_name = update_data['message']['from'].get('first_name', 'Герой')

            logger.info(f"🎯 Данные от Mini App от {user_name} (ID: {user_id})")
            logger.info(f"📄 Сырые данные: {web_app_data}")

            try:
                data = json.loads(web_app_data['data'])
                logger.info(f"🔍 Распарсенные данные: {json.dumps(data, ensure_ascii=False, indent=2)}")

                # ===== СОХРАНЕНИЕ ТРЕНИРОВКИ =====
                if data.get('type') == 'new_workout':
                    workout = data.get('workout', {})
                    client_id = workout.get('client_id')

                    logger.info(f"💾 СОХРАНЕНИЕ тренировки для {user_name}")
                    logger.info(f"📝 Название: {workout.get('name')}")
                    logger.info(f"📊 Упражнений: {len(workout.get('exercises', []))}")
                    logger.info(f"🆔 Клиентский ID: {client_id}")

                    # Сохраняем в базу данных
                    workout_id = db.save_workout(
                        user_id=user_id,
                        workout_name=workout.get('name', 'Тренировка'),
                        exercises=workout.get('exercises', [])
                    )

                    if workout_id:
                        logger.info(f"✅ ТРЕНИРОВКА СОХРАНЕНА! ID в БД: {workout_id}")

                        # Отправляем подтверждение пользователю в Telegram
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

                        # Здесь можно отправить обратно в Mini App реальный ID
                        # но для этого нужен отдельный механизм
                        logger.info(f"🔄 Клиентский ID: {client_id} -> Реальный ID: {workout_id}")
                    else:
                        logger.error("❌ Не удалось сохранить тренировку")

                # ===== УДАЛЕНИЕ ТРЕНИРОВКИ =====
                elif data.get('type') == 'delete_workout':
                    workout_id = data.get('workout_id')
                    logger.info(f"🗑️ ЗАПРОС НА УДАЛЕНИЕ тренировки {workout_id} от {user_name}")

                    # Удаляем из базы данных
                    with db.get_connection() as conn:
                        cursor = conn.cursor()

                        # Сначала проверяем, существует ли тренировка и принадлежит ли она пользователю
                        cursor.execute('''
                            SELECT id, workout_name FROM workouts 
                            WHERE id = ? AND user_id = ?
                        ''', (workout_id, user_id))

                        workout = cursor.fetchone()

                        if workout:
                            logger.info(f"✅ Тренировка найдена в БД: ID={workout[0]}, Название={workout[1]}")

                            # Удаляем тренировку
                            cursor.execute('''
                                DELETE FROM workouts 
                                WHERE id = ? AND user_id = ?
                            ''', (workout_id, user_id))

                            conn.commit()

                            if cursor.rowcount > 0:
                                logger.info(f"✅ ТРЕНИРОВКА {workout_id} УСПЕШНО УДАЛЕНА из БД")

                                # Отправляем подтверждение пользователю в Telegram
                                asyncio.run_coroutine_threadsafe(
                                    bot.send_message(
                                        chat_id=user_id,
                                        text=f"🗑️ <b>Тренировка удалена</b>\n\n"
                                             f"🏛️ <b>{workout[1]}</b>\n"
                                             f"🆔 ID: {workout_id}",
                                        parse_mode="HTML"
                                    ),
                                    loop
                                )
                            else:
                                logger.error(f"❌ Не удалось удалить тренировку {workout_id}")
                        else:
                            logger.warning(
                                f"⚠️ Тренировка {workout_id} не найдена в БД или принадлежит другому пользователю")

                            # Отправляем уведомление об ошибке
                            asyncio.run_coroutine_threadsafe(
                                bot.send_message(
                                    chat_id=user_id,
                                    text=f"❌ <b>Ошибка удаления</b>\n\n"
                                         f"Тренировка с ID {workout_id} не найдена в базе данных",
                                    parse_mode="HTML"
                                ),
                                loop
                            )

                else:
                    logger.warning(f"⚠️ Неизвестный тип данных: {data.get('type')}")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки данных: {e}", exc_info=True)

        # Отправляем в основной обработчик для обычных сообщений
        asyncio.run_coroutine_threadsafe(process_update(update_data), loop)

        logger.info("✅ Webhook обработан успешно")
        logger.info("=" * 60)
        return "ok", 200

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================
# ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ
# ============================================

@dp.message(Command("check_db"))
async def cmd_check_db(message: Message):
    """Проверить содержимое базы данных"""
    user_id = message.from_user.id
    workouts = db.get_user_workouts(user_id, limit=10)

    text = f"📊 <b>База данных для {message.from_user.first_name}</b>\n\n"
    text += f"👤 User ID: <code>{user_id}</code>\n"
    text += f"📚 Всего тренировок: {len(workouts)}\n\n"

    if workouts:
        text += "<b>Тренировки в БД:</b>\n"
        for w in workouts:
            date = w['date'][:10] if w.get('date') else 'неизвестно'
            text += f"• ID: {w['id']} — {w['name']} ({date})\n"
    else:
        text += "❌ Тренировок пока нет!\n"

    await message.answer(text, parse_mode="HTML")


# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)