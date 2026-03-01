from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from datetime import datetime
import logging

from keyboards.reply import get_back_keyboard
from database import Database

router = Router()
logger = logging.getLogger(__name__)

# Создаём объект базы данных
db = Database()


@router.message(F.text == "📜 ХРОНИКИ")
async def chronicles(message: Message):
    """Показывает реальную историю тренировок из базы данных"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    logger.info(f"{user_name} (id: {user_id}) смотрит хроники")

    try:
        # Получаем тренировки из базы
        workouts = db.get_user_workouts(user_id, limit=5)
        stats = db.get_workout_stats(user_id)

        if not workouts:
            text = (
                "📜 <b>ХРОНИКИ ПУСТЫ</b>\n\n"
                "Твои подвиги ещё не записаны в свитки...\n\n"
                "🏛️ Открой <b>«Чертог тренировок»</b> и создай свой первый подвиг!"
            )
        else:
            # Формируем текст с историей
            text = f"📜 <b>ХРОНИКИ ГЕРОЯ {user_name.upper()}</b>\n\n"
            text += f"🏛 <b>Всего подвигов:</b> {stats['total_workouts']}\n"
            text += f"💪 <b>Упражнений выполнено:</b> {stats['total_exercises']}\n"
            text += f"🏋️ <b>Общий поднятый вес:</b> {stats['total_weight']:.0f} кг\n\n"
            text += "📋 <b>Последние записи:</b>\n\n"

            for workout in workouts:
                # Преобразуем дату из ISO формата
                try:
                    workout_date = datetime.fromisoformat(workout['date'].replace('Z', '+00:00'))
                    date_str = workout_date.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str = workout['date']

                exercises_count = len(workout['exercises'])
                text += f"• <b>{date_str}</b> — {exercises_count} упражнений\n"

                # Показываем первые 3 упражнения
                for i, ex in enumerate(workout['exercises'][:3], 1):
                    text += f"  {i}. {ex.get('name', 'Без названия')} — {ex.get('sets', 0)}×{ex.get('reps', 0)} × {ex.get('weight', 0)}кг\n"

                if len(workout['exercises']) > 3:
                    text += f"  ... и ещё {len(workout['exercises']) - 3}\n"
                text += "\n"

            text += "⚡ <i>Продолжай в том же духе, герой!</i>"

        # Пробуем отправить с картинкой свитка
        try:
            photo = FSInputFile("media/scroll.jpg")
            await message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        except FileNotFoundError:
            # Если нет картинки - просто текст
            await message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )

    except Exception as e:
        # Обрабатываем ошибки базы данных
        logger.error(f"Ошибка при получении хроник для пользователя {user_id}: {e}")
        await message.answer(
            "❌ <b>Ошибка чтения хроник</b>\n\n"
            "Свитки повреждены или ещё не созданы. Попробуй позже.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )