"""
Главный файл запуска бота
Чертог тренировок - Древняя Греция встречает тёмное фэнтези
Поддержка локального запуска (polling) и Render.com (webhook)
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command

from database import Database
from config import BOT_TOKEN, WEB_APP_URL
from handlers import start, oracle, chronicles, trials, info

# Оптимизация для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаём объект базы данных
db = Database()

# Определяем, работаем ли мы на Render
ON_RENDER = os.environ.get('RENDER', False)
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', None)

# Настройки для вебхуков
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}" if RENDER_URL else None

# ЗАМЕНИ НА СВОЙ TELEGRAM ID (узнай у @userinfobot)
ADMIN_ID = 7483916545  # ← ВСТАВЬ СВОЙ ID СЮДА!


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id == ADMIN_ID


async def main():
    """Запуск бота"""
    logger.info("🏛 Чертог тренировок открывается...")
    start_time = datetime.now()

    # Создаём бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаём диспетчер
    dp = Dispatcher()

    # ===========================================
    # АДМИН-КОМАНДЫ
    # ===========================================

    @dp.message(Command("admin_clear_all"))
    async def cmd_admin_clear(message: Message):
        """Очистить все тренировки у всех пользователей"""

        if not is_admin(message.from_user.id):
            await message.answer("⛔ Доступ запрещён")
            return

        await message.answer(
            "⚠️ <b>ВНИМАНИЕ!</b>\n"
            "Это удалит ВСЕ тренировки у ВСЕХ пользователей.\n"
            "Для подтверждения отправь:\n"
            "<code>/confirm_clear YES</code>",
            parse_mode=ParseMode.HTML
        )

    @dp.message(Command("confirm_clear"))
    async def cmd_confirm_clear(message: Message):
        """Подтверждение очистки базы данных"""

        if not is_admin(message.from_user.id):
            return

        args = message.text.split()
        if len(args) < 2 or args[1] != "YES":
            await message.answer("❌ Неверное подтверждение")
            return

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Получаем статистику до удаления
                cursor.execute("SELECT COUNT(*) FROM workouts")
                workouts_before = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM workout_templates")
                templates_before = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]

                # Удаляем тренировки и шаблоны
                cursor.execute("DELETE FROM workout_templates")
                templates_deleted = cursor.rowcount
                cursor.execute("DELETE FROM workouts")
                workouts_deleted = cursor.rowcount

                conn.commit()

            await message.answer(
                f"✅ <b>База данных очищена!</b>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• 👤 Пользователей: {users_count}\n"
                f"• 🗑️ Удалено тренировок: {workouts_deleted} (было {workouts_before})\n"
                f"• 🗑️ Удалено шаблонов: {templates_deleted} (было {templates_before})\n\n"
                f"Пользователи сохранены.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка при очистке БД: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("admin_stats"))
    async def cmd_admin_stats(message: Message):
        """Показать полную статистику бота (только для админа)"""

        if not is_admin(message.from_user.id):
            await message.answer("⛔ Доступ запрещён")
            return

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Общая статистика
                cursor.execute("SELECT COUNT(*) FROM users")
                users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM workouts")
                workouts = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM workout_templates")
                templates = cursor.fetchone()[0]

                # Топ пользователей по тренировкам
                cursor.execute("""
                    SELECT u.first_name, u.username, COUNT(w.id) as workout_count
                    FROM users u
                    LEFT JOIN workouts w ON u.user_id = w.user_id
                    GROUP BY u.user_id
                    ORDER BY workout_count DESC
                    LIMIT 5
                """)
                top_users = cursor.fetchall()

                # Последние 5 тренировок
                cursor.execute("""
                    SELECT w.id, u.first_name, w.workout_name, w.workout_date
                    FROM workouts w
                    JOIN users u ON w.user_id = u.user_id
                    ORDER BY w.workout_date DESC
                    LIMIT 5
                """)
                last_workouts = cursor.fetchall()

            text = f"📊 <b>АДМИН-СТАТИСТИКА</b>\n\n"
            text += f"<b>Общая статистика:</b>\n"
            text += f"• 👤 Пользователей: {users}\n"
            text += f"• 🏋️ Тренировок: {workouts}\n"
            text += f"• 📋 Шаблонов: {templates}\n\n"

            if top_users:
                text += f"<b>Топ пользователей:</b>\n"
                for user in top_users:
                    name = user[0] or 'Неизвестно'
                    username = f"(@{user[1]})" if user[1] else ''
                    count = user[2] or 0
                    text += f"• {name} {username} — {count} тренировок\n"

            if last_workouts:
                text += f"\n<b>Последние тренировки:</b>\n"
                for w in last_workouts:
                    date = datetime.fromisoformat(w[3]).strftime("%d.%m %H:%M")
                    text += f"• {w[1]}: {w[2]} ({date})\n"

            await message.answer(text, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ===========================================
    # ПОДКЛЮЧАЕМ РОУТЕРЫ ИЗ ДРУГИХ ФАЙЛОВ
    # ===========================================

    dp.include_router(start.router)
    dp.include_router(oracle.router)
    dp.include_router(chronicles.router)
    dp.include_router(trials.router)
    dp.include_router(info.router)

    # ===========================================
    # ОБРАБОТЧИК ДАННЫХ ИЗ MINI APP
    # ===========================================

    @dp.message(F.content_type == 'web_app_data')
    async def handle_web_app_data(message: Message):
        """Обработка данных из Mini App с названиями тренировок"""
        try:
            logger.info("=" * 50)
            logger.info("📩 ПОЛУЧЕН ЗАПРОС ОТ MINI APP")
            logger.info(f"👤 Пользователь: {message.from_user.id} ({message.from_user.first_name})")

            if not message.web_app_data:
                logger.error("❌ Нет web_app_data в сообщении!")
                return

            # Парсим данные
            raw_data = message.web_app_data.data
            logger.info(f"📄 Данные: {raw_data}")

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
                await message.answer("❌ Ошибка формата данных")
                return

            user_id = message.from_user.id

            # Проверяем тип данных
            if data.get('type') == 'new_workout':
                workout = data.get('workout', {})
                workout_name = workout.get('name', 'Тренировка')
                exercises = workout.get('exercises', [])

                logger.info(f"🏋️ Название: {workout_name}")
                logger.info(f"📊 Упражнений: {len(exercises)}")

                if not exercises:
                    await message.answer("❌ Нет упражнений для сохранения")
                    return

                # Сохраняем тренировку
                try:
                    workout_id = db.save_workout(
                        user_id=user_id,
                        workout_name=workout_name,
                        exercises=exercises
                    )

                    # Формируем ответ
                    exercises_list = "\n".join([
                        f"  {i}. {ex.get('name')} — {ex.get('sets')}×{ex.get('reps')} × {ex.get('weight')}кг"
                        for i, ex in enumerate(exercises[:5], 1)
                    ])

                    if len(exercises) > 5:
                        exercises_list += f"\n  ... и ещё {len(exercises) - 5}"

                    await message.answer(
                        f"✅ <b>Тренировка сохранена!</b>\n\n"
                        f"🏛️ <b>{workout_name}</b>\n"
                        f"📋 <b>Упражнения:</b>\n{exercises_list}\n\n"
                        f"📊 <b>Всего:</b> {len(exercises)} упражнений\n"
                        f"🆔 <b>ID:</b> {workout_id}",
                        parse_mode=ParseMode.HTML
                    )

                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения: {e}")
                    await message.answer("❌ Ошибка сохранения тренировки")

            elif data.get('type') == 'delete_workout':
                workout_id = data.get('workout_id')
                if workout_id:
                    db.delete_workout(workout_id)
                    await message.answer(f"🗑️ Тренировка {workout_id} удалена")

            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка")

    # ===========================================
    # ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ
    # ===========================================

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        """Помощь по командам"""
        help_text = """
🆘 <b>Помощь по Чертогу</b>

<b>Основные команды:</b>
/start — Запустить бота
/help — Показать эту помощь
/stats — Моя статистика
/workouts — Последние тренировки

<b>Как пользоваться:</b>
1️⃣ Нажми кнопку «⚔️ ВОЙТИ В ЧЕРТОГ ТРЕНИРОВОК»
2️⃣ В приложении создай тренировку с названием
3️⃣ Добавь упражнения и сохрани
4️⃣ Смотри историю в разделе «📜 ХРОНИКИ»

<b>Советы:</b>
• Давай тренировкам эпичные названия
• Сохраняй шаблоны для частых тренировок
• Следи за статистикой

🏛️ <i>Слава героям!</i>
        """
        await message.answer(help_text, parse_mode=ParseMode.HTML)

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message):
        """Показать статистику пользователя"""
        user_id = message.from_user.id
        stats = db.get_workout_stats(user_id)
        workouts = db.get_user_workouts(user_id, limit=3)

        text = f"📊 <b>Статистика героя {message.from_user.first_name}</b>\n\n"
        text += f"🏛️ <b>Всего тренировок:</b> {stats['total_workouts']}\n"
        text += f"💪 <b>Всего упражнений:</b> {stats['total_exercises']}\n"
        text += f"🏋️ <b>Поднято кг:</b> {stats['total_weight']:.0f}\n"
        text += f"🔄 <b>Уникальных упражнений:</b> {stats['unique_exercises']}\n\n"

        if workouts:
            text += "<b>Последние подвиги:</b>\n"
            for w in workouts:
                date = datetime.fromisoformat(w['date']).strftime("%d.%m.%Y %H:%M")
                text += f"• {date} — {w['name']} ({len(w['exercises'])} упр.)\n"

        await message.answer(text, parse_mode=ParseMode.HTML)

    @dp.message(Command("workouts"))
    async def cmd_workouts(message: Message):
        """Показать последние тренировки"""
        user_id = message.from_user.id
        workouts = db.get_user_workouts(user_id, limit=5)

        if not workouts:
            await message.answer(
                "📜 <b>Хроники пусты</b>\n\n"
                "Твои подвиги ещё не записаны. Создай первую тренировку!",
                parse_mode=ParseMode.HTML
            )
            return

        text = f"📜 <b>Последние подвиги {message.from_user.first_name}</b>\n\n"

        for w in workouts:
            date = datetime.fromisoformat(w['date']).strftime("%d.%m.%Y %H:%M")
            text += f"🏛️ <b>{w['name']}</b> — {date}\n"
            text += f"   {len(w['exercises'])} упражнений\n"

            for i, ex in enumerate(w['exercises'][:3], 1):
                text += f"   {i}. {ex['name']} — {ex['sets']}×{ex['reps']} × {ex['weight']}кг\n"

            if len(w['exercises']) > 3:
                text += f"   ... и ещё {len(w['exercises']) - 3}\n"
            text += "\n"

        await message.answer(text, parse_mode=ParseMode.HTML)

    @dp.message(Command("myid"))
    async def cmd_myid(message: Message):
        """Показать свой Telegram ID"""
        await message.answer(f"🆔 Твой ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

    # ===========================================
    # ЗАПУСК БОТА (С ПОДДЕРЖКОЙ RENDER)
    # ===========================================

    if ON_RENDER:
        # Режим Render.com - используем вебхуки
        if not RENDER_URL:
            logger.error("❌ RENDER_EXTERNAL_URL не задан!")
            return

        logger.info(f"🌐 Запуск в режиме Render.com")
        logger.info(f"🔗 URL сервиса: {RENDER_URL}")
        logger.info(f"🔗 Вебхук путь: {WEBHOOK_PATH}")

        # Устанавливаем вебхук
        try:
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True,
                max_connections=40,
                allowed_updates=dp.resolve_used_update_types()
            )
            logger.info(f"✅ Вебхук установлен на {WEBHOOK_URL}")

            # Проверяем информацию о вебхуке
            webhook_info = await bot.get_webhook_info()
            logger.info(f"📊 Информация о вебхуке:")
            logger.info(f"   • URL: {webhook_info.url}")
            logger.info(f"   • Ожидающих обновлений: {webhook_info.pending_update_count}")
            logger.info(f"   • Макс. соединений: {webhook_info.max_connections}")

        except Exception as e:
            logger.error(f"❌ Ошибка установки вебхука: {e}")
            return

        # Запускаем aiohttp сервер для приёма вебхуков
        try:
            from aiohttp import web

            app = web.Application()

            @app.post(WEBHOOK_PATH)
            async def handle_webhook(request):
                """Обработчик вебхуков от Telegram"""
                try:
                    update_data = await request.json()
                    update = Update(**update_data)
                    await dp.feed_webhook_update(bot, update)
                    return web.Response(text="OK")
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки вебхука: {e}")
                    return web.Response(text="ERROR", status=500)

            @app.get("/")
            async def health_check(request):
                """Проверка работоспособности"""
                return web.Response(text="🏛 Чертог тренировок работает!")

            @app.get("/health")
            async def health_check_detailed(request):
                """Детальная проверка здоровья"""
                return web.json_response({
                    "status": "ok",
                    "bot": "running",
                    "webhook": WEBHOOK_URL,
                    "timestamp": datetime.now().isoformat()
                })

            port = int(os.environ.get('PORT', 8000))
            logger.info(f"🚀 Запуск веб-сервера на порту {port}")

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()

            logger.info(f"✅ Веб-сервер запущен на 0.0.0.0:{port}")

            # Держим сервер запущенным
            await asyncio.Event().wait()

        except Exception as e:
            logger.error(f"❌ Ошибка запуска веб-сервера: {e}")
            raise
    else:
        # Локальный режим - используем polling
        logger.info("💻 Запуск в локальном режиме (polling)")

        # Удаляем вебхук если был
        await bot.delete_webhook(drop_pending_updates=True)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"⚔️ Бот готов к подвигам! (запуск за {elapsed:.2f} сек)")

        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=30
            )
        finally:
            await bot.session.close()
            logger.info("🏛 Чертог закрывается...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)