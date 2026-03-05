"""
main.py - Полный код с отправкой плана в Telegram
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
from handlers import start, chronicles, trials, info, trainer

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
dp.include_router(trainer.router)
dp.include_router(chronicles.router)
dp.include_router(trials.router)
dp.include_router(info.router)

# ============================================
# АСИНХРОННЫЙ ЦИКЛ
# ============================================

loop = asyncio.new_event_loop()


def run_async_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()


thread = Thread(target=run_async_loop, daemon=True)
thread.start()
logger.info("✅ Асинхронный цикл запущен")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def process_update(update_data):
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"❌ Ошибка process_update: {e}")


async def setup_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        info = await bot.get_webhook_info()
        logger.info(f"✅ Вебхук установлен: {info.url}")
        return info
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        return None


try:
    future = asyncio.run_coroutine_threadsafe(setup_webhook(), loop)
    future.result(timeout=10)
    logger.info("✅ Бот готов к работе!")
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


# ===== ГЕНЕРАЦИЯ ПЛАНА =====
@app.route('/get_plan', methods=['POST', 'OPTIONS'])
def get_plan():
    print("\n" + "=" * 60)
    print("🔥🔥🔥 ЗАПРОС НА /get_plan ПОЛУЧЕН 🔥🔥🔥")

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'preflight ok'})
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response, 200

    try:
        data = request.get_json()
        user_id = data.get('user_id')
        focus = data.get('focus', 'все')

        print(f"📋 Параметры: user_id={user_id}, focus={focus}")

        if user_id == 0:
            user_id = 12345
            print("⚠️ Тестовый режим")

        # Генерируем план
        plan = db.generate_weekly_plan(user_id, focus)

        # Сохраняем план в БД
        plan_json = json.dumps(plan, ensure_ascii=False)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_plans (user_id, plan_name, focus_muscle, week_plan)
                VALUES (?, ?, ?, ?)
            ''', (user_id, f'План на неделю ({focus})', focus, plan_json))
            conn.commit()

        # Формируем красивое сообщение
        plan_message = f"🏋️ <b>Твой план на неделю (фокус: {focus})</b>\n\n"

        days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        day_names = {
            'понедельник': '🌙 ПОНЕДЕЛЬНИК', 'вторник': '🔥 ВТОРНИК', 'среда': '💧 СРЕДА',
            'четверг': '🌪️ ЧЕТВЕРГ', 'пятница': '⚡ ПЯТНИЦА', 'суббота': '✨ СУББОТА', 'воскресенье': '☀️ ВОСКРЕСЕНЬЕ'
        }

        for day in days:
            if day in plan:
                day_plan = plan[day]
                if day_plan['exercises']:
                    plan_message += f"<b>{day_names.get(day, day)}</b>\n"
                    plan_message += f"<code>{'=' * 30}</code>\n"

                    for i, ex in enumerate(day_plan['exercises'], 1):
                        intensity = '🔴 Тяжёлая' if ex['sets'] >= 5 else ('🟢 Лёгкая' if ex['sets'] <= 3 else '🟡 Средняя')
                        plan_message += f"{i}. {ex['name']}\n"
                        plan_message += f"   {intensity} | {ex['sets']}×{ex['reps']} | {ex['weight']} кг\n"

                    plan_message += "\n"
                else:
                    plan_message += f"<b>{day_names.get(day, day)}</b> — 😴 Отдых\n\n"

        plan_message += "✏️ <i>Открой Mini App, чтобы отредактировать план</i>"

        # Отправляем в Telegram
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=user_id,
                text=plan_message,
                parse_mode="HTML"
            ),
            loop
        )

        # Отправляем подтверждение в Mini App
        response_data = {'success': True, 'message': 'План отправлен в Telegram'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        return response, 200

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({'success': False, 'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        return response, 500


# ===== ПОЛУЧЕНИЕ СОХРАНЁННОГО ПЛАНА =====
@app.route('/get_user_plan', methods=['POST', 'OPTIONS'])
def get_user_plan():
    """Получить сохранённый план пользователя"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'preflight ok'})
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response, 200

    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if user_id == 0:
            user_id = 12345

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT week_plan, focus_muscle FROM user_plans 
                WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))

            row = cursor.fetchone()

            if row:
                plan = json.loads(row[0])
                response_data = {
                    'success': True,
                    'plan': plan,
                    'focus': row[1]
                }
            else:
                response_data = {'success': False, 'error': 'План не найден'}

        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        return response, 200

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        response = jsonify({'success': False, 'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', 'https://nerxi4513458765.github.io')
        return response, 500


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    try:
        update_data = request.get_json()
        logger.info("=" * 60)

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

                # ===== УДАЛЕНИЕ ПО ДАТЕ =====
                elif data.get('type') == 'delete_workout_by_date':
                    iso_date = data.get('date')
                    logger.info(f"🗑️ Удаление тренировки от {iso_date}")

                    date_part = iso_date.split('T')[0]

                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            DELETE FROM workouts 
                            WHERE user_id = ? AND DATE(workout_date) = ?
                        ''', (user_id, date_part))
                        conn.commit()
                        deleted = cursor.rowcount

                        if deleted > 0:
                            logger.info(f"✅ Удалено {deleted} тренировок")
                            asyncio.run_coroutine_threadsafe(
                                bot.send_message(
                                    chat_id=user_id,
                                    text=f"🗑️ <b>Тренировка удалена</b>",
                                    parse_mode="HTML"
                                ),
                                loop
                            )
                        else:
                            logger.warning(f"⚠️ Тренировки не найдены")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки данных: {e}")

        asyncio.run_coroutine_threadsafe(process_update(update_data), loop)
        return "ok", 200

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ
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
        text += "<b>Последние тренировки:</b>\n"
        for w in workouts[:5]:
            text += f"• ID: {w['id']} — {w['name']}\n"
    else:
        text += "❌ Тренировок пока нет\n"

    await message.answer(text, parse_mode="HTML")


# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Запуск на порту {port}")
    app.run(host='0.0.0.0', port=port)