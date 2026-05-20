"""
Клавиатуры и кнопки бота
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ── Главное меню (обычные кнопки) ──────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(
        KeyboardButton(text="🛒 Купить VPN"),
        KeyboardButton(text="👤 Мой профиль"),
    )
    kb.row(
        KeyboardButton(text="📋 Мои покупки"),
        KeyboardButton(text="❓ Помощь"),
    )
    return kb.as_markup(resize_keyboard=True)


# ── Покупка ────────────────────────────────────────────────────────────────

def buy_keyboard(payment_url: str, payment_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="💳 Оплатить через ЮMoney",
        url=payment_url
    ))
    kb.row(InlineKeyboardButton(
        text="✅ Я оплатил — проверить",
        callback_data=f"check_payment:{payment_id}"
    ))
    kb.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel_payment"
    ))
    return kb.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment"))
    return kb.as_markup()


# ── Профиль ────────────────────────────────────────────────────────────────

def profile_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="📋 История покупок",
        callback_data="my_purchases"
    ))
    kb.row(InlineKeyboardButton(
        text="🛒 Купить ещё",
        callback_data="go_buy"
    ))
    return kb.as_markup()


# ── Инструкция после выдачи ключа ─────────────────────────────────────────

def key_issued_keyboard(instructions_url: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if instructions_url:
        kb.row(InlineKeyboardButton(
            text="📖 Инструкция по подключению",
            url=instructions_url
        ))
    kb.row(InlineKeyboardButton(
        text="💬 Поддержка",
        callback_data="support"
    ))
    return kb.as_markup()


# ── Админ-панель ───────────────────────────────────────────────────────────

def admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔑 Добавить ключи", callback_data="admin_add_keys"),
        InlineKeyboardButton(text="📊 Статистика",      callback_data="admin_stats"),
    )
    kb.row(
        InlineKeyboardButton(text="🗝 Кол-во ключей",  callback_data="admin_keys_count"),
        InlineKeyboardButton(text="📤 Загрузить .txt", callback_data="admin_upload_txt"),
    )
    kb.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close"))
    return kb.as_markup()


def admin_back_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back"))
    return kb.as_markup()


def admin_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm:{action}"),
        InlineKeyboardButton(text="❌ Отмена",      callback_data="admin_back"),
    )
    return kb.as_markup()
