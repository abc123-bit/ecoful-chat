from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
from loguru import logger

# 简化版配置
class SimpleSettings:
    APP_NAME = "Knowledge Base API"
    APP_VERSION = "1.0.0"
    DEBUG = True
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

settings = SimpleSettings()

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="知识库管理和RAG问答系统API（简化版）",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")

    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": exc.errors()}
    )

# 健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": "simplified"
    }

# 根路径
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} (Simplified Mode)",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

# 简化的API路由
@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "API v1 is working in simplified mode!"}

# 模拟知识库列表
@app.get("/api/v1/knowledge-bases/")
async def list_knowledge_bases():
    return [
        {
            "id": 1,
            "name": "示例知识库",
            "description": "这是一个演示知识库",
            "collection_name": "kb_demo",
            "embedding_model": "text-embedding-v1",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "status": "active",
            "file_count": 0,
            "document_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ]

# 模拟创建知识库
from pydantic import BaseModel

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""
    chunk_size: int = 1000
    chunk_overlap: int = 200

@app.post("/api/v1/knowledge-bases/")
async def create_knowledge_base(kb_data: KnowledgeBaseCreate):
    # 模拟创建成功
    return {
        "id": 2,
        "name": kb_data.name,
        "description": kb_data.description,
        "collection_name": "kb_2",
        "embedding_model": "text-embedding-v1",
        "chunk_size": kb_data.chunk_size,
        "chunk_overlap": kb_data.chunk_overlap,
        "status": "active",
        "file_count": 0,
        "document_count": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

# 模拟文件上传
@app.post("/api/v1/knowledge-bases/{kb_id}/files")
async def upload_file(kb_id: int):
    return {
        "id": 1,
        "filename": "example.pdf",
        "file_size": 1024000,
        "file_type": "pdf",
        "processing_status": "completed",
        "created_at": "2024-01-01T00:00:00Z"
    }

# 模拟获取知识库详情
@app.get("/api/v1/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: int):
    return {
        "id": kb_id,
        "name": f"知识库 {kb_id}",
        "description": "这是一个演示知识库",
        "collection_name": f"kb_{kb_id}",
        "embedding_model": "text-embedding-v1",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "status": "active",
        "file_count": 0,
        "document_count": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

# 模拟更新知识库
@app.put("/api/v1/knowledge-bases/{kb_id}")
async def update_knowledge_base(kb_id: int, kb_data: KnowledgeBaseCreate):
    return {
        "id": kb_id,
        "name": kb_data.name,
        "description": kb_data.description,
        "collection_name": f"kb_{kb_id}",
        "embedding_model": "text-embedding-v1",
        "chunk_size": kb_data.chunk_size,
        "chunk_overlap": kb_data.chunk_overlap,
        "status": "active",
        "file_count": 0,
        "document_count": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

# 模拟删除知识库
@app.delete("/api/v1/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: int):
    return {"message": "Knowledge base deleted successfully"}

# 模拟获取文件列表
@app.get("/api/v1/knowledge-bases/{kb_id}/files")
async def get_files(kb_id: int):
    return [
        {
            "id": 1,
            "filename": "示例文档.pdf",
            "file_size": 1024000,
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "processing_status": "completed",
            "chunk_count": 5,
            "created_at": "2024-01-01T00:00:00Z",
            "extracted_text": "这是从PDF中提取的示例文本内容..."
        },
        {
            "id": 2,
            "filename": "测试文档.docx",
            "file_size": 512000,
            "file_type": "docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "processing_status": "completed",
            "chunk_count": 3,
            "created_at": "2024-01-01T01:00:00Z",
            "extracted_text": "这是从Word文档中提取的示例文本内容..."
        }
    ]

# 模拟获取对话列表
@app.get("/api/v1/chat/conversations/{kb_id}")
async def get_conversations(kb_id: int):
    return [
        {
            "id": 1,
            "session_id": "demo_session_1",
            "title": "关于PDF文档的讨论",
            "message_count": 4,
            "updated_at": "2024-01-01T02:00:00Z",
            "is_active": True
        },
        {
            "id": 2,
            "session_id": "demo_session_2",
            "title": "Word文档相关问题",
            "message_count": 2,
            "updated_at": "2024-01-01T01:30:00Z",
            "is_active": True
        }
    ]

# 模拟获取对话消息
@app.get("/api/v1/chat/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    return [
        {
            "id": 1,
            "role": "user",
            "content": "这个文档主要讲什么？",
            "created_at": "2024-01-01T02:00:00Z"
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "根据文档内容，这份文档主要介绍了...",
            "created_at": "2024-01-01T02:00:30Z",
            "retrieved_chunks": [],
            "source_files": ["示例文档.pdf"]
        }
    ]

# 模拟问答
class ChatRequest(BaseModel):
    question: str
    knowledge_base_id: int
    conversation_id: str = None
    stream: bool = False
    max_chunks: int = 5

@app.post("/api/v1/chat/ask")
async def ask_question(chat_request: ChatRequest):
    return {
        "answer": f"这是对问题 '{chat_request.question}' 的模拟回答。当前运行在简化模式下，完整功能需要启动完整的后端服务。基于知识库 {chat_request.knowledge_base_id} 中的文档，我为您提供以下信息...",
        "sources": [
            {
                "file_name": "示例文档.pdf",
                "file_type": "pdf",
                "chunk_id": "chunk_1",
                "relevance_score": 0.8
            },
            {
                "file_name": "测试文档.docx",
                "file_type": "docx",
                "chunk_id": "chunk_2",
                "relevance_score": 0.6
            }
        ],
        "conversation_id": chat_request.conversation_id or "demo_conv_new",
        "message_id": "demo_msg_new",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (Simplified Mode)")
    logger.info("注意: 当前运行在简化模式下，部分功能为模拟实现")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )