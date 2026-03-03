"""
handlers/chronicles.py - Отображение хроник в боте
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
import logging
from datetime import datetime

from database import Database

router = Router()
logger = logging.getLogger(__name__)
db = Database()


@router.message(F.text == "📜 ХРОНИКИ")
async def show_chronicles(message: Message):
    """Показать историю тренировок"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    workouts = db.get_user_workouts(user_id, limit=10)
    stats = db.get_workout_stats(user_id)

    if not workouts:
        await message.answer(
            "📜 <b>ХРОНИКИ ПУСТЫ</b>\n\n"
            "Твои подвиги ещё не записаны в свитки...\n"
            "Создай первую тренировку в Mini App!",
            parse_mode=ParseMode.HTML
        )
        return

    text = f"📜 <b>ХРОНИКИ ГЕРОЯ {user_name.upper()}</b>\n\n"
    text += f"• Всего подвигов: {stats['total_workouts']}\n"
    text += f"• Упражнений выполнено: {stats['total_exercises']}\n"
    text += f"• Общий поднятый вес: {stats['total_weight']:.0f} кг\n\n"
    text += "<b>Последние записи:</b>\n\n"

    for workout in workouts[:5]:
        date = datetime.fromisoformat(workout['date']).strftime("%d.%m.%Y %H:%M")
        text += f"• <b>{date}</b> — {len(workout['exercises'])} упражнений\n"

        for i, ex in enumerate(workout['exercises'][:3], 1):
            text += f"  {i}. {ex['name']} — {ex['sets']}×{ex['reps']} × {ex['weight']}кг\n"

        if len(workout['exercises']) > 3:
            text += f"  ... и ещё {len(workout['exercises']) - 3}\n"
        text += "\n"

    text += "> Продолжай в том же духе, герой!"

    await message.answer(text, parse_mode=ParseMode.HTML)
