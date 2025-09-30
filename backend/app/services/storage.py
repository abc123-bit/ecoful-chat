# 这个文件定义了一个MinIO存储类，用于与MinIO对象存储服务进行交互。
# 它提供了上传、下载、删除文件，检查文件是否存在，获取文件信息，生成预签名URL，列出文件等功能。
import io
import hashlib
from datetime import datetime, timedelta
from typing import Optional, BinaryIO, Tuple
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from minio import Minio
from minio.error import S3Error
from loguru import logger

from app.core.config import settings


class MinIOStorage:
    """MinIO对象存储服务"""

    def __init__(self):
        """初始化MinIO客户端"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.public_client = self.client
        self.bucket_name = settings.MINIO_BUCKET_NAME

        raw_public_endpoint = settings.MINIO_PUBLIC_ENDPOINT
        self.public_endpoint_scheme = None
        self.public_endpoint_host = None

        if raw_public_endpoint:
            endpoint_value = raw_public_endpoint
            if '://' not in endpoint_value:
                default_scheme = 'https' if settings.MINIO_SECURE else 'http'
                endpoint_value = f"{default_scheme}://{endpoint_value}"
            parsed = urlparse(endpoint_value)
            host = parsed.netloc or parsed.path
            if host:
                self.public_endpoint_host = host
                self.public_endpoint_scheme = parsed.scheme or ('https' if settings.MINIO_SECURE else 'http')

        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created successfully")
            else:
                logger.info(f"Bucket '{self.bucket_name}' already exists")
        except S3Error as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Tuple[str, str, int]:
        """
        上传文件到MinIO

        Args:
            file_data: 文件数据流
            object_name: 对象名称（路径）
            content_type: 文件MIME类型
            metadata: 文件元数据

        Returns:
            Tuple[object_key, file_hash, file_size]
        """
        try:
            # 读取文件数据并计算哈希
            file_content = file_data.read()
            file_size = len(file_content)
            file_hash = hashlib.md5(file_content).hexdigest()

            # 重置文件指针
            file_stream = io.BytesIO(file_content)

            # 准备元数据
            if metadata is None:
                metadata = {}

            metadata.update({
                "file-hash": file_hash,
                "upload-time": datetime.utcnow().isoformat(),
                "file-size": str(file_size)
            })

            # 上传文件
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type,
                metadata=metadata
            )

            logger.info(f"File uploaded successfully: {object_name}")
            return object_name, file_hash, file_size

        except S3Error as e:
            logger.error(f"Failed to upload file {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file {object_name}: {e}")
            raise

    def download_file(self, object_name: str) -> BinaryIO:
        """
        从MinIO下载文件

        Args:
            object_name: 对象名称

        Returns:
            文件数据流
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response

        except S3Error as e:
            logger.error(f"Failed to download file {object_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading file {object_name}: {e}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        删除文件

        Args:
            object_name: 对象名称

        Returns:
            是否删除成功
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file {object_name}: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: 对象名称

        Returns:
            文件是否存在
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence {object_name}: {e}")
            return False

    def get_file_info(self, object_name: str) -> Optional[dict]:
        """
        获取文件信息

        Args:
            object_name: 对象名称

        Returns:
            文件信息字典
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "object_name": object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        except S3Error as e:
            logger.error(f"Failed to get file info {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file info {object_name}: {e}")
            return None

    def generate_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        response_headers: Optional[dict] = None
    ) -> Optional[str]:
        """
        生成预签名URL

        Args:
            object_name: 对象名称
            expires: 过期时间

        Returns:
            预签名URL
        """
        try:
            client = self.client
            url = client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires,
                response_headers=response_headers
            )

            if self.public_endpoint_host:
                parsed_url = urlparse(url)
                scheme = self.public_endpoint_scheme or parsed_url.scheme
                new_url = urlunparse(parsed_url._replace(scheme=scheme, netloc=self.public_endpoint_host))
                return new_url

            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {object_name}: {e}")
            return None

    def list_files(self, prefix: str = "", recursive: bool = True) -> list:
        """
        列出文件

        Args:
            prefix: 文件前缀
            recursive: 是否递归

        Returns:
            文件列表
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files with prefix {prefix}: {e}")
            return []

    def generate_object_name(
        self,
        knowledge_base_id: int,
        filename: str,
        file_hash: str
    ) -> str:
        """
        生成对象名称

        Args:
            knowledge_base_id: 知识库ID
            filename: 文件名
            file_hash: 文件哈希

        Returns:
            对象名称
        """
        # 获取文件扩展名
        file_ext = Path(filename).suffix.lower()

        # 生成日期路径
        date_path = datetime.utcnow().strftime("%Y/%m/%d")

        # 生成对象名称: kb_{id}/{date}/{hash}{ext}
        object_name = f"kb_{knowledge_base_id}/{date_path}/{file_hash}{file_ext}"

        return object_name


# 创建全局存储实例
storage = MinIOStorage()