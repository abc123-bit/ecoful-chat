"""
文件处理工具模块
"""
import os
import mimetypes
from typing import Optional, Tuple
from pathlib import Path
import PyPDF2
import pdfplumber
import docx
from bs4 import BeautifulSoup
import logging


class FileHandler:
    """文件处理工具类"""

    def __init__(self):
        self.supported_formats = {
            '.pdf': 'PDF',
            '.docx': 'Word',
            '.doc': 'Word',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.txt': 'Text'
        }

    def get_file_type(self, file_path: str) -> Optional[str]:
        """
        获取文件类型

        Args:
            file_path (str): 文件路径

        Returns:
            Optional[str]: 文件类型标识
        """
        if not os.path.exists(file_path):
            return None

        _, ext = os.path.splitext(file_path.lower())
        return self.supported_formats.get(ext)

    def read_pdf(self, file_path: str) -> Tuple[str, dict]:
        """
        读取PDF文件

        Args:
            file_path (str): PDF文件路径

        Returns:
            Tuple[str, dict]: (文本内容, 元数据)
        """
        text_content = ""
        metadata = {}

        try:
            # 使用pdfplumber读取PDF
            with pdfplumber.open(file_path) as pdf:
                # 提取元数据
                if pdf.metadata:
                    metadata = {
                        'title': pdf.metadata.get('Title', ''),
                        'author': pdf.metadata.get('Author', ''),
                        'subject': pdf.metadata.get('Subject', ''),
                        'creator': pdf.metadata.get('Creator', ''),
                        'producer': pdf.metadata.get('Producer', ''),
                        'creation_date': pdf.metadata.get('CreationDate', ''),
                        'mod_date': pdf.metadata.get('ModDate', '')
                    }

                # 提取文本内容
                for page in pdf.pages:
                    text_content += page.extract_text() or ""

        except Exception as e:
            logging.error(f"读取PDF文件失败: {e}")
            # 尝试使用PyPDF2作为备选方案
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text_content += page.extract_text()
            except Exception as e2:
                logging.error(f"使用PyPDF2读取PDF文件也失败: {e2}")

        return text_content, metadata

    def read_word(self, file_path: str) -> Tuple[str, dict]:
        """
        读取Word文件

        Args:
            file_path (str): Word文件路径

        Returns:
            Tuple[str, dict]: (文本内容, 元数据)
        """
        text_content = ""
        metadata = {}

        try:
            doc = docx.Document(file_path)

            # 提取文本内容
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"

            # 提取核心属性作为元数据
            core_props = doc.core_properties
            metadata = {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'created': core_props.created or '',
                'modified': core_props.modified or '',
                'subject': core_props.subject or '',
                'keywords': core_props.keywords or ''
            }

        except Exception as e:
            logging.error(f"读取Word文件失败: {e}")

        return text_content, metadata

    def read_html(self, file_path: str) -> Tuple[str, dict]:
        """
        读取HTML文件

        Args:
            file_path (str): HTML文件路径

        Returns:
            Tuple[str, dict]: (文本内容, 元数据)
        """
        text_content = ""
        metadata = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            soup = BeautifulSoup(content, 'html.parser')

            # 提取文本内容
            text_content = soup.get_text()

            # 提取元数据
            title_tag = soup.find('title')
            metadata['title'] = title_tag.get_text() if title_tag else ''

            # 提取meta标签信息
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                name = tag.get('name') or tag.get('property')
                content = tag.get('content')
                if name and content:
                    metadata[name] = content

        except Exception as e:
            logging.error(f"读取HTML文件失败: {e}")

        return text_content, metadata

    def read_text(self, file_path: str) -> Tuple[str, dict]:
        """
        读取文本文件

        Args:
            file_path (str): 文本文件路径

        Returns:
            Tuple[str, dict]: (文本内容, 元数据)
        """
        text_content = ""
        metadata = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
        except Exception as e:
            logging.error(f"读取文本文件失败: {e}")

        return text_content, metadata

    def read_file(self, file_path: str) -> Tuple[str, dict, str]:
        """
        通用文件读取方法

        Args:
            file_path (str): 文件路径

        Returns:
            Tuple[str, dict, str]: (文本内容, 元数据, 文件类型)
        """
        file_type = self.get_file_type(file_path)

        if not file_type:
            raise ValueError(f"不支持的文件格式: {file_path}")

        if file_type == 'PDF':
            content, metadata = self.read_pdf(file_path)
        elif file_type == 'Word':
            content, metadata = self.read_word(file_path)
        elif file_type == 'HTML':
            content, metadata = self.read_html(file_path)
        elif file_type == 'Text':
            content, metadata = self.read_text(file_path)
        else:
            raise ValueError(f"未实现的文件类型: {file_type}")

        return content, metadata, file_type

    def save_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> bool:
        """
        保存文件

        Args:
            file_path (str): 保存路径
            content (str): 文件内容
            encoding (str): 编码格式

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding=encoding) as file:
                file.write(content)
            return True
        except Exception as e:
            logging.error(f"保存文件失败: {e}")
            return False