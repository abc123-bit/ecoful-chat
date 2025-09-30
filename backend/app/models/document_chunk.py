from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DocumentChunk(Base):
    """文档块模型"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, comment="所属知识库ID")
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, comment="所属文件ID")

    # 内容信息
    content = Column(Text, nullable=False, comment="文档块内容")
    content_length = Column(Integer, comment="内容长度")
    content_hash = Column(String(64), comment="内容哈希")

    # 位置信息
    chunk_index = Column(Integer, comment="在文件中的块索引")
    start_pos = Column(Integer, comment="在原文档中的起始位置")
    end_pos = Column(Integer, comment="在原文档中的结束位置")

    # 分块参数
    chunk_size = Column(Integer, comment="分块大小")
    chunk_overlap = Column(Integer, comment="重叠大小")

    # 向量信息
    vector_id = Column(String(255), comment="在向量数据库中的ID")
    embedding_model = Column(String(100), comment="使用的嵌入模型")
    embedding_dimensions = Column(Integer, comment="向量维度")

    # 元数据
    chunk_metadata = Column(JSON, comment="文档块元数据")

    # 质量评分
    quality_score = Column(Float, comment="内容质量评分")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    vectorized_at = Column(DateTime(timezone=True), comment="向量化时间")

    # 关联关系
    knowledge_base = relationship("KnowledgeBase", back_populates="document_chunks")
    file = relationship("File", back_populates="document_chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, kb_id={self.knowledge_base_id}, file_id={self.file_id})>"