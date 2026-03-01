from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard(web_app_url: str) -> ReplyKeyboardMarkup:
    """
    Главная клавиатура с античным стилем
    """
    builder = ReplyKeyboardBuilder()

    # Самая главная кнопка — открыть Mini App
    builder.add(KeyboardButton(
        text="⚔️ ВОЙТИ В ЧЕРТОГ ТРЕНИРОВОК",
        web_app=WebAppInfo(url=web_app_url)
    ))

    # Кнопки для навигации
    builder.add(KeyboardButton(text="🏺 ОРАКУЛ"))
    builder.add(KeyboardButton(text="📜 ХРОНИКИ"))
    builder.add(KeyboardButton(text="🔥 ИСПЫТАНИЯ"))
    builder.add(KeyboardButton(text="🏛 О ЧЕРТОГЕ"))
    builder.add(KeyboardButton(text="⚡ ПОДВИГ ДНЯ"))

    # Располагаем: первая кнопка во всю ширину, остальные по 2 в ряд
    builder.adjust(1, 2, 2, 1)

    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопкой возврата
    """
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 ВЕРНУТЬСЯ В ЧЕРТОГ"))
    return builder.as_markup(resize_keyboard=True)