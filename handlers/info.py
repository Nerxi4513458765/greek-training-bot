from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import logging
from datetime import datetime

from keyboards.reply import get_back_keyboard
from database import Database

router = Router()
logger = logging.getLogger(__name__)
db = Database()


@router.message(F.text == "⚡ ПОДВИГ ДНЯ")
async def daily_trial(message: Message):
    """Подвиг дня с персональной статистикой"""
    user_id = message.from_user.id
    stats = db.get_workout_stats(user_id)

    # Определяем подвиг дня на основе статистики
    if stats['total_workouts'] == 0:
        trial = "🔰 Начать первую тренировку"
        description = "Сделай первый шаг к бессмертию!"
    elif stats['total_workouts'] < 5:
        trial = "🛡️ 3 тренировки за неделю"
        description = "Герой не отдыхает!"
    else:
        trial = "🏆 Побить личный рекорд"
        description = "Добавь вес или повторения"

    trials_text = (
        f"⚡ <b>ПОДВИГ ДНЯ</b>\n\n"
        f"<b>{trial}</b>\n"
        f"{description}\n\n"
        f"📊 <b>Твоя статистика:</b>\n"
        f"• Тренировок: {stats['total_workouts']}\n"
        f"• Упражнений: {stats['total_exercises']}\n"
        f"• Поднято: {stats['total_weight']:.0f} кг\n"
    )

    if stats['last_workout']:
        last_date = datetime.fromisoformat(stats['last_workout']).strftime("%d.%m.%Y")
        trials_text += f"• Последний подвиг: {last_date}\n"

    await message.answer(
        trials_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )