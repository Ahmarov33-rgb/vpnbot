"""
Работа с API ЮMoney — создание платежей и проверка оплаты
"""
import hashlib
import logging
import uuid
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


def generate_payment_id(user_id: int) -> str:
    """Генерирует уникальный ID платежа на основе user_id + UUID."""
    return f"vpn_{user_id}_{uuid.uuid4().hex[:8]}"


def build_payment_url(wallet: str, amount: int, payment_id: str, label: str) -> str:
    """
    Строит ссылку на оплату через ЮMoney (Quickpay).
    Документация: https://yoomoney.ru/docs/payment-buttons/using-api/forms
    """
    base = "https://yoomoney.ru/quickpay/confirm.xml"
    params = (
        f"receiver=4100119537329697"
        f"&quickpay-form=button"
        f"&targets=VPN+{label}"
        f"&paymentType=AC"          # AC = банковская карта, PC = кошелёк ЮMoney
        f"&sum={amount}"
        f"&label={payment_id}"      # label = наш payment_id для идентификации
        f"&successURL=https://t.me/your_bot"  # куда вернуть после оплаты
    )
    return f"{base}?{params}"


def verify_notification(
    notification_type: str,
    operation_id: str,
    amount: str,
    currency: str,
    datetime_: str,
    sender: str,
    codepro: str,
    secret: str,
    sha1_hash: str,
) -> bool:
    """
    Проверяет подпись уведомления от ЮMoney.
    Документация: https://yoomoney.ru/docs/payment-buttons/using-api/notifications
    """
    check_str = "&".join([
        notification_type,
        operation_id,
        amount,
        currency,
        datetime_,
        sender,
        codepro,
        secret,
        sha1_hash,
    ])
    # ЮMoney использует SHA-1
    computed = hashlib.sha1(check_str.encode("utf-8")).hexdigest()
    return computed == sha1_hash


async def check_payment_via_api(
    token: str, payment_id: str, expected_amount: int
) -> Optional[str]:
    """
    Проверяет, прошёл ли платёж через API ЮMoney.
    Возвращает operation_id если оплата найдена, иначе None.

    Используется как резервная проверка (на случай если webhook не пришёл).
    """
    url = "https://yoomoney.ru/api/operation-history"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "label": payment_id,
        "type": "deposition",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("ЮMoney API ответил %d", resp.status)
                    return None

                data = await resp.json()
                operations = data.get("operations", [])

                for op in operations:
                    # Проверяем: статус, сумма и label совпадают
                    if (
                        op.get("status") == "success"
                        and op.get("label") == payment_id
                        and int(float(op.get("amount", 0))) >= expected_amount
                    ):
                        return op.get("operation_id")

    except aiohttp.ClientError as e:
        logger.error("Ошибка запроса к ЮMoney: %s", e)
    except Exception as e:
        logger.error("Неожиданная ошибка при проверке платежа: %s", e)

    return None
