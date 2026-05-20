"""
Точка входа — запуск бота
"""
import asyncio
import logging
import sys
from aiohttp import web

from aiogram import Bot, Dispatcher
 
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import config
from database.db import init_db
from handlers import user, admin
from handlers.webhook import create_webhook_app

# ── Настройка логирования ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        
    ],
)
logger = logging.getLogger(__name__)


# ── Запуск бота ────────────────────────────────────────────────────────────

async def main() -> None:
    import os
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    await init_db(config.db_path)
    logger.info("База данных готова")

    # Создаём бота и диспетчер


    bot = Bot(
        token=config.bot_token,
    
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(user.router)
    dp.include_router(admin.router)

    # Уведомление админу о старте
    try:
        await bot.send_message(
            config.admin_id,
            "🚀 <b>Бот запущен!</b>\n\n"
            f"🔑 Свободных ключей: <b>—</b>\n"
            f"Используй /admin для управления.",
        )
    except Exception as e:
        logger.warning("Не удалось отправить уведомление админу: %s", e)

    # Запускаем webhook-сервер для ЮMoney в фоне (порт 8080)
    webhook_app = create_webhook_app(bot)
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()
    logger.info("Webhook-сервер запущен на порту 8080")

    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
