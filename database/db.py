"""
База данных SQLite — все операции с данными
"""
import aiosqlite
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def init_db(db_path: str) -> None:
    """Создаёт таблицы если их нет."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.executescript("""
            -- Пользователи
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                total_spent INTEGER DEFAULT 0
            );

            -- Свободные VPN ключи (загружает админ)
            CREATE TABLE IF NOT EXISTS vpn_keys (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key_value  TEXT UNIQUE NOT NULL,
                added_at   TEXT DEFAULT (datetime('now'))
            );

            -- Выданные ключи (история покупок)
            CREATE TABLE IF NOT EXISTS issued_keys (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                key_value    TEXT NOT NULL,
                payment_id   TEXT UNIQUE NOT NULL,
                amount       INTEGER NOT NULL,
                issued_at    TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Платежи (для защиты от двойной оплаты)
            CREATE TABLE IF NOT EXISTS payments (
                payment_id   TEXT PRIMARY KEY,
                user_id      INTEGER NOT NULL,
                amount       INTEGER NOT NULL,
                status       TEXT DEFAULT 'pending',
                created_at   TEXT DEFAULT (datetime('now')),
                confirmed_at TEXT
            );
        """)
        await db.commit()
    logger.info("База данных инициализирована: %s", db_path)


# ── Пользователи ───────────────────────────────────────────────────────────

async def get_or_create_user(db_path: str, user_id: int, username: str, full_name: str) -> None:
    """Регистрирует пользователя если не зарегистрирован."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, full_name)
               VALUES (?, ?, ?)""",
            (user_id, username, full_name)
        )
        # Обновляем имя если изменилось
        await db.execute(
            """UPDATE users SET username=?, full_name=? WHERE user_id=?""",
            (username, full_name, user_id)
        )
        await db.commit()


async def get_user_purchases(db_path: str, user_id: int) -> list:
    """Возвращает историю покупок пользователя."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT key_value, amount, issued_at
               FROM issued_keys WHERE user_id=?
               ORDER BY issued_at DESC""",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()


# ── VPN ключи ──────────────────────────────────────────────────────────────

async def add_keys(db_path: str, keys: list[str]) -> tuple[int, int]:
    """
    Добавляет список ключей в базу.
    Возвращает (добавлено, дублей пропущено).
    """
    added = 0
    skipped = 0
    async with aiosqlite.connect(db_path) as db:
        for key in keys:
            key = key.strip()
            if not key:
                continue
            try:
                await db.execute(
                    "INSERT INTO vpn_keys (key_value) VALUES (?)", (key,)
                )
                added += 1
            except aiosqlite.IntegrityError:
                # Ключ уже существует
                skipped += 1
        await db.commit()
    logger.info("Добавлено ключей: %d, пропущено дублей: %d", added, skipped)
    return added, skipped


async def get_free_keys_count(db_path: str) -> int:
    """Возвращает количество свободных ключей."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM vpn_keys") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def pop_free_key(db_path: str) -> Optional[str]:
    """
    Атомарно извлекает один свободный ключ из базы.
    Удаляет его из списка свободных.
    Возвращает ключ или None если нет.
    """
    async with aiosqlite.connect(db_path) as db:
        # Выбираем первый ключ
        async with db.execute(
            "SELECT id, key_value FROM vpn_keys ORDER BY id LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        key_id, key_value = row
        # Удаляем из свободных
        await db.execute("DELETE FROM vpn_keys WHERE id=?", (key_id,))
        await db.commit()
        return key_value


# ── Платежи ────────────────────────────────────────────────────────────────

async def create_payment(db_path: str, payment_id: str, user_id: int, amount: int) -> None:
    """Создаёт запись о новом платеже."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO payments (payment_id, user_id, amount)
               VALUES (?, ?, ?)""",
            (payment_id, user_id, amount)
        )
        await db.commit()


async def get_payment(db_path: str, payment_id: str) -> Optional[aiosqlite.Row]:
    """Возвращает запись платежа по ID."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE payment_id=?", (payment_id,)
        ) as cursor:
            return await cursor.fetchone()


async def confirm_payment(db_path: str, payment_id: str) -> None:
    """Помечает платёж как подтверждённый."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE payments SET status='confirmed',
               confirmed_at=datetime('now')
               WHERE payment_id=?""",
            (payment_id,)
        )
        await db.commit()


async def is_payment_used(db_path: str, payment_id: str) -> bool:
    """Проверяет, был ли платёж уже использован (защита от дублей)."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT id FROM issued_keys WHERE payment_id=?", (payment_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def save_issued_key(
    db_path: str, user_id: int, key_value: str, payment_id: str, amount: int
) -> None:
    """Сохраняет запись о выданном ключе и обновляет статистику."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO issued_keys (user_id, key_value, payment_id, amount)
               VALUES (?, ?, ?, ?)""",
            (user_id, key_value, payment_id, amount)
        )
        await db.execute(
            "UPDATE users SET total_spent=total_spent+? WHERE user_id=?",
            (amount, user_id)
        )
        await db.commit()


# ── Статистика (для админа) ────────────────────────────────────────────────

async def get_stats(db_path: str) -> dict:
    """Собирает общую статистику."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as cnt FROM users") as c:
            users_total = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM issued_keys"
        ) as c:
            sales_total = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM issued_keys"
        ) as c:
            revenue_total = (await c.fetchone())["total"]

        async with db.execute("SELECT COUNT(*) as cnt FROM vpn_keys") as c:
            free_keys = (await c.fetchone())["cnt"]

        async with db.execute(
            """SELECT COUNT(*) as cnt FROM issued_keys
               WHERE issued_at >= datetime('now','-1 day')"""
        ) as c:
            sales_today = (await c.fetchone())["cnt"]

        async with db.execute(
            """SELECT u.full_name, u.username, COUNT(i.id) as purchases
               FROM users u
               LEFT JOIN issued_keys i ON u.user_id=i.user_id
               GROUP BY u.user_id ORDER BY purchases DESC LIMIT 5"""
        ) as c:
            top_users = await c.fetchall()

    return {
        "users_total": users_total,
        "sales_total": sales_total,
        "revenue_total": revenue_total,
        "free_keys": free_keys,
        "sales_today": sales_today,
        "top_users": top_users,
    }
