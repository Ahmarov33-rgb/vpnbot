"""
Конфигурация бота — загрузка переменных из .env
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram
    bot_token: str
    admin_id: int

    # ЮMoney
    yoomoney_wallet: str
    yoomoney_secret: str
    yoomoney_token: str

    # Магазин
    vpn_price: int
    vpn_plan_name: str
    vpn_instructions_url: str

    # Уведомления
    low_keys_threshold: int

    # База данных
    db_path: str


def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env файле!")

    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        raise ValueError("ADMIN_ID не задан в .env файле!")

    return Config(
        bot_token=bot_token,
        admin_id=int(admin_id),
        yoomoney_wallet=os.getenv("YOOMONEY_WALLET", ""),
        yoomoney_secret=os.getenv("YOOMONEY_SECRET", ""),
        yoomoney_token=os.getenv("YOOMONEY_TOKEN", ""),
        vpn_price=int(os.getenv("VPN_PRICE", "199")),
        vpn_plan_name=os.getenv("VPN_PLAN_NAME", "VPN Premium — 30 дней"),
        vpn_instructions_url=os.getenv("VPN_INSTRUCTIONS_URL", ""),
        low_keys_threshold=int(os.getenv("LOW_KEYS_THRESHOLD", "3")),
        db_path=os.getenv("DB_PATH", "data/vpn_bot.db"),
    )


config = load_config()
