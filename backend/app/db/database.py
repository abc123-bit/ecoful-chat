from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings

# 同步数据库引擎（用于Alembic迁移）
engine = create_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# 异步数据库引擎（用于API操作）
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine
)

# 基础模型类
Base = declarative_base()

# 依赖注入：获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 同步数据库会话（用于迁移脚本）
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 依赖注入：获取异步数据库会话
from typing import AsyncGenerator

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话的上下文管理器"""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()