from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import os

_raw_url = os.getenv("DATABASE_URL", "")
DATABASE_URL = (
    _raw_url
    .replace("postgresql://", "postgresql+asyncpg://", 1)
    .replace("postgres://", "postgresql+asyncpg://", 1)
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app import models  # noqa
        await conn.run_sync(Base.metadata.create_all)
        # Dodaj nowe kolumny do istniejących tabel (bezpieczne wielokrotne uruchamianie)
        await conn.execute(text(
            "ALTER TABLE tenant_settings ADD COLUMN IF NOT EXISTS reminder_2_message TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE tenant_settings ADD COLUMN IF NOT EXISTS reminder_2_days INTEGER DEFAULT 1"
        ))
        await conn.execute(text(
            "ALTER TABLE message_logs ADD COLUMN IF NOT EXISTS is_reminder_2 BOOLEAN DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS city_1 VARCHAR(200)"
        ))
        await conn.execute(text(
            "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS city_2 VARCHAR(200)"
        ))
        await conn.execute(text(
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS login_username VARCHAR(100)"
        ))
        await conn.execute(text(
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS login_password_hash VARCHAR(200)"
        ))
