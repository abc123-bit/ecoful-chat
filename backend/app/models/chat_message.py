from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False, comment="所属对话ID")

    # 消息内容
    role = Column(String(20), nullable=False, comment="角色: user, assistant, system")
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(String(50), default="text", comment="消息类型: text, image, file")

    # 检索上下文
    retrieved_chunks = Column(JSON, comment="检索到的文档块")
    retrieval_score = Column(Float, comment="检索相关性评分")
    source_files = Column(JSON, comment="来源文件信息")

    # AI回复相关
    model_name = Column(String(100), comment="使用的AI模型")
    prompt_tokens = Column(Integer, comment="提示词token数")
    completion_tokens = Column(Integer, comment="回复token数")
    total_tokens = Column(Integer, comment="总token数")

    # 质量评估
    quality_score = Column(Float, comment="回复质量评分")
    user_feedback = Column(String(20), comment="用户反馈: like, dislike")

    # 元数据
    message_metadata = Column(JSON, comment="消息元数据")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    conversation = relationship("ChatConversation", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"