from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="知识库名称")
    description = Column(Text, comment="知识库描述")

    # 向量数据库相关
    collection_name = Column(String(255), unique=True, nullable=False, comment="Chroma集合名称")
    embedding_model = Column(String(100), default="text-embedding-v3", comment="嵌入模型")

    # 分块配置
    chunk_size = Column(Integer, default=1000, comment="文本分块大小")
    chunk_overlap = Column(Integer, default=200, comment="分块重叠")

    # 检索配置
    retrieval_config = Column(JSON, comment="检索配置")

    # 状态
    status = Column(String(50), default="active", comment="状态: active, archived, deleted")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 统计信息
    file_count = Column(Integer, default=0, comment="文件数量")
    document_count = Column(Integer, default=0, comment="文档块数量")

    # 关联关系
    files = relationship("File", back_populates="knowledge_base", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("ChatConversation", back_populates="knowledge_base", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name='{self.name}', status='{self.status}')>"