from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import logging

from keyboards.reply import get_back_keyboard
from utils.texts import SECTION_DESCRIPTIONS

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "🔥 ИСПЫТАНИЯ")
async def trials(message: Message):
    """Показывает готовую программу тренировок"""
    logger.info(f"{message.from_user.first_name} смотрит испытания")

    try:
        photo = FSInputFile("media/spartan.jpg")
        await message.answer_photo(
            photo=photo,
            caption=SECTION_DESCRIPTIONS["trials"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
    except FileNotFoundError:
        await message.answer(
            SECTION_DESCRIPTIONS["trials"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )