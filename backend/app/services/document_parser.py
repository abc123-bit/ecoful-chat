"""
文档解析模块
"""
from typing import Tuple, Dict, List, Optional
from pathlib import Path
import re
import logging

from .utils.file_handler import FileHandler
from .utils.logger import info, error
from .models.document import DocumentMetadata, ProcessedDocument


class DocumentParser:
    """文档解析器类"""

    def __init__(self):
        self.file_handler = FileHandler()
        self.supported_formats = self.file_handler.supported_formats

    def parse_document(self, file_path: str) -> ProcessedDocument:
        """
        解析文档

        Args:
            file_path (str): 文档路径

        Returns:
            ProcessedDocument: 处理后的文档对象
        """
        info(f"开始解析文档: {file_path}")

        try:
            # 读取文件
            content, metadata, file_type = self.file_handler.read_file(file_path)

            # 创建处理后的文档对象
            processed_doc = ProcessedDocument()
            processed_doc.content = content

            # 提取基础元数据
            doc_metadata = self._extract_basic_metadata(file_path, metadata, file_type)
            processed_doc.metadata = doc_metadata

            # 提取结构信息
            sections = self._extract_sections(content)
            processed_doc.sections = sections

            # 提取表格信息（简化处理）
            tables = self._extract_tables(content)
            processed_doc.tables = tables

            # 提取图片信息（简化处理）
            images = self._extract_images(content)
            processed_doc.images = images

            info(f"文档解析完成: {file_path}")
            return processed_doc

        except Exception as e:
            error(f"解析文档失败: {file_path}, 错误: {e}")
            raise

    def _extract_basic_metadata(self, file_path: str, file_metadata: dict, file_type: str) -> DocumentMetadata:
        """
        提取基础元数据

        Args:
            file_path (str): 文件路径
            file_metadata (dict): 文件元数据
            file_type (str): 文件类型

        Returns:
            DocumentMetadata: 文档元数据对象
        """
        metadata = DocumentMetadata()
        file_path_obj = Path(file_path)

        # 基础信息
        metadata.document_id = file_path_obj.stem
        metadata.document_name = file_path_obj.name
        metadata.document_type = file_type

        # 从文件元数据中提取信息
        metadata.publish_time = str(file_metadata.get('creation_date', ''))
        metadata.effective_time = str(file_metadata.get('mod_date', ''))
        metadata.issuing_authority = str(file_metadata.get('author', ''))
        metadata.legal_level = "地方"  # 默认值，后续可以通过规则识别

        # 从文件名中提取信息（如果符合命名规范）
        # 命名规范：{文档类型}_{发布机关}_{发布年份}_{序号}_{版本}
        name_parts = file_path_obj.stem.split('_')
        if len(name_parts) >= 3:
            if not metadata.document_type:
                metadata.document_type = name_parts[0]
            if not metadata.issuing_authority:
                metadata.issuing_authority = name_parts[1]

        return metadata

    def _extract_sections(self, content: str) -> List[Dict]:
        """
        提取章节信息

        Args:
            content (str): 文档内容

        Returns:
            List[Dict]: 章节信息列表
        """
        sections = []

        # 匹配章节标题的正则表达式
        # 支持多种章节格式，如：第一章、第1章、一、1.1等
        section_patterns = [
            r'(第[一二三四五六七八九十\d]+[章节条])',
            r'([一二三四五六七八九十\d]+[\.、][\s\S]*?)(?=\n[一二三四五六七八九十\d]+[\.、]|\Z)',
            r'(\d+\.\d+[\s\S]*?)(?=\n\d+\.\d+|\Z)'
        ]

        for pattern in section_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                section = {
                    'title': match.group(1).strip(),
                    'position': match.start(),
                    'content': match.group(0).strip()
                }
                sections.append(section)

        # 按位置排序
        sections.sort(key=lambda x: x['position'])

        return sections

    def _extract_tables(self, content: str) -> List[Dict]:
        """
        提取表格信息（简化实现）

        Args:
            content (str): 文档内容

        Returns:
            List[Dict]: 表格信息列表
        """
        tables = []

        # 简单匹配表格模式（基于制表符或多个空格分隔的行）
        lines = content.split('\n')
        table_lines = []
        in_table = False

        for i, line in enumerate(lines):
            # 检查是否为表格行（包含制表符或多个空格分隔的字段）
            if '\t' in line or re.search(r'\s{2,}', line):
                if not in_table:
                    in_table = True
                    table_lines = [line]
                else:
                    table_lines.append(line)
            else:
                if in_table and len(table_lines) > 1:
                    # 认为找到了一个表格
                    table = {
                        'position': i - len(table_lines),
                        'lines': table_lines,
                        'row_count': len(table_lines)
                    }
                    tables.append(table)
                    in_table = False
                    table_lines = []

        return tables

    def _extract_images(self, content: str) -> List[Dict]:
        """
        提取图片信息（简化实现）

        Args:
            content (str): 文档内容

        Returns:
            List[Dict]: 图片信息列表
        """
        images = []

        # 对于PDF和Word文档，图片提取需要专门的库处理
        # 这里仅作为占位符实现
        # 实际实现中可能需要使用pdfplumber或python-docx的图片提取功能

        return images

    def get_supported_formats(self) -> Dict[str, str]:
        """
        获取支持的文件格式

        Returns:
            Dict[str, str]: 支持的文件格式字典
        """
        return self.supported_formats


# 便捷函数
def parse_document(file_path: str) -> ProcessedDocument:
    """
    解析文档的便捷函数

    Args:
        file_path (str): 文档路径

    Returns:
        ProcessedDocument: 处理后的文档对象
    """
    parser = DocumentParser()
    return parser.parse_document(file_path)