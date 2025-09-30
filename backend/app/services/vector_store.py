import json
import uuid
from typing import List, Dict, Optional, Tuple, Any, Union
from loguru import logger
from datetime import datetime

from app.core.config import settings

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, using mock implementation")

try:
    from app.services.bailian_client import bailian_client
    BAILIAN_AVAILABLE = True
except ImportError:
    BAILIAN_AVAILABLE = False
    logger.warning("Bailian client not available, using mock embeddings")

# 安全转换ID为字符串
def safe_convert_id(value: Any) -> Optional[str]:
    """安全转换ID为字符串"""
    if value is None:
        return None
    elif isinstance(value, (int, float, bool)):
        return str(value)
    elif isinstance(value, str):
        return value
    else:
        try:
            return str(value)
        except:
            return None

# 清理元数据值
def clean_metadata_value(value: Any) -> Union[str, int, float, bool, None]:
    """
    清理元数据值，确保符合 ChromaDB 要求
    
    Args:
        value: 原始值
        
    Returns:
        符合要求的元数据值
    """
    if value is None:
        return None
    elif isinstance(value, (int, float, bool)):
        return value
    elif isinstance(value, str):
        # 确保字符串不是空的
        return value if value.strip() else None
    elif isinstance(value, (list, dict)):
        # 将列表或字典转换为 JSON 字符串
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            try:
                return str(value)
            except:
                return None
    else:
        try:
            # 尝试转换为字符串
            return str(value)
        except:
            return None

# 清理元数据字典
def clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool, None]]:
    """
    清理元数据字典，确保所有值符合 ChromaDB 要求
    
    Args:
        metadata: 原始元数据字典
        
    Returns:
        清理后的元数据字典
    """
    cleaned = {}
    for key, value in metadata.items():
        # 特别处理 ID 字段
        if key.endswith('_id') or key == 'id':
            cleaned[key] = safe_convert_id(value)
        else:
            cleaned[key] = clean_metadata_value(value)
    
    # 移除所有None值
    cleaned = {k: v for k, v in cleaned.items() if v is not None}
    return cleaned

# 验证元数据字典
def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """
    验证元数据是否符合 ChromaDB 要求
    
    Args:
        metadata: 元数据字典
        
    Returns:
        是否有效
    """
    for key, value in metadata.items():
        if not isinstance(value, (str, int, float, bool)):
            logger.warning(f"Invalid metadata type: {key}={value} (type: {type(value)})")
            return False
    return True

# ChromaDB 向量存储实现
class ChromaVectorStore:
    """Chroma向量数据库服务"""

    def __init__(self):
        self.client = None
        self._connect()

    # 连接到Chroma数据库
    def _connect(self):
        """连接到Chroma数据库"""
        try:
            # 根据配置选择连接方式
            if settings.CHROMA_HOST and settings.CHROMA_PORT:
                # 远程连接
                self.client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT
                )
                logger.info(f"Connected to remote Chroma at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            else:
                # 本地持久化连接
                self.client = chromadb.PersistentClient(
                    path=settings.CHROMA_PERSIST_DIRECTORY,
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info(f"Connected to local Chroma at {settings.CHROMA_PERSIST_DIRECTORY}")

        except Exception as e:
            logger.error(f"Failed to connect to Chroma: {e}")
            raise
    
    # 获取或创建集合
    def get_or_create_collection(self, name: str, metadata: Optional[dict] = None):
        """
        兼容 Chroma v2 HTTP 在 embedding_function 上的怪异：先尝试官方 get_or_create，
        若命中 '_type' 等服务端解析错误，则走 “先查后建 + 显式 embedding_function=None”。
        """
        def _clean(d: dict) -> dict:
            out = {}
            for k, v in (d or {}).items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v
                else:
                    out[k] = str(v)
            return out

        base_meta = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "created_by": "kb_api",
            "purpose": "knowledge_base"
        }
        base_meta.update(_clean(metadata or {}))

        # 1) 先走常规（新版本组合一般OK）
        try:
            return self.client.get_or_create_collection(
                name=name,
                metadata=base_meta
                # 注意：这里不要传 embedding_function 参数，让它保持 None
            )
        except Exception as e:
            msg = str(e)
            # 2) 命中嵌入函数相关异常（'_type' / 'embedding_function'）
            if ("'_type'" in msg) or ("embedding_function" in msg.lower()):
                logger.warning(
                    f"get_or_create_collection hit EF bug for [{name}], "
                    f"fallback to get-then-create with embedding_function=None"
                )
                # 2.1 试试能不能直接拿（已存在）
                try:
                    return self.client.get_collection(name=name)
                except Exception:
                    pass
                # 2.2 显式创建，强制 embedding_function=None，避免发 {}
                return self.client.create_collection(
                    name=name,
                    metadata=base_meta,
                    embedding_function=None  # 关键：告诉服务端不负责算 embedding
                )
            # 3) 其他异常正常抛出
            logger.error(f"Failed to get_or_create_collection {name}: {e!r}")
            raise

    # 删除集合
    def delete_collection(self, name: str) -> bool:
        """删除集合（不存在也不报错）"""
        try:
            # chroma http client
            self.client.delete_collection(name)
            logger.info(f"Deleted Chroma collection: {name}")
            return True
        except Exception as e:
            # 某些实现会抛 NotFound，也统一吞掉
            logger.warning(f"Delete collection {name} got: {e} (ignored if not found)")
            return False
        
    # 获取或创建集合
    async def add_documents(
        self,
        collection_name: str,
        documents: List[Dict],
        batch_size: int = 100
    ) -> List[str]:
        """
        正确的分批入库流程：
        1) 先从 documents 中提取 batch_ids / batch_texts / batch_metadatas
        2) 再批量生成 embeddings
        3) 校验四个数组长度一致
        4) 最后只调用一次 collection.add(...)
        """
        collection = self.get_or_create_collection(
            collection_name,
            metadata={"purpose": "document_storage", "created_at": datetime.now().isoformat()}
        )

        all_ids: List[str] = []

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]

            batch_ids: List[str] = []
            batch_texts: List[str] = []
            batch_metadatas: List[Dict] = []

            # 1) 准备批次数据（清洗元数据  跳过空文本）
            for doc in batch_docs:
                doc_id = doc.get("id") or str(uuid.uuid4())
                text = (doc.get("content") or "").strip()
                if not text:
                    logger.warning(f"Skipping empty document text: id={doc_id}")
                    continue

                metadata = doc.get("metadata", {}) or {}
                cleaned_metadata = clean_metadata(metadata)
                if not validate_metadata(cleaned_metadata):
                    logger.error(f"Invalid metadata for document {doc_id}: {cleaned_metadata}")
                    cleaned_metadata = {
                        "validated": False,
                        "original_id": doc_id,
                        "created_at": datetime.now().isoformat()
                    }
                    if not validate_metadata(cleaned_metadata):
                        logger.error(f"Skipping document {doc_id} due to invalid fallback metadata")
                        continue

                batch_ids.append(doc_id)
                batch_texts.append(text)
                batch_metadatas.append(cleaned_metadata)

            if not batch_ids:
                logger.warning(f"No valid documents in batch {i // batch_size + 1}, skipping.")
                continue

            # 2) 生成 embeddings（分小批防止超时/限流）
            batch_embeddings: List[List[float]] = []
            sub_size = 10
            for j in range(0, len(batch_texts), sub_size):
                sub_texts = batch_texts[j:j + sub_size]
                try:
                    sub_embs = await bailian_client.create_embeddings(sub_texts)
                except Exception as e:
                    raise RuntimeError(f"Embedding sub-batch failed at {j // sub_size + 1}: {e}")
                if not sub_embs or len(sub_embs) != len(sub_texts):
                    raise RuntimeError(
                        f"Embeddings count mismatch: got={len(sub_embs) if sub_embs else 0}, "
                        f"expect={len(sub_texts)}"
                    )
                batch_embeddings.extend(sub_embs)

            # 3) 一致性校验
            if not (len(batch_ids) == len(batch_texts) == len(batch_metadatas) == len(batch_embeddings)):
                raise RuntimeError(
                    "Batch arrays length mismatch before collection.add: "
                    f"ids={len(batch_ids)}, docs={len(batch_texts)}, "
                    f"metas={len(batch_metadatas)}, embs={len(batch_embeddings)}"
                )

            # 4) 仅在准备完毕后调用一次 add（绝不传空列表）
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,
            )
            all_ids.extend(batch_ids)
            logger.info(f"Added batch {i // batch_size + 1}: {len(batch_ids)} documents")
        logger.info(f"Added {len(all_ids)} documents to collection {collection_name}")
        return all_ids


# 统一的向量存储管理器
class VectorStoreManager:
    """向量存储管理器"""

    ## 统一的检索接口
    async def search_knowledge_base(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        在指定集合中检索，返回 [{content, source_file, file_type, id, score, metadata, file_id, vector_id}, ...]
        """
        from app.services.bailian_client import bailian_client
        try:
            # 1) 拿到/创建集合（带非空 metadata）
            collection = self.vector_store.get_or_create_collection(
                collection_name,
                metadata={"purpose": "search"}
            )

            # 2) 生成查询向量
            emb = (await bailian_client.create_embeddings(query))[0]

            # 3) 查询（包含需要的字段，新增 ids）
            res = collection.query(
                query_embeddings=[emb],
                n_results=max(1, n_results),
                include=["documents", "metadatas", "distances"]  
            )

            ids = (res.get("ids") or [[]])[0]
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]

            out = []
            for i, content in enumerate(docs):
                md = metas[i] or {}
                vid = ids[i] if i < len(ids) else None

                # 距离 -> 简易得分（越小越好）
                score = None
                try:
                    d = float(dists[i])
                    score = 1.0 / (1.0 + d)
                except Exception:
                    pass

                out.append({
                    "content": content,
                    "source_file": md.get("source_file") or md.get("file_name"),
                    "file_type": md.get("file_type"),
                    "id": md.get("chunk_id") or md.get("id"),
                    "score": score,
                    "metadata": md,
                    "file_id": md.get("file_id"),
                    "vector_id": md.get("vector_id")  # 用 metadata 回传 vector_id
                })
            return out
        except Exception as e:
            logger.error(f"search_knowledge_base error on collection={collection_name}: {e}")
            return []


    ## 创建知识库集合，不需要异步处理
    async def create_knowledge_base_collection(
        self,
        collection_name: str,
        name: str,
        description: Optional[str] = ""
    ) -> bool:
        meta = {
            "kb_name": name,
            "description": description or "",
            "created_at": datetime.now().isoformat()
        }
        # 直接确保集合存在（幂等）
        self.vector_store.get_or_create_collection(collection_name, metadata=meta)
        logger.info(f"Ensured Chroma collection exists: {collection_name}")
        return True

    ## 删除知识库，不需要异步处理
    def delete_knowledge_base_collection(self, collection_name: str) -> bool:
        ok = self.vector_store.delete_collection(collection_name)
        logger.info(f"Deleted Chroma collection (if exists): {collection_name}")
        return ok

    def __init__(self):
        self.vector_store = ChromaVectorStore()

    async def add_document_chunks(
        self,
        collection_name: str,
        chunks: List[Dict],
        batch_size: int = 64   # <== 新增批量参数，默认64，可按需调优
    ) -> List[str]:
        """
        添加文档块到向量库（全量批处理 + 1:1 对齐返回）
        """

        # 1) 预构建 documents
        documents: List[Dict] = []
        for idx, chunk in enumerate(chunks):
            # —— 原有逻辑：构造元数据 ——
            raw_meta = chunk.get("metadata") or {}

            chunk_id = safe_convert_id(chunk.get("id"))
            file_id = safe_convert_id(chunk.get("file_id"))
            knowledge_base_id = safe_convert_id(chunk.get("knowledge_base_id"))

            doc_metadata = {
                "chunk_id": chunk_id,
                "file_id": file_id,
                "knowledge_base_id": knowledge_base_id,
                # 注意：尽量把 chunk_index 放进 metadata，后续召回时可定位
                "chunk_index": chunk.get("chunk_index", raw_meta.get("chunk_index", idx)),
                "source_file": raw_meta.get("source_file"),
                "file_type": raw_meta.get("file_type"),
                "content_type": raw_meta.get("content_type"),
                "keywords": raw_meta.get("keywords", ""),
                "page_number": raw_meta.get("page_number"),
                "section_title": raw_meta.get("section_title"),
                "created_at": datetime.now().isoformat()
            }

            # 附加未覆盖的元数据字段
            for k, v in raw_meta.items():
                if k not in doc_metadata:
                    doc_metadata[k] = v

            # —— 在 metadata 里写入 vector_id（= 我们即将作为 Chroma 文档 id 传入的值） ——
            doc_id = str(uuid.uuid4())
            doc_metadata["vector_id"] = doc_id

            # —— 兜底：Chroma 禁止空 metadata，这里双保险 ——
            if not doc_metadata:
                doc_metadata = {
                    "default_metadata": "true",
                    "created_at": datetime.now().isoformat()
                }

            cleaned_metadata = clean_metadata(doc_metadata)

            # 限制 content 长度，防止超长
            SAFE_MAX_CHARS = 6000

            def _clip(txt: str, max_chars: int = SAFE_MAX_CHARS) -> str:
                if not txt:
                    return ""
                return txt if len(txt) <= max_chars else txt[:max_chars]

            documents.append({
                "id": doc_id,                              # 用上面生成的 doc_id
                "content": _clip(chunk.get("content", "") or ""),
                "metadata": cleaned_metadata
            })

        # 2) 批量写入：保证“全量输入 -> 全量ID输出”
        all_ids: List[str] = []
        for start in range(0, len(documents), batch_size):
            batch = documents[start:start + batch_size]
            # 这里沿用你现有的底层实现；务必确保它对一个 batch 返回等长的 id 列表
            ids = await self.vector_store.add_documents(collection_name, batch)
            if not ids or len(ids) != len(batch):
                raise RuntimeError(
                    f"Vector store returned invalid ids: got {0 if not ids else len(ids)} vs expected {len(batch)}"
                )
            all_ids.extend(ids)

        # 最终返回列表长度必须与输入 chunks 相等
        if len(all_ids) != len(chunks):
            raise RuntimeError(
                f"Vectorization size mismatch: ids={len(all_ids)} vs chunks={len(chunks)}"
            )

        return all_ids


# 根据可用性选择向量存储实现
if CHROMADB_AVAILABLE:
    # 使用真实的ChromaDB实现
    vector_store_manager = VectorStoreManager()
    logger.info("Using ChromaDB vector store")
else:
    # 使用模拟实现
    from app.services.vector_store_mock import MockVectorStoreManager
    vector_store_manager = MockVectorStoreManager()
    logger.info("Using Mock vector store (ChromaDB not available)")