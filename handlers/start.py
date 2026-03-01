from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
import logging

from database import Database
from keyboards.reply import get_main_keyboard, get_back_keyboard
from config import WEB_APP_URL
from utils.texts import WELCOME_TEXTS, SECTION_DESCRIPTIONS

# Создаём глобальный объект базы данных
db = Database()

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Первое вхождение в чертог"""
    user = message.from_user
    user_name = user.first_name

    # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ В БАЗУ ДАННЫХ (ШАГ 2)
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    logger.info(f"Герой {user_name} (id: {user.id}) вошёл в чертог")

    # Пробуем отправить картинку со статуей
    try:
        photo = FSInputFile("media/statue.jpg")
        await message.answer_photo(
            photo=photo,
            caption=WELCOME_TEXTS["main"](user_name),
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard(WEB_APP_URL)
        )
    except FileNotFoundError:
        # Если нет картинки - просто текст
        await message.answer(
            WELCOME_TEXTS["main"](user_name),
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard(WEB_APP_URL)
        )


@router.message(F.text == "🔙 ВЕРНУТЬСЯ В ЧЕРТОГ")
async def back_to_main(message: Message):
    """Возврат в главное меню"""
    await message.answer(
        WELCOME_TEXTS["return"],
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard(WEB_APP_URL)
    )


@router.message(F.text == "⚔️ ВОЙТИ В ЧЕРТОГ ТРЕНИРОВОК")
async def open_training_hall(message: Message):
    """Кнопка открытия Mini App"""
    await message.answer(
        "🏛 <b>Врата открываются...</b>\n\n"
        "Ты переносишься в чертог тренировок. Да прибудет с тобой сила!",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard(WEB_APP_URL)
    )