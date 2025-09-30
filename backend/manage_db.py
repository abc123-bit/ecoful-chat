#!/usr/bin/env python3
"""
数据库管理工具
用于初始化数据库、运行迁移等操作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
from loguru import logger

from app.core.config import settings
from app.db.database import Base, engine


def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 解析数据库URL以获取数据库名
        from urllib.parse import urlparse
        parsed = urlparse(settings.DATABASE_URL)
        db_name = parsed.path[1:]  # 去掉开头的'/'

        # 创建不包含数据库名的连接URL
        server_url = f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"

        # 连接到PostgreSQL服务器（连接到默认的postgres数据库）
        temp_engine = create_engine(server_url.replace("postgresql://", "postgresql+psycopg2://"))

        with temp_engine.connect() as conn:
            # 设置自动提交模式
            conn.execute(text("COMMIT"))

            # 检查数据库是否存在
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not result.fetchone():
                # 创建数据库
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")

        temp_engine.dispose()

    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise


def init_alembic():
    """初始化Alembic"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.init(alembic_cfg, "migrations")
        logger.info("Alembic initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Alembic: {e}")
        raise


def create_migration(message: str):
    """创建新的迁移"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.revision(alembic_cfg, autogenerate=True, message=message)
        logger.info(f"Migration '{message}' created successfully")
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise


def run_migrations():
    """运行数据库迁移"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


def reset_database():
    """重置数据库（删除所有表并重新创建）"""
    try:
        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")

        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created")

        # 标记数据库为最新版本
        alembic_cfg = Config("alembic.ini")
        command.stamp(alembic_cfg, "head")
        logger.info("Database reset completed")

    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise


def show_current_revision():
    """显示当前数据库版本"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.current(alembic_cfg)
    except Exception as e:
        logger.error(f"Failed to show current revision: {e}")
        raise


def show_migration_history():
    """显示迁移历史"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.history(alembic_cfg)
    except Exception as e:
        logger.error(f"Failed to show migration history: {e}")
        raise


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py <command> [args]")
        print("Commands:")
        print("  create-db              - Create database if not exists")
        print("  init                   - Initialize Alembic")
        print("  migrate <message>      - Create new migration")
        print("  upgrade                - Run migrations")
        print("  reset                  - Reset database (drop and recreate all tables)")
        print("  current                - Show current revision")
        print("  history                - Show migration history")
        return

    command_name = sys.argv[1]

    try:
        if command_name == "create-db":
            create_database()
        elif command_name == "init":
            init_alembic()
        elif command_name == "migrate":
            if len(sys.argv) < 3:
                print("Please provide migration message")
                return
            create_migration(sys.argv[2])
        elif command_name == "upgrade":
            run_migrations()
        elif command_name == "reset":
            confirm = input("Are you sure you want to reset the database? (yes/no): ")
            if confirm.lower() == "yes":
                reset_database()
            else:
                print("Operation cancelled")
        elif command_name == "current":
            show_current_revision()
        elif command_name == "history":
            show_migration_history()
        else:
            print(f"Unknown command: {command_name}")

    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()