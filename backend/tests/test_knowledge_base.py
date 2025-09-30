import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app
from app.db.database import Base
from app.models.knowledge_base import KnowledgeBase
from app.models.file import File as FileModel
from unittest.mock import Mock, patch
import io

client = TestClient(app)

# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

@pytest.fixture(scope="module")
def test_db():
    # 创建测试数据库表
    Base.metadata.create_all(bind=engine)
    yield
    # 测试完成后清理
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_create_knowledge_base():
    """测试创建知识库"""
    response = client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Test KB", "description": "Test knowledge base", "chunk_size": 1000, "chunk_overlap": 200}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test KB"
    assert "collection_name" in data

@pytest.mark.asyncio
async def test_list_knowledge_bases():
    """测试获取知识库列表"""
    response = client.get("/api/v1/knowledge-bases/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_knowledge_base():
    """测试获取特定知识库"""
    # 先创建一个知识库
    create_response = client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Test KB", "description": "Test knowledge base", "chunk_size": 1000, "chunk_overlap": 200}
    )
    assert create_response.status_code == 200
    kb_id = create_response.json()["id"]

    # 获取知识库
    response = client.get(f"/api/v1/knowledge-bases/{kb_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == kb_id
    assert data["name"] == "Test KB"

@pytest.mark.asyncio
async def test_update_knowledge_base():
    """测试更新知识库"""
    # 先创建一个知识库
    create_response = client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Test KB", "description": "Test knowledge base", "chunk_size": 1000, "chunk_overlap": 200}
    )
    assert create_response.status_code == 200
    kb_id = create_response.json()["id"]

    # 更新知识库
    update_response = client.put(
        f"/api/v1/knowledge-bases/{kb_id}",
        json={"name": "Updated KB", "description": "Updated knowledge base"}
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated KB"
    assert data["description"] == "Updated knowledge base"

@pytest.mark.asyncio
async def test_delete_knowledge_base():
    """测试删除知识库"""
    # 先创建一个知识库
    create_response = client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Test KB", "description": "Test knowledge base", "chunk_size": 1000, "chunk_overlap": 200}
    )
    assert create_response.status_code == 200
    kb_id = create_response.json()["id"]

    # 删除知识库
    response = client.delete(f"/api/v1/knowledge-bases/{kb_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Knowledge base deleted successfully"