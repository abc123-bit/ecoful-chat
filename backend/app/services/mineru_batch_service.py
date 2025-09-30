"""MinerU批量处理服务模块。"""
import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List

import requests

from .enhanced_parser import EnhancedDocumentParser
from .mineru_parser import MinerUParser
from .utils.logger import error, info, warning


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".rtf", ".txt"}


@dataclass
class FileProcessResult:
    """记录单个文件的处理结果。"""

    file_name: str
    status: str
    message: str
    output_dir: str
    chunk_count: int = 0
    metadata_path: str = ""
    chunk_files: List[str] = None
    batch_id: str = ""
    zip_url: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "file_name": self.file_name,
            "status": self.status,
            "message": self.message,
            "output_dir": self.output_dir,
            "chunk_count": self.chunk_count,
            "metadata_path": self.metadata_path,
            "chunk_files": self.chunk_files or [],
            "batch_id": self.batch_id,
            "zip_url": self.zip_url,
        }


class MinerUBatchService:
    """封装MinerU批量上传、轮询和分段处理逻辑。"""

    def __init__(self, raw_dir: str, output_dir: str):
        self.raw_dir = Path(raw_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.section_parser = EnhancedDocumentParser()

    def process_all(self, force: bool = False) -> List[Dict[str, object]]:
        """处理raw目录下的全部文件。"""
        parser = MinerUParser()
        if not self.raw_dir.exists():
            warning(f"原始目录不存在: {self.raw_dir}")
            return []

        files = sorted([p for p in self.raw_dir.iterdir() if p.is_file()])
        if not files:
            warning(f"原始目录为空: {self.raw_dir}")
            return []

        results: List[Dict[str, object]] = []
        for file_path in files:
            result = self._process_single_file(file_path, parser, force)
            results.append(result.to_dict())
        return results

    def _process_single_file(self, file_path: Path, parser: MinerUParser, force: bool) -> FileProcessResult:
        info(f"开始处理文件: {file_path}")
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            warning(f"跳过不支持的文件格式: {file_path.name}")
            return FileProcessResult(
                file_name=file_path.name,
                status="skipped",
                message="unsupported file extension",
                output_dir=""
            )

        target_dir = self.output_dir / file_path.stem
        if target_dir.exists() and force:
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            parse_response = parser.parse_document(str(file_path), output_format="json")
        except Exception as exc:
            error(f"调用MinerU失败: {exc}")
            return FileProcessResult(
                file_name=file_path.name,
                status="failed",
                message=str(exc),
                output_dir=str(target_dir)
            )

        try:
            response_data = json.loads(parse_response)
        except json.JSONDecodeError as exc:
            error(f"MinerU返回数据格式错误: {exc}")
            fallback_path = target_dir / "mineru_raw.txt"
            fallback_path.write_text(parse_response, encoding="utf-8")
            return FileProcessResult(
                file_name=file_path.name,
                status="failed",
                message="invalid JSON response",
                output_dir=str(target_dir)
            )

        batch_id = response_data.get("batch_id", "")
        response_data = self._wait_for_completion(parser, batch_id, response_data)
        results = response_data.get("extract_result", [])
        if not results:
            warning(f"未获得MinerU解析结果: {file_path.name}")
            return FileProcessResult(
                file_name=file_path.name,
                status="failed",
                message="empty extract_result",
                output_dir=str(target_dir)
            )

        for result_entry in results:
            state = result_entry.get("state")
            if state != "done":
                warning(f"文件尚未完成解析: {file_path.name}, 状态: {state}")
                continue

            zip_url = result_entry.get("full_zip_url")
            if not zip_url:
                warning(f"未提供结果压缩包地址: {file_path.name}")
                continue

            extracted_dir = target_dir / "mineru_raw"
            self._download_and_extract(zip_url, extracted_dir)

            full_md_path = self._locate_file(extracted_dir, "full.md")
            if not full_md_path.exists():
                warning(f"未找到full.md: {file_path.name}")
                continue

            markdown_text = full_md_path.read_text(encoding="utf-8", errors="ignore")
            sections = self._split_into_major_sections(markdown_text)
            chunks = self._build_chunks(sections, {
                "batch_id": batch_id,
                "data_id": result_entry.get("data_id", ""),
                "mineru_file_name": result_entry.get("file_name", file_path.name),
                "original_file_name": file_path.name,
                "original_file_size": file_path.stat().st_size,
                "extracted_root": str(extracted_dir),
            })

            if not chunks:
                warning(f"未生成任何拆分结果: {file_path.name}")
                continue

            chunk_dir = target_dir / "chunks"
            self._write_chunks(chunks, chunk_dir)
            metadata_path = self._save_metadata({
                "batch_id": batch_id,
                "data_id": result_entry.get("data_id", ""),
                "mineru_file_name": result_entry.get("file_name", file_path.name),
                "original_file_name": file_path.name,
                "original_file_size": file_path.stat().st_size,
                "chunk_count": len(chunks),
                "zip_url": zip_url,
            }, target_dir)

            chunk_files = sorted(p.name for p in chunk_dir.glob("chunk_*.json"))
            info(f"处理完成: {file_path}")
            return FileProcessResult(
                file_name=file_path.name,
                status="success",
                message="",
                output_dir=str(target_dir),
                chunk_count=len(chunks),
                metadata_path=str(metadata_path),
                chunk_files=chunk_files,
                batch_id=batch_id,
                zip_url=zip_url,
            )

        return FileProcessResult(
            file_name=file_path.name,
            status="failed",
            message="no completed entries",
            output_dir=str(target_dir)
        )

    def _wait_for_completion(self, parser: MinerUParser, batch_id: str, initial: Dict[str, object], *, interval: int = 5, max_attempts: int = 24) -> Dict[str, object]:
        if not batch_id:
            return initial

        data = initial
        for _ in range(max_attempts):
            pending = [entry for entry in data.get("extract_result", []) if entry.get("state") != "done"]
            if not pending:
                return data
            time.sleep(interval)
            raw = parser._get_processing_result(batch_id)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                error("轮询MinerU结果时解析JSON失败")
                return initial
        warning(f"超过最大轮询次数仍未完成: batch {batch_id}")
        return data

    def _download_and_extract(self, zip_url: str, output_dir: Path) -> None:
        info(f"下载MinerU结果: {zip_url}")
        response = requests.get(zip_url, stream=True, timeout=120)
        response.raise_for_status()

        buffer = BytesIO()
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                buffer.write(chunk)
        buffer.seek(0)

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(buffer) as zf:
            zf.extractall(output_dir)

    def _locate_file(self, root: Path, filename: str) -> Path:
        for path in root.rglob(filename):
            return path
        return root / filename

    def _split_into_major_sections(self, markdown_text: str) -> List[Dict[str, object]]:
        return self.section_parser.split_text_into_major_sections(markdown_text)

    def _make_chunk_id(self, title: str, index: int) -> str:
        slug = re.sub(r"[^0-9A-Za-z]+", " ", title).strip().replace(" ", "_").lower()
        return f"section_{slug}" if slug else f"section_{index:02d}"

    def _build_chunks(self, sections: List[Dict[str, object]], source: Dict[str, object]) -> List[Dict[str, object]]:
        chunks: List[Dict[str, object]] = []
        for index, section in enumerate(sections, start=1):
            content = section.get("content", "").strip()
            if not content:
                continue
            chunk = {
                "id": self._make_chunk_id(section.get("title", ""), index),
                "title": section.get("title", f"Section {index}"),
                "start_line": section.get("start_line", 1),
                "end_line": section.get("end_line", section.get("start_line", 1)),
                "position": section.get("position", 0),
                "char_count": len(content),
                "content": content,
                "source_file": source,
            }
            chunks.append(chunk)
        return chunks

    def _write_chunks(self, chunks: List[Dict[str, object]], chunk_dir: Path) -> None:
        if chunk_dir.exists():
            shutil.rmtree(chunk_dir)
        chunk_dir.mkdir(parents=True, exist_ok=True)

        for index, chunk in enumerate(chunks, start=1):
            file_path = chunk_dir / f"chunk_{index:02d}.json"
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(chunk, fp, ensure_ascii=False, indent=2)
            info(f"写入拆分结果: {file_path}")

    def _save_metadata(self, metadata: Dict[str, object], output_dir: Path) -> Path:
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, ensure_ascii=False, indent=2)
        info(f"保存处理元数据: {metadata_path}")
        return metadata_path
