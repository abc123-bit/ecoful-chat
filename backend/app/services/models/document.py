"""
文档模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional
import json


@dataclass
class DocumentMetadata:
    """文档元数据结构"""
    document_id: str = ""
    document_name: str = ""
    document_type: str = ""
    publish_time: str = ""
    effective_time: str = ""
    issuing_authority: str = ""
    legal_level: str = ""  # "国家|地方"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "publish_time": self.publish_time,
            "effective_time": self.effective_time,
            "issuing_authority": self.issuing_authority,
            "legal_level": self.legal_level
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentMetadata':
        """从字典创建实例"""
        return cls(
            document_id=data.get("document_id", ""),
            document_name=data.get("document_name", ""),
            document_type=data.get("document_type", ""),
            publish_time=data.get("publish_time", ""),
            effective_time=data.get("effective_time", ""),
            issuing_authority=data.get("issuing_authority", ""),
            legal_level=data.get("legal_level", "")
        )


@dataclass
class ProcessedDocument:
    """处理后的文档结构"""
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    content: str = ""
    sections: List[dict] = field(default_factory=list)  # 章节信息
    tables: List[dict] = field(default_factory=list)    # 表格信息
    images: List[dict] = field(default_factory=list)    # 图片信息

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "metadata": self.metadata.to_dict(),
            "content": self.content,
            "sections": self.sections,
            "tables": self.tables,
            "images": self.images
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedDocument':
        """从字典创建实例"""
        metadata = DocumentMetadata.from_dict(data.get("metadata", {}))
        return cls(
            metadata=metadata,
            content=data.get("content", ""),
            sections=data.get("sections", []),
            tables=data.get("tables", []),
            images=data.get("images", [])
        )