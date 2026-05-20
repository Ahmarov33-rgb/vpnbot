"""
Хендлеры администратора — управление ключами, статистика
"""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, Document

from config import config
from database import db
from utils import keyboards, texts

logger = logging.getLogger(__name__)
router = Router()


# ── FSM состояния ──────────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    waiting_keys_text = State()   # ожидание текста с ключами
    waiting_keys_file = State()   # ожидание .txt файла с ключами


# ── Фильтр: только для администратора ─────────────────────────────────────

def is_admin(message_or_callback) -> bool:
    uid = (
        message_or_callback.from_user.id
        if hasattr(message_or_callback, "from_user")
        else None
    )
    return uid == config.admin_id


# ── /admin — главная панель ───────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message):
        await message.answer("❌ Нет доступа.")
        return

    keys_count = await db.get_free_keys_count(config.db_path)
    await message.answer(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"🔑 Свободных ключей: <b>{keys_count}</b>\n\n"
        f"Выбери действие:",
        reply_markup=keyboards.admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return
    await callback.message.delete()
    await callback.answer("Панель закрыта")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return
    await state.clear()
    keys_count = await db.get_free_keys_count(config.db_path)
    await callback.message.edit_text(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"🔑 Свободных ключей: <b>{keys_count}</b>\n\n"
        f"Выбери действие:",
        reply_markup=keyboards.admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Статистика ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    stats = await db.get_stats(config.db_path)
    await callback.message.edit_text(
        texts.admin_stats_text(stats),
        reply_markup=keyboards.admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Количество ключей ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_keys_count")
async def admin_keys_count(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    count = await db.get_free_keys_count(config.db_path)
    status = "✅ Достаточно" if count > config.low_keys_threshold else "⚠️ Мало!"

    await callback.message.edit_text(
        f"🔑 <b>Свободные ключи</b>\n\n"
        f"Количество: <b>{count}</b>\n"
        f"Статус: {status}\n\n"
        f"Порог предупреждения: <b>{config.low_keys_threshold}</b>",
        reply_markup=keyboards.admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Добавить ключи текстом ─────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_keys")
async def admin_add_keys_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_keys_text)
    await callback.message.edit_text(
        "📝 <b>Добавление ключей</b>\n\n"
        "Отправь ключи сообщением — <b>каждый с новой строки</b>:\n\n"
        "<code>ключ1\nключ2\nключ3</code>\n\n"
        "Или загрузи .txt файл через «Загрузить .txt»",
        reply_markup=keyboards.admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_keys_text)
async def admin_receive_keys_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    raw_keys = message.text.strip().splitlines()
    keys = [k.strip() for k in raw_keys if k.strip()]

    if not keys:
        await message.answer("❌ Не нашёл ключей. Убедись что каждый ключ на отдельной строке.")
        return

    added, skipped = await db.add_keys(config.db_path, keys)
    total = await db.get_free_keys_count(config.db_path)
    await state.clear()

    await message.answer(
        f"✅ <b>Ключи добавлены!</b>\n\n"
        f"➕ Добавлено: <b>{added}</b>\n"
        f"⏭ Пропущено (дубли): <b>{skipped}</b>\n"
        f"🔑 Всего свободных: <b>{total}</b>",
        parse_mode="HTML",
    )
    logger.info("Админ добавил %d ключей, пропущено %d дублей", added, skipped)


# ── Добавить ключи .txt файлом ─────────────────────────────────────────────

@router.callback_query(F.data == "admin_upload_txt")
async def admin_upload_txt_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_keys_file)
    await callback.message.edit_text(
        "📤 <b>Загрузка ключей из файла</b>\n\n"
        "Отправь <b>.txt файл</b>, где каждый ключ на отдельной строке.\n\n"
        "Пример содержимого файла:\n"
        "<code>vless://key1...\nvless://key2...\nvless://key3...</code>",
        reply_markup=keyboards.admin_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_keys_file, F.document)
async def admin_receive_keys_file(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    doc: Document = message.document

    # Проверяем расширение файла
    if not doc.file_name.endswith(".txt"):
        await message.answer("❌ Нужен файл с расширением .txt")
        return

    # Скачиваем файл
    try:
        file = await message.bot.get_file(doc.file_id)
        downloaded = await message.bot.download_file(file.file_path)
        content = downloaded.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("Ошибка скачивания файла: %s", e)
        await message.answer("❌ Не удалось скачать файл. Попробуй снова.")
        return

    raw_keys = content.strip().splitlines()
    keys = [k.strip() for k in raw_keys if k.strip()]

    if not keys:
        await message.answer("❌ Файл пустой или нет ключей.")
        return

    added, skipped = await db.add_keys(config.db_path, keys)
    total = await db.get_free_keys_count(config.db_path)
    await state.clear()

    await message.answer(
        f"✅ <b>Файл обработан!</b>\n\n"
        f"📄 Строк в файле: <b>{len(raw_keys)}</b>\n"
        f"➕ Добавлено: <b>{added}</b>\n"
        f"⏭ Пропущено (дубли): <b>{skipped}</b>\n"
        f"🔑 Всего свободных: <b>{total}</b>",
        parse_mode="HTML",
    )
    logger.info("Файл: добавлено %d ключей, %d дублей", added, skipped)


@router.message(AdminStates.waiting_keys_file)
async def admin_file_wrong_type(message: Message) -> None:
    """Пользователь отправил не файл."""
    if not is_admin(message):
        return
    await message.answer("❌ Ожидаю .txt файл. Отправь файл или нажми «Назад».")


# ── /broadcast — рассылка (бонусная функция) ──────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    """Рассылка сообщения всем пользователям."""
    if not is_admin(message):
        await message.answer("❌ Нет доступа.")
        return

    # Текст после /broadcast
    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer(
            "Использование: /broadcast <текст сообщения>\n\n"
            "Пример: /broadcast Добавили новые ключи! Покупайте VPN 🔥"
        )
        return

    # Получаем всех пользователей
    import aiosqlite
    sent = 0
    failed = 0
    async with aiosqlite.connect(config.db_path) as db_conn:
        async with db_conn.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()

    for (user_id,) in users:
        try:
            await message.bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📨 <b>Рассылка завершена</b>\n\n"
        f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        parse_mode="HTML",
    )
    logger.info("Рассылка: отправлено %d, ошибок %d", sent, failed)
