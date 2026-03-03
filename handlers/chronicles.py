"""
handlers/chronicles.py - Отображение хроник в боте с фото
"""

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import logging
from datetime import datetime
from pathlib import Path

from database import Database

router = Router()
logger = logging.getLogger(__name__)
db = Database()

# Определяем путь к папке с медиафайлами
BASE_DIR = Path(__file__).parent.parent
MEDIA_DIR = BASE_DIR / "media"


@router.message(F.text == "📜 ХРОНИКИ")
async def show_chronicles(message: Message):
    """Показать историю тренировок с фото свитка"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    workouts = db.get_user_workouts(user_id, limit=10)
    stats = db.get_workout_stats(user_id)

    # Формируем текст
    if not workouts:
        text = (
            "📜 <b>ХРОНИКИ ПУСТЫ</b>\n\n"
            "Твои подвиги ещё не записаны в свитки...\n"
            "Создай первую тренировку в Mini App!"
        )
    else:
        text = f"📜 <b>ХРОНИКИ ГЕРОЯ {user_name.upper()}</b>\n\n"
        text += f"• Всего подвигов: {stats['total_workouts']}\n"
        text += f"• Упражнений выполнено: {stats['total_exercises']}\n"
        text += f"• Общий поднятый вес: {stats['total_weight']:.0f} кг\n\n"
        text += "<b>Последние записи:</b>\n\n"

        for workout in workouts[:5]:
            try:
                date = datetime.fromisoformat(workout['date']).strftime("%d.%m.%Y %H:%M")
            except:
                date = workout['date']

            text += f"• <b>{date}</b> — {len(workout['exercises'])} упражнений\n"

            for i, ex in enumerate(workout['exercises'][:3], 1):
                text += f"  {i}. {ex['name']} — {ex['sets']}×{ex['reps']} × {ex['weight']}кг\n"

            if len(workout['exercises']) > 3:
                text += f"  ... и ещё {len(workout['exercises']) - 3}\n"
            text += "\n"

        text += "> Продолжай в том же духе, герой!"

    # Пытаемся отправить с фото
    try:
        photo_path = MEDIA_DIR / "scroll.jpg"
        if photo_path.exists():
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Фото отправлено для {user_name}")
        else:
            # Если фото нет - просто текст
            logger.warning(f"⚠️ Файл scroll.jpg не найден в {MEDIA_DIR}")
            await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фото: {e}")
        # Отправляем без фото
        await message.answer(text, parse_mode=ParseMode.HTML)