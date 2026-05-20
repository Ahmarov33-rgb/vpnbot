"""
Тексты сообщений бота — всё в одном месте для удобного редактирования
"""
from config import config


def welcome_text(full_name: str) -> str:
    return (
        f"👋 Привет, <b>{full_name}</b>!\n\n"
        f"Добро пожаловать в <b>VPN Bot</b> — быстрый и надёжный VPN.\n\n"
        f"🔒 Анонимность и безопасность в интернете\n"
        f"⚡️ Высокая скорость соединения\n"
        f"🌍 Серверы по всему миру\n\n"
        f"Выбери нужный раздел в меню ниже 👇"
    )


def buy_info_text() -> str:
    return (
        f"🛒 <b>Покупка VPN</b>\n\n"
        f"📦 Тариф: <b>{config.vpn_plan_name}</b>\n"
        f"💰 Цена: <b>{config.vpn_price} ₽</b>\n\n"
        f"После оплаты вы получите ключ для подключения.\n"
        f"⚡️ Выдача ключа — автоматически!\n\n"
        f"Нажми кнопку ниже для оплаты 👇"
    )


def payment_created_text(payment_id: str) -> str:
    return (
        f"💳 <b>Счёт создан</b>\n\n"
        f"Сумма к оплате: <b>{config.vpn_price} ₽</b>\n"
        f"ID платежа: <code>{payment_id}</code>\n\n"
        f"1️⃣ Нажми «Оплатить через ЮMoney»\n"
        f"2️⃣ Оплати на открывшейся странице\n"
        f"3️⃣ Вернись и нажми «Я оплатил — проверить»\n\n"
        f"⏳ Ссылка действительна 30 минут"
    )


def payment_pending_text() -> str:
    return (
        f"⏳ <b>Оплата не найдена</b>\n\n"
        f"Платёж ещё не поступил. Это может занять до 2 минут.\n\n"
        f"Если вы уже оплатили — подождите немного и нажмите "
        f"«Я оплатил — проверить» снова."
    )


def key_issued_text(key: str) -> str:
    return (
        f"🎉 <b>Оплата подтверждена!</b>\n\n"
        f"Ваш VPN ключ:\n"
        f"<code>{key}</code>\n\n"
        f"📋 Скопируйте ключ и следуйте инструкции по подключению.\n\n"
        f"✅ Тариф: <b>{config.vpn_plan_name}</b>\n"
        f"🔒 Приятного использования!"
    )


def no_keys_text() -> str:
    return (
        f"😔 <b>Ключи временно закончились</b>\n\n"
        f"Приносим извинения! Администратор уже уведомлён.\n"
        f"Ключи будут добавлены в ближайшее время.\n\n"
        f"Ваш платёж был зачислен — обратитесь в поддержку "
        f"для получения ключа вручную."
    )


def profile_text(full_name: str, user_id: int, purchases: int, spent: int) -> str:
    return (
        f"👤 <b>Мой профиль</b>\n\n"
        f"Имя: <b>{full_name}</b>\n"
        f"ID: <code>{user_id}</code>\n\n"
        f"📦 Покупок: <b>{purchases}</b>\n"
        f"💰 Потрачено: <b>{spent} ₽</b>"
    )


def purchases_text(rows: list) -> str:
    if not rows:
        return "📋 У вас ещё нет покупок.\n\nНажмите 🛒 Купить VPN чтобы начать!"

    lines = ["📋 <b>История покупок:</b>\n"]
    for i, row in enumerate(rows, 1):
        date = row["issued_at"][:10]
        lines.append(
            f"{i}. <code>{row['key_value'][:20]}...</code>\n"
            f"   💰 {row['amount']} ₽  |  📅 {date}"
        )
    return "\n".join(lines)


def help_text() -> str:
    return (
        f"❓ <b>Помощь</b>\n\n"
        f"<b>Как купить VPN:</b>\n"
        f"1. Нажмите 🛒 Купить VPN\n"
        f"2. Нажмите «Оплатить через ЮMoney»\n"
        f"3. Оплатите удобным способом\n"
        f"4. Вернитесь в бот и нажмите «Я оплатил»\n"
        f"5. Получите ключ автоматически!\n\n"
        f"<b>Поддержка:</b>\n"
        f"Если возникли проблемы — напишите @your_support\n\n"
        f"<b>Возврат средств:</b>\n"
        f"Возможен в течение 24 часов после покупки"
    )


def admin_stats_text(stats: dict) -> str:
    top = "\n".join(
        f"  {i+1}. {u['full_name'] or 'Аноним'} — {u['purchases']} покупок"
        for i, u in enumerate(stats["top_users"])
    ) or "  Нет данных"

    return (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{stats['users_total']}</b>\n"
        f"🛒 Продаж всего: <b>{stats['sales_total']}</b>\n"
        f"📅 Продаж сегодня: <b>{stats['sales_today']}</b>\n"
        f"💰 Выручка: <b>{stats['revenue_total']} ₽</b>\n"
        f"🔑 Свободных ключей: <b>{stats['free_keys']}</b>\n\n"
        f"🏆 <b>Топ покупателей:</b>\n{top}"
    )


def low_keys_alert(count: int) -> str:
    return (
        f"⚠️ <b>Внимание! Заканчиваются ключи</b>\n\n"
        f"Осталось всего <b>{count}</b> свободных ключей.\n"
        f"Пожалуйста, добавьте новые ключи через /admin → «Добавить ключи»"
    )
