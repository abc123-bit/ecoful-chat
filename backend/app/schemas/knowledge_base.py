from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: Optional[str] = Field(None, max_length=1000, description="知识库描述")
    chunk_size: int = Field(1000, ge=100, le=4000, description="文本分块大小")
    chunk_overlap: int = Field(200, ge=0, le=1000, description="分块重叠")


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    chunk_size: Optional[int] = Field(None, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000)


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    collection_name: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    status: str
    file_count: int
    document_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    processing_status: str
    created_at: datetime


class DocumentChunkResponse(BaseModel):
    id: int
    content: str
    chunk_index: int
    content_length: int
    metadata: Dict[str, Any]
    created_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_id: int = Field(..., description="知识库ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    stream: bool = Field(False, description="是否流式响应")
    max_chunks: int = Field(5, ge=1, le=20, description="最大检索块数")


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    conversation_id: str
    message_id: str
    usage: Optional[Dict[str, Any]]