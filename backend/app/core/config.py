from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Knowledge Base API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # 数据库配置
    DATABASE_URL: str

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "knowledge-base"
    MINIO_PUBLIC_ENDPOINT: Optional[str] = None
    MINIO_SECURE: bool = False

    # 百炼平台配置
    BAILIAN_API_KEY: str = "sk-7a5a21764086445a9ecc4bd389075a98"
    BAILIAN_ENDPOINT: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    BAILIAN_EMBEDDING_MODEL: str = "text-embedding-v1"
    BAILIAN_CHAT_MODEL: str = "qwen3-max"

    # Chroma配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"

    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 文件配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "text/plain",
        "text/markdown",
        "image/jpeg",
        "image/png",
        "image/gif"
    ]

    # 文本分块配置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

# 创建必要的目录
def create_directories():
    """创建必要的目录"""
    directories = [
        "uploads",
        "logs",
        settings.CHROMA_PERSIST_DIRECTORY
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化时创建目录
create_directories()