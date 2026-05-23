"""
Хендлеры для пользователей — главное меню, покупка, профиль
"""
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from config import config
from database import db
from utils import keyboards, texts, payment

logger = logging.getLogger(__name__)
router = Router()


# ── /start ────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие при первом запуске."""
    await db.get_or_create_user(
        config.db_path,
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
    )
    await message.answer(
        texts.welcome_text(message.from_user.full_name),
        reply_markup=keyboards.main_menu(),
        parse_mode="HTML",
    )


# ── Купить VPN ────────────────────────────────────────────────────────────

@router.message(F.text == "🛒 Купить VPN")
async def cmd_buy(message: Message) -> None:
    """Показывает информацию о покупке и создаёт платёж."""
    await db.get_or_create_user(
        config.db_path,
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
    )

    # Проверяем что есть свободные ключи
    keys_count = await db.get_free_keys_count(config.db_path)
    if keys_count == 0:
        await message.answer(
            "😔 <b>Ключи временно закончились</b>\n\nПожалуйста, вернитесь позже.",
            parse_mode="HTML",
        )
        return

    # Создаём платёж
    payment_id = payment.generate_payment_id(message.from_user.id)
    pay_url = payment.build_payment_url(
        wallet=config.yoomoney_wallet,
        amount=config.vpn_price,
        payment_id=payment_id,
        label=f"user_{message.from_user.id}",
    )

    # Сохраняем ожидающий платёж
    await db.create_payment(
        config.db_path,
        payment_id=payment_id,
        user_id=message.from_user.id,
        amount=config.vpn_price,
    )

    await message.answer(
        texts.payment_created_text(payment_id),
        reply_markup=keyboards.buy_keyboard(pay_url, payment_id),
        parse_mode="HTML",
    )
    logger.info("Создан платёж %s для user %d", payment_id, message.from_user.id)


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(callback: CallbackQuery) -> None:
    """Проверяет оплату по кнопке «Я оплатил»."""
    payment_id = callback.data.split(":", 1)[1]
    await callback.answer("⏳ Проверяем оплату...", show_alert=False)

    # Защита от повторного использования
    if await db.is_payment_used(config.db_path, payment_id):
        await callback.message.edit_text(
            "✅ Этот платёж уже был использован. Ключ уже выдан.",
            parse_mode="HTML",
        )
        return

    # Получаем данные платежа из базы
    pay_record = await db.get_payment(config.db_path, payment_id)
    if not pay_record:
        await callback.answer("❌ Платёж не найден.", show_alert=True)
        return

    # Проверяем через API ЮMoney
    operation_id = await payment.check_payment_via_api(
        token=config.yoomoney_token,
        payment_id=payment_id,
        expected_amount=pay_record["amount"],
    )

    if not operation_id:
        await callback.message.answer(
        "❌ Оплата не найдена.\n\nЕсли уже оплатили — подождите минуту и нажмите кнопку снова."
    )
    return

# Оплата подтверждена — выдаём ключ
    await _issue_key(
    callback.message,
    callback.from_user.id,
    payment_id,
    pay_record["amount"]
)


async def _issue_key(message: Message, user_id: int, payment_id: str, amount: int) -> None:
    """Внутренняя функция выдачи ключа после подтверждения оплаты."""
    # Повторная проверка на дубли (race condition защита)
    if await db.is_payment_used(config.db_path, payment_id):
        return

    # Берём свободный ключ
    key = await db.pop_free_key(config.db_path)

    if not key:
        # Ключей нет — уведомляем пользователя и администратора
        await message.edit_text(texts.no_keys_text(), parse_mode="HTML")
        await message.bot.send_message(
            config.admin_id,
            f"🚨 <b>КРИТИЧНО: Нет ключей!</b>\n\n"
            f"Пользователь {user_id} оплатил, но ключей нет.\n"
            f"Payment ID: <code>{payment_id}</code>\n"
            f"Сумма: {amount} ₽\n\n"
            f"Выдайте ключ вручную!",
            parse_mode="HTML",
        )
        logger.error("Нет ключей для payment_id=%s user_id=%d", payment_id, user_id)
        return

    # Сохраняем в историю
    await db.save_issued_key(config.db_path, user_id, key, payment_id, amount)
    await db.confirm_payment(config.db_path, payment_id)

    # Отправляем ключ пользователю
    await message.edit_text(
        texts.key_issued_text(key),
        reply_markup=keyboards.key_issued_keyboard(config.vpn_instructions_url),
        parse_mode="HTML",
    )
    logger.info("Выдан ключ для user %d, payment %s", user_id, payment_id)

    # Проверяем остаток ключей и предупреждаем админа
    remaining = await db.get_free_keys_count(config.db_path)
    if remaining <= config.low_keys_threshold:
        await message.bot.send_message(
            config.admin_id,
            texts.low_keys_alert(remaining),
            parse_mode="HTML",
        )
        logger.warning("Мало ключей: %d", remaining)


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_callback(callback: CallbackQuery) -> None:
    """Отменяет создание платежа."""
    await callback.message.edit_text(
        "❌ Покупка отменена.\n\nВозвращайся когда будешь готов! 👋",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "go_buy")
async def go_buy_callback(callback: CallbackQuery) -> None:
    """Переход к покупке из профиля."""
    await callback.answer()
    await cmd_buy(callback.message)


# ── Профиль ───────────────────────────────────────────────────────────────

@router.message(F.text == "👤 Мой профиль")
async def cmd_profile(message: Message) -> None:
    """Показывает профиль пользователя."""
    await db.get_or_create_user(
        config.db_path,
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
    )

    purchases = await db.get_user_purchases(config.db_path, message.from_user.id)
    total_spent = sum(row["amount"] for row in purchases)

    await message.answer(
        texts.profile_text(
            message.from_user.full_name,
            message.from_user.id,
            len(purchases),
            total_spent,
        ),
        reply_markup=keyboards.profile_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Мои покупки")
@router.callback_query(F.data == "my_purchases")
async def cmd_purchases(event) -> None:
    """Показывает историю покупок."""
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        send = event.message.answer
        await event.answer()
    else:
        user_id = event.from_user.id
        send = event.answer

    purchases = await db.get_user_purchases(config.db_path, user_id)
    await send(texts.purchases_text(purchases), parse_mode="HTML")


# ── Помощь ────────────────────────────────────────────────────────────────

@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(texts.help_text(), parse_mode="HTML")


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "💬 <b>Поддержка</b>\n\nНапишите нам: @your_support",
        parse_mode="HTML",
    )
