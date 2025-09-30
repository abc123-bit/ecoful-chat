from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ChatConversation(Base):
    """聊天对话模型"""
    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, comment="所属知识库ID")

    # 对话信息
    title = Column(String(500), comment="对话标题")
    session_id = Column(String(255), unique=True, nullable=False, comment="会话ID")

    # 配置
    system_prompt = Column(Text, comment="系统提示词")
    retrieval_config = Column(JSON, comment="检索配置")
    chat_config = Column(JSON, comment="聊天配置")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否活跃")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_message_at = Column(DateTime(timezone=True), comment="最后消息时间")

    # 统计信息
    message_count = Column(Integer, default=0, comment="消息数量")

    # 关联关系
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatConversation(id={self.id}, session_id='{self.session_id}', title='{self.title}')>"