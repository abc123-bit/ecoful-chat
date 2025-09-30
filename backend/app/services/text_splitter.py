
from __future__ import annotations
import re
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from loguru import logger

# ==================== 文本分块器 ====================
class TextSplitter(ABC):
    """文本分块器基类"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """分割文本为块"""
        pass

# ==================== 具体分块器实现 ====================
class RecursiveCharacterTextSplitter(TextSplitter):
    """递归字符文本分块器"""

    # 默认分隔符列表，按优先级从高到低
    # pthon中的字符串中，反斜杠需要转义，所以\n表示
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        super().__init__(chunk_size, chunk_overlap)
        ## 默认分隔符列表，按优先级从高到低
        ## pthon中的字符串中，反斜杠需要转义，所以\n表示换行符
        self.separators = separators or [
            "\n\n",  # 段落分隔符
            "\n",     # 行分隔符
            "。",      # 中文句号
            "！",      # 中文感叹号
            "？",      # 中文问号
            ".",      # 英文句号
            "!",      # 英文感叹号
            "?",      # 英文问号
            ";",      # 分号
            ",",      # 逗号
            " ",      # 空格
            ""        # 字符级分割
        ]

    # 递归分割文本
    def split_text(self, text: str) -> List[str]:
        """递归分割文本"""
        if not text:
            return []

        # 如果文本长度小于等于chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        current_separator_index = 0

        # 递归尝试不同的分隔符
        chunks = self._split_with_separator(
            text, self.separators[current_separator_index], current_separator_index
        )

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    # 使用指定分隔符分割文本
    def _split_with_separator(
        self, text: str, separator: str, separator_index: int
    ) -> List[str]:
        """使用指定分隔符分割文本"""
        if not separator:
            # 字符级分割
            return self._character_split(text)

        # 按分隔符分割
        splits = text.split(separator)
        chunks = []
        current_chunk = ""

        for split in splits:
            # 如果split本身就太长，需要进一步分割
            if len(split) > self.chunk_size:
                # 先处理当前积累的chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 递归使用下一个分隔符
                if separator_index + 1 < len(self.separators):
                    sub_chunks = self._split_with_separator(
                        split, self.separators[separator_index + 1], separator_index + 1
                    )
                    chunks.extend(sub_chunks)
                else:
                    # 没有更多分隔符，字符级分割
                    sub_chunks = self._character_split(split)
                    chunks.extend(sub_chunks)
            else:
                # 检查加入这个split后是否超过chunk_size
                test_chunk = current_chunk + separator + split if current_chunk else split

                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # 超过了，保存当前chunk并开始新的
                    if current_chunk:
                        chunks.append(current_chunk)

                    current_chunk = split

        # 处理最后的chunk
        if current_chunk:
            chunks.append(current_chunk)

        # 处理重叠
        return self._handle_overlap(chunks)

    # 字符级分割
    def _character_split(self, text: str) -> List[str]:
        """字符级分割"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap

        return chunks

    # 处理块之间的重叠
    def _handle_overlap(self, chunks: List[str]) -> List[str]:
        """处理块之间的重叠"""
        if not chunks or self.chunk_overlap == 0:
            return chunks

        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # 从前一个chunk取重叠部分
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) >= self.chunk_overlap else prev_chunk

                # 合并重叠文本和当前chunk
                overlapped_chunk = overlap_text + chunk
                overlapped_chunks.append(overlapped_chunk)

        return overlapped_chunks

# Markdown文本分块器
class MarkdownTextSplitter(TextSplitter):
    """Markdown文本分块器"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        self.separators = [
            "\n## ",    # 二级标题
            "\n### ",   # 三级标题
            "\n#### ",  # 四级标题
            "\n##### ", # 五级标题
            "\n\\n",    # 段落
            "\n",       # 行
            " ",        # 空格
            ""          # 字符
        ]

    def split_text(self, text: str) -> List[str]:
        """分割Markdown文本"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators
        )
        return splitter.split_text(text)

# 档分块处理器
class DocumentChunkProcessor:
    """文档分块处理器"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks(
        self,
        text: str,
        file_metadata: Dict,
        splitter_type: str = "recursive"
    ) -> List[Dict]:
        """
        创建文档块

        Args:
            text: 文档文本
            file_metadata: 文件元数据
            splitter_type: 分块器类型

        Returns:
            List[chunk_dict]
        """
        # 选择分块器
        if splitter_type == "markdown":
            splitter = MarkdownTextSplitter(self.chunk_size, self.chunk_overlap)
        else:
            splitter = RecursiveCharacterTextSplitter(self.chunk_size, self.chunk_overlap)

        # 分割文本
        text_chunks = splitter.split_text(text)

        # 创建块对象
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            if not chunk_text.strip():
                continue

            # 创建一个基础元数据字典，包含文件级别信息
            base_metadata = {
                "source_file": file_metadata.get("original_filename"),
                "file_type": file_metadata.get("file_type"),
                "processor_type": file_metadata.get("processor_type"),
                "chunk_method": splitter_type,
                "total_chunks": len(text_chunks),
                "chunk_position": i + 1,
            }

            # 提取块级别的元数据
            chunk_specific_metadata = self._extract_chunk_metadata(chunk_text, file_metadata)

            # 合并所有元数据
            full_metadata = {**base_metadata, **chunk_specific_metadata}
            
            # 如果元数据为空
            if not full_metadata: 
                full_metadata = {
                    "source_file": file_metadata.get("original_filename", "unknown"),
                    "file_type": file_metadata.get("file_type", "unknown"),
                    "chunk_index": i,
                    "chunk_position": i + 1,
                    "total_chunks": len(text_chunks)
                }
                
            # 创建块字典
            chunk = {
                "content": chunk_text,
                "chunk_index": i,
                "content_length": len(chunk_text),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "metadata": full_metadata
            }

            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks

    def _extract_chunk_metadata(self, chunk_text: str, file_metadata: Dict) -> Dict:
        """提取块的元数据"""
        metadata = {}

        # 统计信息
        metadata["word_count"] = len(chunk_text.split())
        metadata["char_count"] = len(chunk_text)
        metadata["line_count"] = len(chunk_text.splitlines())

        # 检测内容类型
        if self._is_table_content(chunk_text):
            metadata["content_type"] = "table"
        elif self._is_list_content(chunk_text):
            metadata["content_type"] = "list"
        elif self._is_code_content(chunk_text):
            metadata["content_type"] = "code"
        else:
            metadata["content_type"] = "text"

        # 提取关键词（简单实现）
        keywords = self._extract_keywords(chunk_text)
        if keywords:
            metadata["keywords"] = keywords

        return metadata

    def _is_table_content(self, text: str) -> bool:
        """检测是否为表格内容"""
        return "|" in text and text.count("|") > 2

    def _is_list_content(self, text: str) -> bool:
        """检测是否为列表内容"""
        lines = text.splitlines()
        list_indicators = ["•", "●", "○", "▪", "▫", "-", "*", "+"]
        numbered_pattern = re.compile(r'^\\s*\\d+[.)、]')

        list_lines = 0
        for line in lines:
            line = line.strip()
            if (any(line.startswith(indicator) for indicator in list_indicators) or
                numbered_pattern.match(line)):
                list_lines += 1

        return list_lines > 0 and list_lines / len(lines) > 0.3

    def _is_code_content(self, text: str) -> bool:
        """检测是否为代码内容"""
        code_indicators = ["```", "def ", "function ", "class ", "import ", "from ", "<?", "?>"]
        return any(indicator in text for indicator in code_indicators)

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词（简单实现）"""
        # 移除标点和特殊字符
        cleaned_text = re.sub(r'[^\\w\\s]', ' ', text.lower())
        words = cleaned_text.split()

        # 过滤停用词（简单版本）
        stop_words = {
            "的", "是", "在", "有", "和", "与", "或", "但", "而", "了", "也", "都", "还", "就",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "is", "are", "was", "were", "be", "been", "being", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should"
        }

        filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]

        # 统计词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 返回频率最高的词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]

# 创建全局文档分块处理器实例
def create_document_chunks(
    text: str,
    file_metadata: Dict,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    splitter_type: str = "recursive"
) -> List[Dict]:
    """创建文档块的便捷函数"""
    processor = DocumentChunkProcessor(chunk_size, chunk_overlap)
    return processor.create_chunks(text, file_metadata, splitter_type)

# ==================== 旧 Markdown 拆分（回退） ====================
def _md_soft_split(text: str, max_len: int) -> List[str]:
    if len(text) <= max_len:
        return [text]
    parts = re.split(r"([。！？!?；;]\s*)", text)
    buf, out = "", []
    for i in range(0, len(parts), 2):
        seg = parts[i]
        tail = parts[i + 1] if i + 1 < len(parts) else ""
        candidate = buf + seg + tail
        if len(candidate) >= max_len and buf:
            out.append(buf)
            buf = seg + tail
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out

# 旧 Markdown 拆分（回退）
def _legacy_markdown_split(text: str, chunk_size: int, chunk_overlap: int) -> List[Dict]:
    blocks: List[str] = []
    last = 0
    pattern = re.compile(r"(^# .+$|^## .+$|^### .+$|^----+$|^\d+\.\s+.+$|^[-*+]\s+.+$)", re.MULTILINE)
    for m in pattern.finditer(text):
        start = m.start()
        if start > last:
            blocks.append(text[last:start].strip())
        blocks.append(text[start:m.end()].strip())
        last = m.end()
    tail = text[last:].strip()
    if tail:
        blocks.append(tail)
    blocks = [b for b in blocks if b]

    refined: List[str] = []
    for b in blocks:
        if len(b) > chunk_size:
            refined.extend(_md_soft_split(b, chunk_size))
        else:
            refined.append(b)

    chunks: List[Dict] = []
    for i, content in enumerate(refined):
        if not content:
            continue
        chunks.append({
            "content": content,
            "chunk_index": i,
            "content_length": len(content),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "metadata": {"splitter": "legacy_markdown"},
        })
    return chunks

# ==================== 服务层入口（带回退） ====================
def split_text(
    text: str,
    file_metadata: Optional[Dict] = None,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    splitter_type: str = "recursive"
) -> List[Dict]:
    """
    对外服务层入口：
    - 优先调用 create_document_chunks（你项目的分块实现）；
    - 若分块为空或仅 1 块，则回退到 _legacy_markdown_split。
    """
    file_metadata = file_metadata or {}
    try:
        chunks = create_document_chunks(
            text=text,
            file_metadata=file_metadata,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_type=splitter_type,
        )
        logger.info(f"core 分块完成，共 {len(chunks)} 块")
    except Exception as e:
        logger.warning(f"core 分块失败，使用 legacy markdown 回退：{e}")
        chunks = []

    if not chunks or len(chunks) <= 1:
        legacy_chunks = _legacy_markdown_split(text, chunk_size, chunk_overlap)
        if not chunks:
            chunks = legacy_chunks
        elif len(chunks) == 1 and len(legacy_chunks) > 1:
            chunks = legacy_chunks

    # 补齐字段 & 合并元数据
    for i, ch in enumerate(chunks):
        ch.setdefault("chunk_index", i)
        ch.setdefault("chunk_size", chunk_size)
        ch.setdefault("chunk_overlap", chunk_overlap)
        meta = ch.get("metadata",  {}) or {}
        ch["metadata"] = {**file_metadata, **meta}
        ch.setdefault("content_length", len(ch.get("content", "") or ""))

    return chunks
