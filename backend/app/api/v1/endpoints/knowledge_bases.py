# backend/app/api/v1/endpoints/knowledge_bases.py
# 知识库相关接口
import os
import asyncio
import aiofiles
import inspect 
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from datetime import datetime, timedelta
from minio import Minio 

from app.db.database import get_async_session, get_db, AsyncSessionLocal
from app.models.knowledge_base import KnowledgeBase
from app.models.file import File as FileModel
from app.models.document_chunk import DocumentChunk
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    FileUploadResponse
)
from app.services.vector_store import vector_store_manager
from app.services.storage import storage
from app.services.file_processor import file_processor
from app.services.text_splitter import create_document_chunks
from app.services.bailian_client import bailian_client
import uuid
import hashlib
import io
import mimetypes
from pathlib import Path

from app.core.config import settings

router = APIRouter()

# 获取知识库列表
@router.get("/", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取知识库列表"""
    try:
        result = await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.status == "active")
            .offset(skip)
            .limit(limit)
            .order_by(KnowledgeBase.created_at.desc())
        )
        knowledge_bases = result.scalars().all()
        return knowledge_bases
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge bases")

# 创建知识库
@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新知识库"""
    try:
        # 生成集合名称
        collection_name = f"kb_{uuid.uuid4().hex[:8]}"

        # 创建数据库记录
        kb = KnowledgeBase(
            name=kb_data.name,
            description=kb_data.description,
            collection_name=collection_name,
            chunk_size=kb_data.chunk_size,
            chunk_overlap=kb_data.chunk_overlap,
            embedding_model=settings.BAILIAN_EMBEDDING_MODEL
        )

        db.add(kb)
        await db.commit()
        await db.refresh(kb)

        # 创建向量集合 —— 兼容 Mock / 真实实现（同步或异步）
        func = vector_store_manager.create_knowledge_base_collection

        # 先按“能接受的关键字”去调用（根据签名过滤），不行再回退到位置参数
        try:
            sig = inspect.signature(func)
            # 可供传入的候选参数
            cand_kwargs = {
                "collection_name": kb.collection_name,
                "name": kb.name,
                "description": kb.description,
                # 你的 KB 模型里如果有 embedding_model，这里也给一份（没有就不会传）
                "embedding_model": getattr(kb, "embedding_model", None),
            }
            # 丢掉 None 和不在函数签名里的键
            kw = {k: v for k, v in cand_kwargs.items() if v is not None and k in sig.parameters}

            # 优先用“过滤后的关键字”调用；若函数不支持任意关键字（Mock 常见），会抛 TypeError
            res = func(**kw) if kw else func(kb.collection_name)
        except TypeError:
            # 回退 1：只传集合名（最常见的 Mock 形式）
            try:
                res = func(kb.collection_name)
            except TypeError:
                # 回退 2：传集合名 + 名称（部分实现可能是 (collection_name, name)）
                try:
                    res = func(kb.collection_name, kb.name)
                except TypeError:
                    # 回退 3：传集合名 + embedding_model（有的实现是 (collection_name, embedding_model)）
                    emb = getattr(kb, "embedding_model", None)
                    if emb is not None:
                        res = func(kb.collection_name, emb)
                    else:
                        # 到这里还不行，直接把异常抛出去
                        raise

        # 兼容同步/异步返回
        if inspect.isawaitable(res):
            await res


        logger.info(f"Created knowledge base: {kb.name} (ID: {kb.id})")
        return kb

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge base")

# 获取知识库详情
@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取知识库详情"""
    try:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        return kb

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get knowledge base")

# 更新知识库
@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: int,
    kb_data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新知识库"""
    try:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # 更新字段
        for field, value in kb_data.dict(exclude_unset=True).items():
            setattr(kb, field, value)

        await db.commit()
        await db.refresh(kb)

        logger.info(f"Updated knowledge base: {kb.name} (ID: {kb.id})")
        return kb

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge base")

# 删除知识库
@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_async_session)  # 确保这里是 AsyncSession
):
    try:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # ← 先把要用的信息拷贝出来
        kb_name = kb.name
        kb_id_val = kb.id
        collection_name = kb.collection_name

        # 先删向量集合（同步方法，别 await）
        vector_store_manager.delete_knowledge_base_collection(collection_name)

        # 标记删除并提交
        kb.status = "deleted"
        await db.commit()

        # 提交后只用局部变量，避免触发 ORM 过期刷新
        logger.info(f"Deleted knowledge base: {kb_name} (ID: {kb_id_val})")
        return {"message": "Knowledge base deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge base")


# 后台任务处理上传的文件
def process_uploaded_file(file_id: int, kb_id: int):
    """后台处理上传的文件 - 使用同步会话修复greenlet问题"""
    from app.db.database import SessionLocal
    import asyncio
    import json
    from sqlalchemy import select
    from app.models.file import File as FileModel
    from app.models.knowledge_base import KnowledgeBase
    from app.models.document_chunk import DocumentChunk
    from app.services.vector_store import vector_store_manager
    from app.services.storage import storage
    from app.services.file_processor import file_processor
    from app.services.text_splitter import create_document_chunks
    from datetime import datetime

    # === 新增：把过短的相邻切片自动合并，避免被过滤丢失 ===
    def _coalesce_short_chunks(chunks, 
                            min_chars: int = 200, 
                            min_words: int = 15,
                            max_chars: int = 6000,    # 新增：上限（留余量 < 8192 token）
                            max_words: int = 4000):   # 宽松上限
        """
        将过短的相邻切片合并，直到达到下限；同时不超过上限（超过则先 flush）。
        """
        merged = []
        buf_text = []
        buf_meta = None
        start_idx = None
        acc_chars = 0
        acc_words = 0

        def _flush(end_idx):
            nonlocal buf_text, buf_meta, start_idx, acc_chars, acc_words
            if not buf_text:
                return
            content = "\n".join(buf_text).strip()
            meta = dict(buf_meta or {})
            meta.setdefault("chunk_index", start_idx if start_idx is not None else 0)
            meta.setdefault("chunk_size", 0)
            meta.setdefault("chunk_overlap", 0)
            meta["chunk_index_range"] = [start_idx, end_idx]
            meta["coalesced"] = True
            merged.append({"content": content, "metadata": meta})
            buf_text = []
            buf_meta = None
            start_idx = None
            acc_chars = 0
            acc_words = 0

        def est_words(txt: str) -> int:
            # 简易估算，中文按字符/2，英文按空格切分
            if not txt:
                return 0
            if " " in txt:
                return max(len(txt.split()), 1)
            return max(len(txt) // 2, 1)

        for i, ch in enumerate(chunks):
            text = (ch.get("content") or "").strip()
            meta = ch.get("metadata") or {}
            words = meta.get("word_count")
            if words is None:
                words = est_words(text)

            if not buf_text:
                buf_text = [text]
                buf_meta = meta
                start_idx = ch.get("chunk_index", i)
                acc_chars = len(text)
                acc_words = words
                # 如果单块就超过 max，上面 split_overlong_chunks 会管
                continue

            # 如果再加当前块会超上限，先 flush
            if acc_chars + len(text) > max_chars or acc_words + words > max_words:
                _flush(i - 1)
                # 重新开始缓冲
                buf_text = [text]
                buf_meta = meta
                start_idx = ch.get("chunk_index", i)
                acc_chars = len(text)
                acc_words = words
                continue

            # 否则累加
            buf_text.append(text)
            acc_chars += len(text)
            acc_words += words

            # 如果已达到下限，先 flush（避免无限增长）
            if acc_chars >= min_chars and acc_words >= min_words:
                _flush(i)

        _flush(len(chunks) - 1)
        return merged


    def split_overlong_chunks(chunks, max_chars: int = 6000):
        """
        二次切分：仍超过上限的切片继续按 max_chars 切开；元数据带 part_index。
        """
        result = []
        for ch in chunks:
            txt = ch.get("content") or ""
            meta = dict(ch.get("metadata") or {})
            if len(txt) <= max_chars:
                result.append({"content": txt, "metadata": meta})
                continue
            # 切片
            part = 0
            for start in range(0, len(txt), max_chars):
                sub = txt[start:start + max_chars]
                m = dict(meta)
                m["part_index"] = part
                m.setdefault("chunk_index", meta.get("chunk_index", 0))
                m["split_from_overlong"] = True
                result.append({"content": sub, "metadata": m})
                part += 1
        return result


    session = SessionLocal()
    try:
        # 1) 取文件记录
        file_record = session.execute(
            select(FileModel).where(FileModel.id == file_id)
        ).scalar_one_or_none()

        if not file_record:
            logger.error(f"File record {file_id} not found")
            return

        # 2) 标记处理中
        file_record.processing_status = "processing"
        session.commit()

        # 3) 下载 & 解析
        raw_stream = storage.download_file(file_record.object_key)
        seekable_stream = io.BytesIO(raw_stream.read())

        extracted_text, file_metadata = file_processor.process_file(
            seekable_stream,
            file_record.filename,
            file_record.mime_type
        )

        # 4) 切块（保持你现有参数）
        chunks = create_document_chunks(
            text=extracted_text,
            file_metadata=file_metadata,
            chunk_size=file_record.knowledge_base.chunk_size or 1000,
            chunk_overlap=file_record.knowledge_base.chunk_overlap or 200
        )

        # 5) 合并短块 + 上限控制
        merged_chunks = _coalesce_short_chunks(
            chunks, 
            min_chars=200, min_words=15, 
            max_chars=6000, max_words=4000
        )

        # 二次切分，确保没有超过上限的块
        safe_chunks = split_overlong_chunks(merged_chunks, max_chars=6000)
        

        # 6) 构建向量库 payload（兜底 metadata，保留原有键位）
        chunks_for_vector_store = []
        for i, ch in enumerate(safe_chunks):
            content = (ch.get("content") or "").strip()
            chunk_meta = ch.get("metadata") or {}

            # 不再做“len<20 / word_count<3 丢弃”；既然合并过，这里直接入库
            if not chunk_meta:
                chunk_meta = {
                    "source_file": file_record.filename,
                    "file_type": file_record.file_type,
                    "chunk_index": ch.get("chunk_index", i),
                    "default_metadata": "true"
                }
            else:
                # 兜底必需字段
                chunk_meta.setdefault("source_file", file_record.filename)
                chunk_meta.setdefault("file_type", file_record.file_type)
                chunk_meta.setdefault("chunk_index", ch.get("chunk_index", i))

            # 入库时把 file_id 放进向量 metadata
            chunks_for_vector_store.append({
                "content": content,
                "metadata": chunk_meta,
                "file_id": file_record.id,
                "knowledge_base_id": kb_id
            })

        # 7) 如果空内容，标记完成并返回
        if not chunks_for_vector_store:
            file_record.processing_status = "completed"
            file_record.vectorization_status = "completed"
            file_record.vectorization_error = None
            try:
                file_record.vectorized_at = datetime.now()
            except Exception:
                pass
            file_record.extracted_text = extracted_text
            file_record.extracted_metadata = file_metadata   # 注意：存“文件级”元数据
            file_record.chunk_count = 0
            session.commit()
            logger.info(f"File {file_record.filename} has no processable text, marked as completed.")
            return

        # 8) 异步提交向量库（add_document_chunks 现已支持全量批处理）
        async def _add_chunks_async():
            kb_result = session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            ).scalar_one()
            return await vector_store_manager.add_document_chunks(
                collection_name=kb_result.collection_name,
                chunks=chunks_for_vector_store
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            vector_ids = loop.run_until_complete(_add_chunks_async())
        finally:
            loop.close()

        # 9) 写回 DB（严格 1:1）
        if vector_ids and len(vector_ids) == len(chunks_for_vector_store):
            document_chunks_to_add = []
            for vid, ch in zip(vector_ids, chunks_for_vector_store):
                meta = ch.get("metadata") or {}
                document_chunk = DocumentChunk(
                    knowledge_base_id=kb_id,
                    file_id=file_id,
                    content=ch["content"],
                    content_length=len(ch["content"]),
                    chunk_index=meta.get("chunk_index", 0),
                    chunk_size=meta.get("chunk_size", 0),
                    chunk_overlap=meta.get("chunk_overlap", 0),
                    chunk_metadata=meta,
                    vector_id=vid,
                    vectorized_at=datetime.now()
                )
                document_chunks_to_add.append(document_chunk)

            session.add_all(document_chunks_to_add)

            # 10) 更新统计 & 文件记录
            file_record.processing_status = "completed"
            file_record.vectorization_status = "completed"       # <== 可选：补上向量化状态
            file_record.vectorization_error = None
            file_record.extracted_text = extracted_text
            file_record.extracted_metadata = file_metadata        # <== 修复：不再被 chunk 覆盖
            file_record.chunk_count = len(chunks_for_vector_store)

            kb = session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            ).scalar_one()
            kb.document_count += len(chunks_for_vector_store)

            session.commit()
            logger.info(f"Successfully processed and vectorized file {file_record.filename} (chunks={len(chunks_for_vector_store)})")
        else:
            raise Exception(
                f"Vectorization failed: ids={len(vector_ids) if vector_ids else 0} "
                f"!= chunks={len(chunks_for_vector_store)}"
            )
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        # 失败路径尽量写全，避免 None 属性异常
        try:
            file_record.processing_status = "failed"
            file_record.processing_error = str(e)[:500]
            file_record.vectorization_status = "failed"
            file_record.vectorization_error = str(e)[:500]
            session.commit()
        except Exception:
            pass
    finally:
        session.close()


# 上传文件路由
@router.post("/{kb_id}/files", response_model=FileUploadResponse)
async def upload_file(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传文件到知识库"""
    try:
        # 检查知识库是否存在
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        file_hash = hashlib.md5(file_content).hexdigest()

        if file_size > settings.MAX_FILE_SIZE:
            logger.warning(f'File too large: size={file_size} bytes, name={file.filename}')
            raise HTTPException(status_code=400, detail='文件大小超过限制')

        guessed_type, _ = mimetypes.guess_type(file.filename)
        content_type = file.content_type or guessed_type or ''
        extension = Path(file.filename).suffix.lower()

        if content_type not in settings.ALLOWED_FILE_TYPES:
            fallback_mime_map = {
                '.md': 'text/markdown',
                '.markdown': 'text/markdown',
                '.txt': 'text/plain',
                '.csv': 'text/plain'
            }
            fallback_type = fallback_mime_map.get(extension)
            if fallback_type:
                content_type = fallback_type

        if content_type not in settings.ALLOWED_FILE_TYPES:
            logger.warning(f"Unsupported MIME type: {content_type} for file {file.filename}")
            raise HTTPException(status_code=400, detail='不支持的文件类型')

        processor = file_processor.get_processor(extension.lstrip('.'), content_type)
        if processor is None:
            logger.warning(f"No processor available for file {file.filename} ({content_type})")
            raise HTTPException(status_code=400, detail='暂不支持该文件类型解析')

        # 生成存储路径
        object_key = storage.generate_object_name(
            knowledge_base_id=kb_id,
            filename=file.filename,
            file_hash=file_hash
        )

        # 上传到MinIO
        file_stream = io.BytesIO(file_content)
        storage.upload_file(
            file_data=file_stream,
            object_name=object_key,
            content_type=content_type
        )

        # 创建文件记录
        file_record = FileModel(
            knowledge_base_id=kb_id,
            filename=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            mime_type=content_type,
            file_size=file_size,
            file_hash=file_hash,
            storage_path=f"minio://{storage.bucket_name}/{object_key}",
            bucket_name=storage.bucket_name,
            object_key=object_key,
            processing_status="pending",
            vectorization_status="pending"
        )

        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        await db.refresh(kb) # <--- 添加这一行来“唤醒”kb对象

        # 在所有数据库写操作之前准备好响应对象
        # 此时 file_record 实例是活跃的，访问属性不会触发数据库IO
        response = FileUploadResponse(
            id=file_record.id,
            filename=file_record.filename,
            file_size=file_record.file_size,
            file_type=file_record.file_type,
            processing_status=file_record.processing_status,
            created_at=file_record.created_at
        )
        # ====================================================

        # 添加后台任务处理文件
        background_tasks.add_task(
            process_uploaded_file,
            file_record.id,
            kb_id
        )

        # 更新知识库文件计数
        # 注意：这里的重新查询不是必须的，可以直接使用kb对象
        kb.file_count += 1
        await db.commit()

        logger.info(f"Uploaded file {file.filename} to knowledge base {kb_id}")
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        # 记录错误时不直接包含异常对象，避免触发数据库查询
        logger.error(f"上传出现错误： {kb_id}: {type(e).__name__}: {str(e)[:200]}")
        raise HTTPException(status_code=500, detail="文件上传失败")


# 获取知识库文件列表
@router.get("/{kb_id}/files")
async def list_files(
    kb_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取知识库文件列表"""
    try:
        result = await db.execute(
            select(FileModel)
            .where(FileModel.knowledge_base_id == kb_id)
            .order_by(FileModel.created_at.desc())
        )
        files = result.scalars().all()
        return files

    except Exception as e:
        logger.error(f"Error listing files for knowledge base {kb_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")
    

# 重刷文件向量化
@router.post("/{kb_id}/reindex")
async def reindex_kb(
    kb_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select, or_
    result = await db.execute(
        select(FileModel).where(
            FileModel.knowledge_base_id == kb_id,
            or_(FileModel.vectorization_status == "pending",
                FileModel.vectorization_status == "failed"),
            FileModel.processing_status == "completed"
        )
    )
    files = result.scalars().all()
    for f in files:
        background_tasks.add_task(process_uploaded_file, f.id, kb_id)
    return {"reindexed": len(files)}


# 创建 MinIO 客户端
def get_minio_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    if not (access_key and secret_key):
        print("MINIO_ACCESS_KEY / MINIO_SECRET_KEY 未配置")
        raise RuntimeError("MINIO_ACCESS_KEY / MINIO_SECRET_KEY 未配置")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

# 生成文件下载预签名 URL
@router.get("/{kb_id}/files/{file_id}/sign")
async def sign_file_download(kb_id: int, file_id: int, session: AsyncSession = Depends(get_async_session)):
    # 1) 校验归属
    stmt = select(FileModel).where(FileModel.id == file_id, FileModel.knowledge_base_id == kb_id)
    res = await session.execute(stmt)
    file = res.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在或不属于该知识库")

    if not file.bucket_name or not file.object_key:
        raise HTTPException(status_code=400, detail="文件缺少 bucket/object_key")

    # 2) 生成预签名 URL
    try:
        mc = get_minio_client()
        expires = timedelta(hours=2)
        url = mc.presigned_get_object(file.bucket_name, file.object_key, expires=expires)
        return {
            "url": url,
            "filename": file.filename,
            "bucket": file.bucket_name,
            "object_key": file.object_key,
            "expires_in": int(expires.total_seconds())
        }
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"生成签名链接失败: {e}")

