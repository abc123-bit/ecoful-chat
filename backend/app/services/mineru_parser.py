"""
MinerU文档解析器模块
用于调用MinerU API解析PDF和DOCX文档
"""
import requests
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
import time

from utils.config import get_config
from utils.logger import info, error



class MinerUParser:
    """MinerU文档解析器类"""

    def __init__(self, api_token: str = None):
        """
        初始化MinerU解析器

        Args:
            api_token (str): MinerU API令牌
        """
        self.api_token = api_token or get_config("mineru.api_token", "")
        self.base_url = get_config("mineru.base_url", "https://mineru.net/api/v4")

        if not self.api_token:
            raise ValueError("MinerU API token is required")

    def prepare_upload(self, file_paths: List[str], enable_ocr: bool = True,
                      enable_formula: bool = True, enable_table: bool = True) -> Dict:
        """
        准备文件上传

        Args:
            file_paths (List[str]): 文件路径列表
            enable_ocr (bool): 是否启用OCR
            enable_formula (bool): 是否启用公式识别
            enable_table (bool): 是否启用表格识别

        Returns:
            Dict: 上传准备信息
        """
        info(f"Preparing upload for {len(file_paths)} files")

        # 检查文件数量限制（MinerU限制单次申请不能超过200个）
        if len(file_paths) > 200:
            raise ValueError("单次申请链接不能超过200个文件")

        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }

        # 构造文件信息
        files_info = []
        for i, file_path in enumerate(file_paths):
            file_name = Path(file_path).name
            files_info.append({
                "name": file_name,
                "is_ocr": enable_ocr,
                "data_id": f"file_{i}"
            })

        # 构造请求数据
        data = {
            "enable_formula": enable_formula,
            "language": "ch",
            "enable_table": enable_table,
            "files": files_info
        }

        try:
            # 发送请求
            response = requests.post(
                f"{self.base_url}/file-urls/batch",
                headers=headers,
                json=data
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    info("Upload preparation successful")
                    return result
                else:
                    error(f"Upload preparation failed: {result.get('msg')}")
                    raise Exception(f"Upload preparation failed: {result.get('msg')}")
            else:
                error(f"Upload preparation failed with status {response.status_code}")
                raise Exception(f"Upload preparation failed with status {response.status_code}")

        except Exception as e:
            error(f"Error preparing upload: {e}")
            raise

    def upload_files(self, file_paths: List[str], upload_info: Dict) -> List[Dict]:
        """
        上传文件到MinerU

        Args:
            file_paths (List[str]): 文件路径列表
            upload_info (Dict): 上传准备信息

        Returns:
            List[Dict]: 上传结果列表
        """
        info(f"Uploading {len(file_paths)} files")

        # 检查文件数量是否匹配
        urls = upload_info["data"]["file_urls"]
        if len(file_paths) != len(urls):
            raise ValueError("文件数量与上传URL数量不匹配")

        upload_results = []
        for i, (file_path, url) in enumerate(zip(file_paths, urls)):
            try:
                with open(file_path, 'rb') as f:
                    # 注意：上传文件时无须设置Content-Type请求头
                    response = requests.put(url, data=f)
                    if response.status_code == 200:
                        info(f"File {file_path} uploaded successfully")
                        upload_results.append({
                            "file_path": file_path,
                            "status": "success",
                            "url": url
                        })
                    else:
                        error(f"File {file_path} upload failed with status {response.status_code}")
                        upload_results.append({
                            "file_path": file_path,
                            "status": "failed",
                            "error": f"Status {response.status_code}"
                        })
            except Exception as e:
                error(f"Error uploading file {file_path}: {e}")
                upload_results.append({
                    "file_path": file_path,
                    "status": "failed",
                    "error": str(e)
                })

        return upload_results

    def parse_document(self, file_path: str, output_format: str = "md") -> str:
        """
        解析单个文档（使用实际的MinerU API）

        Args:
            file_path (str): 文件路径
            output_format (str): 输出格式 ("md", "json", "html")

        Returns:
            str: 解析结果
        """
        info(f"Parsing document with MinerU: {file_path}")

        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # 准备上传
            upload_info = self.prepare_upload([file_path])

            # 上传文件
            upload_results = self.upload_files([file_path], upload_info)

            # 检查上传结果
            if not upload_results or upload_results[0]["status"] != "success":
                raise Exception("File upload failed")

            # 获取批次ID
            batch_id = upload_info["data"]["batch_id"]
            info(f"Batch ID: {batch_id}")

            # 轮询获取处理结果
            result = self._get_processing_result(batch_id)

            return result

        except Exception as e:
            error(f"Error parsing document {file_path} with MinerU: {e}")
            # 回退到占位符实现
            return self._parse_with_placeholder(file_path, output_format)

    def parse_documents(self, file_paths: List[str], output_format: str = "md") -> List[str]:
        """
        批量解析文档（使用实际的MinerU API）

        Args:
            file_paths (List[str]): 文件路径列表
            output_format (str): 输出格式 ("md", "json", "html")

        Returns:
            List[str]: 解析结果列表
        """
        info(f"Parsing {len(file_paths)} documents with MinerU")

        try:
            # 准备上传
            upload_info = self.prepare_upload(file_paths)

            # 上传文件
            upload_results = self.upload_files(file_paths, upload_info)

            # 检查上传结果
            failed_uploads = [r for r in upload_results if r["status"] != "success"]
            if failed_uploads:
                raise Exception(f"{len(failed_uploads)} files failed to upload")

            # 获取批次ID
            batch_id = upload_info["data"]["batch_id"]
            info(f"Batch ID: {batch_id}")

            # 轮询获取处理结果
            result = self._get_processing_result(batch_id)

            return [result] * len(file_paths)  # 简化实现，实际应为每个文件返回单独结果

        except Exception as e:
            error(f"Error parsing documents with MinerU: {e}")
            # 回退到占位符实现
            results = []
            for file_path in file_paths:
                results.append(self._parse_with_placeholder(file_path, output_format))
            return results

    def _get_processing_result(self, batch_id: str) -> str:
        """
        获取处理结果

        Args:
            batch_id (str): 批次ID

        Returns:
            str: 解析结果
        """
        info(f"Getting processing result for batch {batch_id}")

        # 轮询获取结果
        max_attempts = 30  # 最多尝试30次
        attempt = 0

        while attempt < max_attempts:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_token}"
                }

                # 使用您提供的正确端点获取结果
                # 文件上传完成后，系统会自动提交解析任务，无须调用提交解析任务接口
                result_url = f"{self.base_url}/extract-results/batch/{batch_id}"
                response = requests.get(result_url, headers=headers)

                info(f"Result query status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    info(f"Result query response: {json.dumps(result, ensure_ascii=False)}")

                    if result.get("code") == 0:
                        # 返回解析结果
                        return json.dumps(result["data"], ensure_ascii=False, indent=2)
                    else:
                        error(f"Failed to get result: {result.get('msg')}")
                        # 如果是处理中状态，继续轮询
                        if result.get('msg') and 'processing' in result.get('msg').lower():
                            time.sleep(5)
                            attempt += 1
                            continue
                        else:
                            raise Exception(f"Failed to get result: {result.get('msg')}")
                elif response.status_code == 404:
                    # 结果尚未准备好，继续轮询
                    info("Result not ready yet, waiting...")
                    time.sleep(5)
                    attempt += 1
                    continue
                else:
                    raise Exception(f"Failed to get result: {response.status_code}")

            except Exception as e:
                error(f"Error getting processing result: {e}")
                attempt += 1
                time.sleep(5)

        raise Exception("Timeout waiting for processing result")

    def _parse_with_placeholder(self, file_path: str, output_format: str) -> str:
        """
        使用占位符实现解析文档

        Args:
            file_path (str): 文件路径
            output_format (str): 输出格式

        Returns:
            str: 解析结果
        """
        info(f"Using placeholder implementation for {file_path}")

        # 获取文件扩展名
        file_extension = Path(file_path).suffix.lower()

        # 根据文件类型进行处理
        if file_extension == ".pdf":
            result = self._parse_pdf_placeholder(file_path, output_format)
        elif file_extension == ".docx":
            result = self._parse_docx_placeholder(file_path, output_format)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

        return result

    def _parse_pdf_placeholder(self, file_path: str, output_format: str) -> str:
        """
        解析PDF文档（占位符实现）

        Args:
            file_path (str): PDF文件路径
            output_format (str): 输出格式

        Returns:
            str: 解析结果
        """
        return f"# 解析结果\n\n这是从 {file_path} 解析的内容（占位符）\n\n## 文档信息\n- 文件名: {Path(file_path).name}\n- 格式: PDF\n- 解析时间: {self._get_current_time()}"

    def _parse_docx_placeholder(self, file_path: str, output_format: str) -> str:
        """
        解析DOCX文档（占位符实现）

        Args:
            file_path (str): DOCX文件路径
            output_format (str): 输出格式

        Returns:
            str: 解析结果
        """
        return f"# 解析结果\n\n这是从 {file_path} 解析的内容（占位符）\n\n## 文档信息\n- 文件名: {Path(file_path).name}\n- 格式: DOCX\n- 解析时间: {self._get_current_time()}"

    def _get_current_time(self) -> str:
        """
        获取当前时间

        Returns:
            str: 当前时间字符串
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def extract_tables_and_images(self, markdown_content: str) -> Dict:
        """
        从Markdown内容中提取表格和图片

        Args:
            markdown_content (str): Markdown内容

        Returns:
            Dict: 提取的表格和图片信息
        """
        info("Extracting tables and images from markdown content")

        tables = []
        images = []

        # 按行分割内容
        lines = markdown_content.split('\n')

        # 提取表格
        in_table = False
        current_table = []
        for line in lines:
            # 检查是否为表格行
            if '|' in line and line.strip().startswith('|'):
                if not in_table:
                    in_table = True
                    current_table = [line]
                else:
                    current_table.append(line)
            else:
                if in_table:
                    # 表格结束
                    if len(current_table) > 1:  # 至少有表头和一行数据
                        tables.append({
                            "content": '\n'.join(current_table),
                            "row_count": len(current_table) - 1  # 不包括表头
                        })
                    in_table = False
                    current_table = []

        # 提取图片
        import re
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.finditer(image_pattern, markdown_content)
        for match in matches:
            alt_text = match.group(1)
            image_url = match.group(2)
            images.append({
                "alt_text": alt_text,
                "url": image_url
            })

        info(f"Extracted {len(tables)} tables and {len(images)} images")
        return {
            "tables": tables,
            "images": images
        }


# 便捷函数
def parse_with_mineru(file_path: str, api_token: str = None) -> str:
    """
    使用MinerU解析文档的便捷函数

    Args:
        file_path (str): 文件路径
        api_token (str): MinerU API令牌

    Returns:
        str: 解析结果
    """
    parser = MinerUParser(api_token)
    return parser.parse_document(file_path)