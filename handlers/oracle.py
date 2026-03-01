from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import random
import logging

from keyboards.reply import get_back_keyboard
from utils.texts import ORACLE_QUOTES, SECTION_DESCRIPTIONS

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "🏺 ОРАКУЛ")
async def oracle(message: Message):
    """Оракул даёт мудрость"""
    logger.info(f"{message.from_user.first_name} вопрошает оракула")

    # Выбираем случайную цитату
    quote = random.choice(ORACLE_QUOTES)

    # Формируем сообщение
    oracle_message = (
        f"{SECTION_DESCRIPTIONS['oracle']}\n\n"
        f"🔮 <b>Пророчество гласит:</b>\n"
        f"<i>«{quote}»</i>\n\n"
        f"🌙 <i>Так молвила Пифия...</i>"
    )

    # Пробуем отправить с картинкой
    try:
        photo = FSInputFile("media/oracle.jpg")
        await message.answer_photo(
            photo=photo,
            caption=oracle_message,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
    except FileNotFoundError:
        await message.answer(
            oracle_message,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )