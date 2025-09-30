from datetime import datetime, timedelta, timezone
from minio import Minio

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import json
import uuid
from urllib.parse import quote

from app.db.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.schemas.knowledge_base import ChatRequest, ChatResponse
from app.services.vector_store import vector_store_manager
from app.services.bailian_client import rag_service
from app.services.storage import storage
from app.models.file import File
from app.models.document_chunk import DocumentChunk

router = APIRouter()


# === 内部工具：根据检索到的 chunks 收集唯一文件源 ===============================
async def _collect_source_files(session: AsyncSession, retrieved_chunks: list):
    """根据检索到的 chunks 收集唯一文件源，返回 [{'file_id':1,'filename':'a.docx'}, ...]"""
    file_ids = set()
    # 1) 优先直接从 chunk 结构拿 file_id
    for ch in retrieved_chunks or []:
        fid = None
        try:
            # ch 可能是 dict / pydantic；根据结构取值
            fid = ch.get("file_id")
            if not fid and isinstance(ch.get("chunk_record"), dict):
                fid = ch["chunk_record"].get("file_id")
        except Exception:
            pass

        if not fid:
            # 兜底：用 vector_id 反查 document_chunks 拿 file_id
            vid = ch.get("vector_id")
            if vid:
                stmt = select(DocumentChunk.file_id).where(DocumentChunk.vector_id == vid)
                res = await session.execute(stmt)
                fid = res.scalar_one_or_none()

        if fid:
            file_ids.add(int(fid))

    if not file_ids:
        return []

    # 2) 一次性查文件表
    stmt = select(File.id, File.filename).where(File.id.in_(file_ids))
    res = await session.execute(stmt)
    rows = res.all()
    return [{"file_id": r[0], "filename": r[1]} for r in rows]

# === 仅在本文件内使用：基于 get_db() 的一次性 AsyncSession 上下文 ===
class _DBSessionCtx:
    def __init__(self):
        self._agen = None
        self.db: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self._agen = get_db()                # get_db 是 async generator
        self.db = await self._agen.__anext__()  # 取到 yield 的 AsyncSession
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.db:
                await self.db.close()
        finally:
            if self._agen:
                await self._agen.aclose()

# === MinIO 客户端（与 knowledge_bases.py 保持一致） 
# 不要直接 raise，返回 None 让上层判断
def _get_minio_client():
    try:
        client = getattr(storage, "public_client", None) or getattr(storage, "client", None)
    except Exception as exc:
        logger.warning(f"Failed to obtain MinIO client: {exc}")
        return None
    return client



# === 知识库问答（支持流式） 
@router.post("/ask")
async def ask_question(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """知识库问答"""
    try:
        # 1) 检查知识库是否存在
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == chat_request.knowledge_base_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # 2) 检索相关文档
        search_results = list(await vector_store_manager.search_knowledge_base(
            collection_name=kb.collection_name,
            query=chat_request.question,
            n_results=chat_request.max_chunks
        ))

        # 3) 获取或创建对话（用 session_id 作为外显 ID）
        conversation_id = chat_request.conversation_id or str(uuid.uuid4())
        conversation = None

        if chat_request.conversation_id:
            conv_result = await db.execute(
                select(ChatConversation).where(
                    ChatConversation.session_id == chat_request.conversation_id
                )
            )
            conversation = conv_result.scalar_one_or_none()

        if not conversation:
            conversation = ChatConversation(
                knowledge_base_id=kb.id,
                session_id=conversation_id,
                title=chat_request.question[:50] + "..." if len(chat_request.question) > 50 else chat_request.question
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)  # 确保 id / session_id 已加载
        
        # ✅ 在任何后续 commit 之前，先把会用到的“纯值”取出来，避免触发过期属性访问
        conv_id_val = int(conversation.id)
        conv_sid_val = str(conversation.session_id)

        # 4) 保存用户消息（先写入，后续再保存助手消息）
        user_message = ChatMessage(
            conversation_id=conv_id_val,
            role="user",
            content=chat_request.question
        )
        db.add(user_message)

        # ✅ 关键：立刻把用户消息落库，避免浏览器刷新丢失
        conversation.message_count = (conversation.message_count or 0) + 1
        conversation.last_message_at = datetime.now(timezone.utc)
        
        # conversation 进入 expired 状态（默认 expire_on_commit=True）
        await db.commit()


        # 5) 返回流式 or 同步
        if chat_request.stream:
            # 直接用前面缓存的纯值；不要再读 conversation.xxx
            # conv_id_val = int(conversation.id)
            # conv_sid_val = str(conversation.session_id)

            return StreamingResponse(
                stream_chat_response(
                    search_results=search_results,
                    question=chat_request.question,
                    conversation_id=conv_id_val,
                    conversation_session_id=conv_sid_val
        ),
                media_type="text/event-stream"
            )

        # —— 非流式路径 ——
        response = await rag_service.generate_answer(
            question=chat_request.question,
            context_chunks=search_results,
            stream=False
        )

        # 汇总用于 UI 的来源（含 file_id / filename）
        ui_sources = await _collect_source_files(db, search_results)

        # 保存助手消息（usage 放到 message_metadata，模型里并没有 usage 字段）
        assistant_message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response["answer"],
            retrieved_chunks=search_results,
            source_files=ui_sources,
            message_metadata={"usage": response.get("usage")}  # ← 仅存到元数据中
        )
        db.add(assistant_message)

        # 兼容：如果未来加了 source_files_detail 列，这里再赋值；当前没有则忽略
        try:
            assistant_message.source_files_detail = ui_sources  # type: ignore[attr-defined]
        except Exception:
            pass

        # 更新会话统计
        conversation.message_count = (conversation.message_count or 0) + 1
        conversation.last_message_at = datetime.now(timezone.utc)

        await db.commit()

        # 返回结果：保持原有 response["sources"] 形态，避免 Pydantic 校验风险；
        # 同时提供 sources_file_detail 给前端做“可溯源预览”。
        return ChatResponse(
            answer=response["answer"],
            sources=response.get("sources", []),      # 可能是字符串列表（模型返回）
            conversation_id=conversation_id,
            message_id=str(assistant_message.id),
            usage=response.get("usage"),
            retrieved_chunks=search_results,
            sources_file_detail=ui_sources            # ← 含 file_id/filename 的列表
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to process question")


# === 流式回答生成器（SSE） =====================================================
async def stream_chat_response(
    search_results,
    question: str,
    conversation_id: int,
    conversation_session_id: str,
) -> AsyncGenerator[str, None]:
    """流式聊天响应（不依赖上游的 ORM 会话；在内部自行开/关 AsyncSession）"""
    try:
        full_response = ""

        # 发送开始信号（只用传入的纯值，不访问 ORM 属性以避免 refresh）
        yield f"data: {json.dumps({'type':'start','conversation_id': conversation_session_id})}\n\n"

        # 获取流式响应
        response_stream = await rag_service.generate_answer(
            question=question,
            context_chunks=search_results,
            stream=True
        )

        async for chunk in response_stream:
            if chunk.get("content"):
                full_response += chunk["content"]
                yield f"data: {json.dumps({'type':'content','content': chunk['content']})}\n\n"

            if chunk.get("finished"):
                async with _DBSessionCtx() as db:
                    ui_sources = await _collect_source_files(db, search_results)

                    assistant_message = ChatMessage(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=full_response,
                        retrieved_chunks=search_results,
                        source_files=ui_sources,
                    )
                    try:
                        assistant_message.source_files_detail = ui_sources  # type: ignore[attr-defined]
                    except Exception:
                        pass

                    db.add(assistant_message)

                    # 更新会话统计（这里再 +1：用户消息已在路由里先提交了 +1）
                    result = await db.execute(
                        select(ChatConversation).where(ChatConversation.id == conversation_id)
                    )
                    conv = result.scalar_one()
                    conv.message_count = (conv.message_count or 0) + 1
                    conv.last_message_at = datetime.now(timezone.utc)

                    await db.commit()
                

                # 结束事件：带上 sources 和 answer
                end_payload = {
                    'type': 'end',
                    'sources': ui_sources,
                    'answer': full_response,
                    'sources_file_detail': ui_sources
                }
                yield f"data: {json.dumps(end_payload)}\n\n"
                break

    except Exception as e:
        logger.error(f"Error in stream response: {e}")
        yield f"data: {json.dumps({'type':'error','message': str(e)})}\n\n"

# === 对话列表 =====
@router.get("/conversations/{kb_id}")
async def get_conversations(
    kb_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取知识库的对话列表"""
    try:
        result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.knowledge_base_id == kb_id)
            .where(ChatConversation.is_active == True)
            .order_by(ChatConversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        return conversations

    except Exception as e:
        logger.error(f"Error getting conversations for kb {kb_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")


# === 对话消息（注意：这里的 path 参数是 session_id 语义） ====================
@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取对话消息：这里的 conversation_id 指 session_id"""
    try:
        conv_result = await db.execute(
            select(ChatConversation).where(
                ChatConversation.session_id == conversation_id
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msg_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = msg_result.scalars().all()
        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get messages")


# === 文件直开/预览 
def _get_first_attr(obj, names: list):
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v:
                return v
    return None


@router.get("/files/{file_id}/open-url")
async def get_file_open_url(file_id: int, db: AsyncSession = Depends(get_db), request: Request = None):
    res = await db.execute(select(File).where(File.id == file_id))
    file = res.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if getattr(file, "bucket_name", None) and getattr(file, "object_key", None):
        from datetime import timedelta
        from urllib.parse import quote

        inline_name = quote(getattr(file, "filename", ""), safe="")
        presigned = storage.generate_presigned_url(
            object_name=file.object_key,
            expires=timedelta(hours=2),
            response_headers={"response-content-disposition": f'inline; filename="{inline_name}"'}
        )

        if presigned:
            return {"url": presigned, "filename": getattr(file, "filename", None)}

        raise HTTPException(status_code=503, detail="对象存储未配置，无法预览该文件")

    direct_url = getattr(file, "url", None) or getattr(file, "storage_url", None)
    if direct_url:
        return {"url": direct_url, "filename": getattr(file, "filename", None)}

    raw_path = f"/api/v1/chat/files/{file_id}/raw"
    base = (str(request.base_url).rstrip("/") if request else "")
    abs_url = f"{base}{raw_path}"
    return {"url": abs_url, "filename": getattr(file, "filename", None)}

@router.get("/files/{file_id}/raw")
async def get_file_raw(file_id: int, db: AsyncSession = Depends(get_db)):
    """
    把文件内容直接给浏览器：
    - 如果是 MinIO 存储：生成“强制 inline”的预签名 URL 并 307 重定向过去
    - 如果记录里有直链：直接 307 重定向
    - 否则再尝试本地/共享盘路径读取并 inline 返回
    """
    res = await db.execute(select(File).where(File.id == file_id))
    file = res.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # 1) MinIO：直接重定向到“强制 inline”的预签名 URL
    if getattr(file, "bucket_name", None) and getattr(file, "object_key", None):
        from datetime import timedelta
        from urllib.parse import quote

        inline_name = quote(getattr(file, "filename", ""), safe="")
        presigned = storage.generate_presigned_url(
            object_name=file.object_key,
            expires=timedelta(hours=2),
            response_headers={"response-content-disposition": f'inline; filename="{inline_name}"'}
        )
        if presigned:
            return RedirectResponse(presigned, status_code=307)

    # 2) 直链
    direct_url = _get_first_attr(file, ["url", "storage_url"])
    if direct_url:
        return RedirectResponse(direct_url, status_code=307)

    # 3) 本地/共享盘路径兜底
    import mimetypes, os
    try:
        import aiofiles  # 按需引入
    except ImportError:
        aiofiles = None

    file_path = _get_first_attr(file, ["path", "file_path", "storage_path"])
    if not file_path:
        raise HTTPException(status_code=404, detail="File has no accessible path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File path not found on server")

    mime, _ = mimetypes.guess_type(file_path)
    mime = mime or "application/octet-stream"

    if aiofiles:
        async def _iterfile():
            async with aiofiles.open(file_path, "rb") as f:
                chunk = await f.read(1024 * 1024)
                while chunk:
                    yield chunk
                    chunk = await f.read(1024 * 1024)
        return StreamingResponse(
            _iterfile(),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{getattr(file, "filename", "file")}"'}
        )
    else:
        def _iterfile_sync():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
        return StreamingResponse(
            _iterfile_sync(),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{getattr(file, "filename", "file")}"'}
        )
