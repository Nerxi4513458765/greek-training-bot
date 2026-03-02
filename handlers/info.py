"""
handlers/info.py - Обработчик раздела "О чертоге"
"""

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import logging
from pathlib import Path

from keyboards.reply import get_back_keyboard
from utils.texts import SECTION_DESCRIPTIONS

router = Router()
logger = logging.getLogger(__name__)

# Определяем путь к папке с медиафайлами
BASE_DIR = Path(__file__).parent.parent
MEDIA_DIR = BASE_DIR / "media"


@router.message(F.text == "🏛 О ЧЕРТОГЕ")
async def about(message: Message):
    """Информация о проекте"""
    user_name = message.from_user.first_name
    logger.info(f"🏛 {user_name} спрашивает о чертоге")

    # Текст о чертоге (можно вынести в texts.py, но для надёжности продублируем)
    about_text = (
        "🏛 <b>О ЧЕРТОГЕ ТРЕНИРОВОК</b>\n\n"
        "Этот храм силы создан для тех, кто чтит заветы древних. "
        "Вдохновлённый мифами Эллады и мрачным величием Аида, "
        "он помогает смертным становиться полубогами.\n\n"
        "<b>Что тебя ждёт:</b>\n"
        "• Создание собственных программ тренировок\n"
        "• Отслеживание прогресса в стиле древних свитков\n"
        "• Пророчества оракула перед каждой тренировкой\n"
        "• Статистика подвигов в хрониках\n\n"
        "<i>«Σῶμα καὶ πνεῦμα» — тело и дух.</i>"
    )

    # Пробуем отправить с картинкой, если есть
    try:
        photo_path = MEDIA_DIR / "about.jpg"
        if photo_path.exists():
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=about_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        else:
            # Если картинки нет - просто текст
            await message.answer(
                about_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото о чертоге: {e}")
        await message.answer(
            about_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )


@router.message(F.text == "🔙 ВЕРНУТЬСЯ В ЧЕРТОГ")
async def back_to_main(message: Message):
    """Возврат в главное меню (дублёр на всякий случай)"""
    from handlers.start import back_to_main as start_back
    await start_back(message)