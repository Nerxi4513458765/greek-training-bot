"""
handlers/trainer.py - Обработчик для раздела Тренер
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "🏋️ ТРЕНЕР")
async def cmd_trainer(message: Message):
    """Информация о тренере и планах"""
    user_name = message.from_user.first_name

    text = (
        f"🏋️ <b>Персональный тренер</b>\n\n"
        f"Привет, {user_name}! В разделе «Тренер» в Mini App ты можешь:\n\n"
        f"• Выбрать фокус на неделю (грудь, спина, ноги и т.д.)\n"
        f"• Получить готовый план тренировок\n"
        f"• Редактировать упражнения под себя\n"
        f"• Использовать план для своих тренировок\n\n"
        f"Открой Mini App и нажми «Тренер» в меню!"
    )

    await message.answer(text, parse_mode=ParseMode.HTML)