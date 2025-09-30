from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, BigInteger, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class File(Base):
    """文件模型"""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, comment="所属知识库ID")

    # 文件基本信息
    filename = Column(String(500), nullable=False, comment="原文件名")
    file_type = Column(String(100), nullable=False, comment="文件类型")
    mime_type = Column(String(200), comment="MIME类型")
    file_size = Column(BigInteger, comment="文件大小(字节)")
    file_hash = Column(String(64), comment="文件MD5哈希")

    # 存储信息
    storage_path = Column(String(1000), comment="MinIO存储路径")
    bucket_name = Column(String(255), comment="MinIO桶名")
    object_key = Column(String(1000), comment="MinIO对象键")

    # 处理状态
    processing_status = Column(String(50), default="pending", comment="处理状态: pending, processing, completed, failed")
    processing_error = Column(Text, comment="处理错误信息")
    processing_progress = Column(Integer, default=0, comment="处理进度(0-100)")

    # 提取的内容
    extracted_text = Column(Text, comment="提取的文本内容")
    extracted_metadata = Column(JSON, comment="提取的元数据")

    # 向量化状态
    vectorization_status = Column(String(50), default="pending", comment="向量化状态: pending, processing, completed, failed")
    vectorization_error = Column(Text, comment="向量化错误信息")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    processed_at = Column(DateTime(timezone=True), comment="处理完成时间")

    # 统计信息
    chunk_count = Column(Integer, default=0, comment="生成的文档块数量")

    # 关联关系
    knowledge_base = relationship("KnowledgeBase", back_populates="files")
    document_chunks = relationship("DocumentChunk", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        try:
            # 检查对象是否已附加到会话
            if hasattr(self, '_sa_instance_state'):
                from sqlalchemy import inspect as sa_inspect
                # 检查对象是否已分离
                if sa_inspect(self).detached:
                    return "<File(id=None, filename=None, status=None)>"

            # 使用 sqlalchemy.inspect 检查对象状态，避免触发数据库查询
            return "<File(id=%r, filename=%r, status=%r)>" % (
                getattr(self, 'id', None),
                getattr(self, 'filename', None),
                getattr(self, 'processing_status', None)
            )
        except:
            return "<File(无法加载属性)>"