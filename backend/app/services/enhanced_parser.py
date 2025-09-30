"""
增强版文档解析器模块
集成MinerU解析器作为高质量解析选项
"""
from typing import Dict, List, Optional
from pathlib import Path
import logging
import re

from .utils.logger import info, error
from .models.document import DocumentMetadata, ProcessedDocument
from .document_parser import DocumentParser
from .mineru_parser import MinerUParser



class EnhancedDocumentParser:
    """增强版文档解析器类"""

    def __init__(self, use_mineru: bool = False, mineru_api_token: str = None):
        """
        初始化增强版文档解析器
        Args:
            use_mineru (bool): 是否使用MinerU解析器
            mineru_api_token (str): MinerU API令牌
        """
        self.use_mineru = use_mineru
        self.basic_parser = DocumentParser()

        # 初始化MinerU解析器（如果启用）
        self.mineru_parser = None
        if self.use_mineru:
            try:
                self.mineru_parser = MinerUParser(mineru_api_token)
                info("MinerU解析器初始化成功")
            except Exception as e:
                error(f"MinerU解析器初始化失败: {e}")
                self.mineru_parser = None
                self.use_mineru = False

    def parse_document(self, file_path: str, use_mineru: Optional[bool] = None) -> ProcessedDocument:
        """
        解析文档

        Args:
            file_path (str): 文档路径
            use_mineru (bool, optional): 是否使用MinerU解析器
        Returns:
            ProcessedDocument: 处理后的文档对象
        """
        use_mineru_flag = use_mineru if use_mineru is not None else self.use_mineru

        info(f"开始解析文档 {file_path}, 使用MinerU: {use_mineru_flag}")

        processed_doc: ProcessedDocument
        if use_mineru_flag and self.mineru_parser:
            try:
                processed_doc = self._parse_with_mineru(file_path)
            except Exception as e:
                error(f"使用MinerU解析失败，回退到基础解析器: {e}")
                processed_doc = self.basic_parser.parse_document(file_path)
        else:
            processed_doc = self.basic_parser.parse_document(file_path)

        self._populate_major_sections(processed_doc)
        return processed_doc

    def _parse_with_mineru(self, file_path: str) -> ProcessedDocument:
        """
        使用MinerU解析文档

        Args:
            file_path (str): 文档路径

        Returns:
            ProcessedDocument: 处理后的文档对象
        """
        info(f"使用MinerU解析文档: {file_path}")

        try:
            result = self.mineru_parser.parse_document(file_path)

            processed_doc = ProcessedDocument()
            processed_doc.content = result

            doc_metadata = self._extract_basic_metadata(file_path)
            processed_doc.metadata = doc_metadata

            return processed_doc

        except Exception as e:
            error(f"MinerU解析失败: {e}")
            raise

    def _extract_basic_metadata(self, file_path: str) -> DocumentMetadata:
        """
        提取基础元数据
        Args:
            file_path (str): 文件路径

        Returns:
            DocumentMetadata: 文档元数据对象
        """
        metadata = DocumentMetadata()
        file_path_obj = Path(file_path)

        metadata.document_id = file_path_obj.stem
        metadata.document_name = file_path_obj.name
        metadata.document_type = file_path_obj.suffix.lower()[1:] if file_path_obj.suffix else ""

        name_parts = file_path_obj.stem.split('_')
        if len(name_parts) >= 3:
            if not metadata.document_type:
                metadata.document_type = name_parts[0]
            if not metadata.issuing_authority:
                metadata.issuing_authority = name_parts[1]

        return metadata

    def parse_documents(self, file_paths: List[str], use_mineru: Optional[bool] = None) -> List[ProcessedDocument]:
        """
        批量解析文档

        Args:
            file_paths (List[str]): 文档路径列表
            use_mineru (bool, optional): 是否使用MinerU解析器
        Returns:
            List[ProcessedDocument]: 处理后的文档对象列表
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.parse_document(file_path, use_mineru)
                results.append(result)
            except Exception as e:
                error(f"解析文档失败: {file_path}, 错误: {e}")
                empty_doc = ProcessedDocument()
                empty_doc.metadata.document_name = Path(file_path).name
                results.append(empty_doc)

        return results

    # ------------------------------------------------------------------
    # 章节拆分相关逻辑
    # ------------------------------------------------------------------
    def split_text_into_major_sections(self, text: str) -> List[Dict]:
        """
        按照大类标题拆分文本内容，仅保留一级结构（如“1 ”、“第一章”）。

        Args:
            text (str): 待拆分的文本内容

        Returns:
            List[Dict]: 拆分后的章节列表
        """
        if not text:
            return []

        lines = text.splitlines()
        if not lines:
            return []

        line_offsets: List[int] = []
        total = 0
        for line in lines:
            line_offsets.append(total)
            total += len(line) + 1  # 近似考虑换行符

        headings: List[tuple] = []
        for idx, raw_line in enumerate(lines):
            stripped_line = raw_line.strip()
            if not stripped_line.startswith('#'):
                continue
            normalized = self._normalize_heading(stripped_line)
            if not normalized:
                continue
            if self._is_major_heading(normalized):
                formatted = self._format_heading_title(normalized)
                headings.append((idx, formatted, line_offsets[idx]))

        sections: List[Dict] = []
        if not headings:
            content = text.strip()
            if content:
                sections.append(
                    {
                        "title": "全文",
                        "start_line": 1,
                        "end_line": len(lines),
                        "position": 0,
                        "content": content,
                    }
                )
            return sections

        first_line_idx = headings[0][0]
        preface = "\n".join(lines[:first_line_idx]).strip()
        if preface and not self._is_major_heading(self._normalize_heading(lines[first_line_idx])):
            sections.append(
                {
                    "title": "前言",
                    "start_line": 1,
                    "end_line": first_line_idx,
                    "position": 0,
                    "content": preface,
                }
            )

        for i, (line_idx, title, position) in enumerate(headings):
            next_line_idx = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
            chunk_lines = lines[line_idx:next_line_idx]
            chunk_text = "\n".join(chunk_lines).strip()
            if not chunk_text:
                continue
            sections.append(
                {
                    "title": title,
                    "start_line": line_idx + 1,
                    "end_line": next_line_idx,
                    "position": position,
                    "content": chunk_text,
                }
            )

        return sections

    def _normalize_heading(self, heading: str) -> str:
        text = heading.strip()
        if not text:
            return ""
        text = text.lstrip('#').strip()
        text = text.replace('\u3000', ' ').strip()
        return text

    def _is_major_heading(self, heading: str) -> bool:
        if not heading:
            return False

        plain = heading.strip()
        if plain in {"前言", "序言", "绪论"}:
            return True
        if plain.startswith("附录"):
            return True
        if re.match(r'^第[一二三四五六七八九十百零〇]+章', plain):
            return True
        if re.match(r'^[一二三四五六七八九十]+[、.]', plain) and not plain.startswith('（') and not plain.startswith('('):
            return True
        if re.match(r'^\d+(?!\.\d)', plain):
            return True
        if re.match(r'^\d+[\.、]\s*[^\d]', plain):
            return True
        return False

    def _format_heading_title(self, heading: str) -> str:
        text = heading.replace('\u3000', ' ').strip()
        text = re.sub(r'^(\d+)([^\s\.])', r'\1 \2', text)
        text = re.sub(r'^(第[一二三四五六七八九十百零〇]+章)([^\s])', r'\1 \2', text)
        return text

    def _populate_major_sections(self, processed_doc: ProcessedDocument) -> None:
        try:
            sections = self.split_text_into_major_sections(processed_doc.content)
        except Exception as exc:
            logging.getLogger(__name__).warning("拆分章节时出错: %s", exc)
            sections = []
        processed_doc.sections = sections


# 便捷函数

def parse_document(file_path: str, use_mineru: bool = False, mineru_api_token: str = None) -> ProcessedDocument:
    """
    解析文档的便捷函数
    Args:
        file_path (str): 文档路径
        use_mineru (bool): 是否使用MinerU解析器
        mineru_api_token (str): MinerU API令牌

    Returns:
        ProcessedDocument: 处理后的文档对象
    """
    parser = EnhancedDocumentParser(use_mineru, mineru_api_token)
    return parser.parse_document(file_path)


def parse_documents(file_paths: List[str], use_mineru: bool = False, mineru_api_token: str = None) -> List[ProcessedDocument]:
    """
    批量解析文档的便捷函数
    Args:
        file_paths (List[str]): 文档路径列表
        use_mineru (bool): 是否使用MinerU解析器
        mineru_api_token (str): MinerU API令牌

    Returns:
        List[ProcessedDocument]: 处理后的文档对象列表
    """
    parser = EnhancedDocumentParser(use_mineru, mineru_api_token)
    return parser.parse_documents(file_paths)
