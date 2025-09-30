from fastapi import APIRouter

# 导入各个模块的路由
from app.api.v1.endpoints import knowledge_bases, chat

api_router = APIRouter()

# 注册路由
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# 临时测试端点
@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working!"}