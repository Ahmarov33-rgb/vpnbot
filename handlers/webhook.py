"""
Webhook-хендлер для уведомлений от ЮMoney
Запускается как отдельный aiohttp сервер рядом с ботом
"""
import logging
from aiohttp import web
from config import config
from database import db
from utils import payment, texts

logger = logging.getLogger(__name__)


async def yoomoney_webhook(request: web.Request) -> web.Response:
    """
    Принимает POST-уведомления от ЮMoney.
    Документация: https://yoomoney.ru/docs/payment-buttons/using-api/notifications
    """
    try:
        data = await request.post()

        notification_type = data.get("notification_type", "")
        operation_id      = data.get("operation_id", "")
        amount            = data.get("amount", "0")
        currency          = data.get("currency", "643")
        datetime_         = data.get("datetime", "")
        sender            = data.get("sender", "")
        codepro           = data.get("codepro", "false")
        sha1_hash         = data.get("sha1_hash", "")
        label             = data.get("label", "")   # наш payment_id

        logger.info(
            "ЮMoney webhook: op=%s amount=%s label=%s",
            operation_id, amount, label
        )

        # 1. Проверяем подпись
        if config.yoomoney_secret:
            valid = payment.verify_notification(
                notification_type=notification_type,
                operation_id=operation_id,
                amount=amount,
                currency=currency,
                datetime_=datetime_,
                sender=sender,
                codepro=codepro,
                secret=config.yoomoney_secret,
                sha1_hash=sha1_hash,
            )
            if not valid:
                logger.warning("Неверная подпись webhook от ЮMoney!")
                return web.Response(status=400, text="Invalid signature")

        # 2. Проверяем что платёж помечен как успешный
        if notification_type not in ("card-incoming", "p2p-incoming"):
            return web.Response(text="OK")

        # 3. Ищем платёж в базе по label
        if not label:
            logger.warning("Webhook без label — пропускаем")
            return web.Response(text="OK")

        pay_record = await db.get_payment(config.db_path, label)
        if not pay_record:
            logger.warning("Webhook: платёж %s не найден в базе", label)
            return web.Response(text="OK")

        # 4. Защита от дублей
        if await db.is_payment_used(config.db_path, label):
            logger.info("Webhook: платёж %s уже обработан", label)
            return web.Response(text="OK")

        # 5. Проверяем сумму
        received = int(float(amount))
        if received < pay_record["amount"]:
            logger.warning(
                "Webhook: сумма %d < ожидаемой %d для %s",
                received, pay_record["amount"], label
            )
            return web.Response(text="OK")

        # 6. Выдаём ключ пользователю
        user_id = pay_record["user_id"]
        key = await db.pop_free_key(config.db_path)

        if not key:
            # Ключей нет — уведомляем админа
            logger.error("Webhook: нет ключей для %s user %d", label, user_id)
            await request.app["bot"].send_message(
                user_id,
                texts.no_keys_text(),
                parse_mode="HTML",
            )
            await request.app["bot"].send_message(
                config.admin_id,
                f"🚨 <b>Нет ключей (webhook)!</b>\n\n"
                f"User: {user_id}\nPayment: <code>{label}</code>\n"
                f"Сумма: {amount} ₽",
                parse_mode="HTML",
            )
            return web.Response(text="OK")

        # Сохраняем и отправляем ключ
        await db.save_issued_key(config.db_path, user_id, key, label, received)
        await db.confirm_payment(config.db_path, label)

        await request.app["bot"].send_message(
            user_id,
            texts.key_issued_text(key),
            parse_mode="HTML",
        )
        logger.info("Webhook: выдан ключ для user %d, payment %s", user_id, label)

        # Предупреждение о малом количестве ключей
        remaining = await db.get_free_keys_count(config.db_path)
        if remaining <= config.low_keys_threshold:
            await request.app["bot"].send_message(
                config.admin_id,
                texts.low_keys_alert(remaining),
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error("Ошибка в webhook: %s", e, exc_info=True)

    return web.Response(text="OK")


def create_webhook_app(bot) -> web.Application:
    """Создаёт aiohttp приложение с webhook роутом."""
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/yoomoney/webhook", yoomoney_webhook)
    return app
