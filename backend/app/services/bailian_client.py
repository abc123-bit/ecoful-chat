# ./backend/app/services/bailian_client.py
import json
import asyncio
from typing import List, Dict, Optional, Union, AsyncGenerator, Tuple
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


# === 内部常量：不改变外部契约，仅用于稳健性 ===
# 由于服务报错 “Range of input length should be [1, 8192]”，这里用字符长度做保守裁剪；
# 6000 字符在中/英混合场景下通常 < 8192 token，必要时你可以调整到 5500 或 6500。
_MAX_INPUT_CHARS = 6000
# 对单次请求的最大子批量，避免一次性发太多 input
_SUB_BATCH_SIZE = 64
# 兜底的向量维度（不调用 create_embeddings 以免递归）
_FALLBACK_EMBED_DIM = 1536


class BailianClient:
    """百炼平台API客户端"""

    def __init__(self):
        self.api_key = settings.BAILIAN_API_KEY
        self.endpoint = settings.BAILIAN_ENDPOINT
        self.embedding_model = settings.BAILIAN_EMBEDDING_MODEL
        self.chat_model = settings.BAILIAN_CHAT_MODEL

        # 百炼平台需要特定的认证格式
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    # ----------------- 私有辅助：文本分段 & 均值合并 -----------------

    @staticmethod
    def _soft_segments(text: str, max_chars: int = _MAX_INPUT_CHARS) -> List[str]:
        """把过长文本按字符安全上限切分；短文本保持 1 段。"""
        if text is None:
            text = ""
        if len(text) <= max_chars:
            return [text]
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    @staticmethod
    def _mean_vectors(vectors: List[List[float]]) -> List[float]:
        """对同一条文本的多个分段向量做元素均值（无 numpy 版）。"""
        if not vectors:
            return []
        length = len(vectors[0])
        if any(len(v) != length for v in vectors):
            # 维度不一致，直接返回首段，避免出错（极少发生）
            return vectors[0]
        sums = [0.0] * length
        for v in vectors:
            for i, x in enumerate(v):
                sums[i] += float(x)
        n = float(len(vectors))
        return [s / n for s in sums]

    def _zero_vector(self, dim: int = _FALLBACK_EMBED_DIM) -> List[float]:
        return [0.0] * dim

    # ----------------- 私有辅助：真正的 HTTP 调用（复用/降级） -----------------

    async def _post_embeddings(self, inputs: List[str], model_name: str) -> List[List[float]]:
        """对一批 inputs 调一次真实的 /embeddings 接口，返回等长向量列表。"""
        payload = {"model": model_name, "input": inputs}

        # 调试信息可按需打开
        # logger.debug(f"Request URL: {self.endpoint}/embeddings")
        # logger.debug(f"Request headers: {self.headers}")
        # logger.debug(f"Request payload size: {len(inputs)}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/embeddings",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        # 解析多种可能格式
        if "data" in result:
            embeddings = [item.get("embedding", []) for item in result["data"]]
        elif "output" in result and "embeddings" in result["output"]:
            embeddings = result["output"]["embeddings"]
        else:
            embeddings = []
            for key in result:
                if isinstance(result[key], list) and len(result[key]) > 0:
                    if isinstance(result[key][0], list):
                        embeddings = result[key]
                        break

        if not embeddings:
            logger.error(f"Unexpected response format: {result}")
            raise ValueError("Failed to extract embeddings from response")

        return embeddings

    # ----------------- 对外：保持签名/契约不变的 create_embeddings -----------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        创建文本嵌入向量
        - 保持对外契约：输入 N 条文本 -> 返回 N 条向量
        - 内部新增：过长文本自动分段；对分段向量做均值合并；子批失败降级逐条重试
        """
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []

        model_name = model or self.embedding_model

        # 1) 先将每条文本做“软分段”，记录映射关系
        # segments_flat: 扁平化后的所有分段；index_map[i] = (start_idx_in_flat, segment_count)
        segments_flat: List[str] = []
        index_map: List[Tuple[int, int]] = []
        for t in texts:
            segs = self._soft_segments(t, _MAX_INPUT_CHARS)
            start = len(segments_flat)
            segments_flat.extend(segs)
            index_map.append((start, len(segs)))

        if not segments_flat:
            return []

        # 2) 以子批为单位调用真实接口；若子批失败，降级到逐条重试，确保每段都有向量
        seg_vectors: List[List[float]] = []
        i = 0
        while i < len(segments_flat):
            sub = segments_flat[i:i + _SUB_BATCH_SIZE]
            try:
                vecs = await self._post_embeddings(sub, model_name)
                if not vecs or len(vecs) != len(sub):
                    raise RuntimeError("embedding api length mismatch")
                seg_vectors.extend(vecs)
                i += _SUB_BATCH_SIZE
                # 避免限流：如需更稳可适当 sleep
                # if i < len(segments_flat):
                #     await asyncio.sleep(0.1)
            except httpx.HTTPStatusError as e:
                # 如果是 400 且包含长度错误，直接降级逐条
                msg = e.response.text if e.response is not None else str(e)
                logger.error(f"HTTP error on segments batch ({i}-{i+len(sub)}): {e.response.status_code} - {msg}")
                # 降级逐条重试，避免整批失败
                for s in sub:
                    try:
                        v = await self._post_embeddings([s], model_name)
                        seg_vectors.extend(v)  # 单条也是列表
                    except Exception as ex2:
                        logger.error(f"embedding failed on single segment: {ex2}")
                        seg_vectors.append(self._zero_vector())
                i += _SUB_BATCH_SIZE
            except Exception as e:
                logger.error(f"Unexpected error on segments batch ({i}-{i+len(sub)}): {e}")
                # 同样降级逐条
                for s in sub:
                    try:
                        v = await self._post_embeddings([s], model_name)
                        seg_vectors.extend(v)
                    except Exception as ex2:
                        logger.error(f"embedding failed on single segment: {ex2}")
                        seg_vectors.append(self._zero_vector())
                i += _SUB_BATCH_SIZE

        # 3) 将分段向量按映射关系合并为“每条文本一条向量”
        out_vectors: List[List[float]] = []
        for start, count in index_map:
            if count == 1:
                out_vectors.append(seg_vectors[start])
            else:
                merged = self._mean_vectors(seg_vectors[start:start + count])
                out_vectors.append(merged)

        logger.info(f"Created embeddings for {len(texts)} texts using model {model_name}")
        return out_vectors

    # ----------------- 对外：聊天接口（未改动） -----------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[Dict, AsyncGenerator[Dict, None]]:
        """
        聊天完成API
        """
        model_name = model or self.chat_model

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            if stream:
                return self._stream_chat_completion(payload)
            else:
                return await self._single_chat_completion(payload)

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise

    async def _single_chat_completion(self, payload: Dict) -> Dict:
        """非流式聊天完成"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Chat completion completed with model {payload['model']}")
            return result

    async def _stream_chat_completion(self, payload: Dict) -> AsyncGenerator[Dict, None]:
        """流式聊天完成"""
        payload["stream"] = True

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀

                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            continue

    # ----------------- 对外：批量嵌入（不改用法） -----------------

    async def batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10,
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        批量创建嵌入向量
        - 保持原用法：按 batch_size 分批调用 create_embeddings
        - create_embeddings 内部已具备分段/容错，这里无需再切分
        """
        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                batch_embeddings = await self.create_embeddings(batch_texts, model)
                all_embeddings.extend(batch_embeddings)

                # 避免API限流（按需调整/或关闭）
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing batch {i}-{i + batch_size}: {e}")
                # 为失败的批次创建空向量（保持返回长度一致）
                all_embeddings.extend([self._zero_vector() for _ in batch_texts])

        logger.info(f"Completed batch embeddings for {len(texts)} texts")
        return all_embeddings

    async def get_embedding_dimensions(self, model: Optional[str] = None) -> int:
        """
        获取嵌入向量维度
        """
        try:
            # 使用测试文本获取维度
            test_embeddings = await self.create_embeddings(["test"], model)
            if test_embeddings and test_embeddings[0]:
                return len(test_embeddings[0])
            else:
                # 默认维度（根据百炼平台的默认embedding模型）
                return _FALLBACK_EMBED_DIM
        except Exception as e:
            logger.warning(f"Could not determine embedding dimensions: {e}")
            return _FALLBACK_EMBED_DIM  # 默认维度

    async def health_check(self) -> bool:
        """
        健康检查
        """
        try:
            # 简单的embedding测试
            await self.create_embeddings(["health check"])
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class RAGService:
    """RAG服务，结合检索和生成"""

    def __init__(self, bailian_client: Optional[BailianClient] = None):
        self.bailian_client = bailian_client or BailianClient()

    async def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Union[Dict, AsyncGenerator[Dict, None]]:
        """
        基于检索到的上下文生成答案
        """
        # 构建上下文
        context_text = self._build_context(context_chunks)

        # 构建提示词
        messages = self._build_messages(question, context_text, system_prompt)

        try:
            response = await self.bailian_client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                stream=stream
            )

            if stream:
                return self._process_stream_response(response, context_chunks)
            else:
                return self._process_single_response(response, context_chunks)

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def _build_context(self, context_chunks: List[Dict]) -> str:
        """构建上下文文本"""
        if not context_chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(context_chunks[:5], 1):  # 最多使用5个chunk
            content = chunk.get("content", "")
            source = chunk.get("source_file", "未知来源")
            context_parts.append(f"[文档{i}] 来源: {source}\n{content}")

        return "\n\n".join(context_parts)

    def _build_messages(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        if system_prompt is None:
            system_prompt = """你是一个专业的知识库助手，请根据提供的上下文信息回答用户的问题。
                                请遵循以下规则：
                                1. 仅基于提供的上下文信息回答问题
                                2. 如果上下文中没有相关信息，请明确说明
                                3. 回答要准确、详细且有条理
                                4. 在回答中引用具体的文档来源
                                5. 如果需要澄清问题，请主动询问"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if context:
            user_message = f"上下文信息：\n{context}\n\n问题：{question}"
        else:
            user_message = f"问题：{question}\n\n注意：没有找到相关的上下文信息，请告诉用户需要更多信息才能回答这个问题。"

        messages.append({"role": "user", "content": user_message})

        return messages

    def _process_single_response(self, response: Dict, context_chunks: List[Dict]) -> Dict:
        """处理单次响应"""
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")

            usage = response.get("usage", {})

            return {
                "answer": content,
                "sources": self._extract_sources(context_chunks),
                "usage": usage,
                "model": response.get("model"),
                "context_chunks": len(context_chunks)
            }
        except Exception as e:
            logger.error(f"Error processing single response: {e}")
            raise

    async def _process_stream_response(
        self,
        response_stream: AsyncGenerator[Dict, None],
        context_chunks: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """处理流式响应"""
        try:
            async for chunk in response_stream:
                choice = chunk.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                content = delta.get("content", "")

                if content:
                    yield {
                        "content": content,
                        "sources": self._extract_sources(context_chunks),
                        "finished": False
                    }

                if choice.get("finish_reason"):
                    yield {
                        "content": "",
                        "sources": self._extract_sources(context_chunks),
                        "finished": True,
                        "context_chunks": len(context_chunks)
                    }

        except Exception as e:
            logger.error(f"Error processing stream response: {e}")
            raise

    def _extract_sources(self, context_chunks: List[Dict]) -> List[Dict]:
        """提取源文件信息"""
        sources = []
        seen_files = set()

        for chunk in context_chunks:
            source_file = chunk.get("source_file")
            if source_file and source_file not in seen_files:
                sources.append({
                    "file_name": source_file,
                    "file_type": chunk.get("file_type"),
                    "chunk_id": chunk.get("id"),
                    "relevance_score": chunk.get("score", 0.0)
                })
                seen_files.add(source_file)

        return sources


# 创建全局实例
bailian_client = BailianClient()
rag_service = RAGService(bailian_client)

# ----------------- 简单测试 -----------------
async def test_embeddings():
    """测试嵌入功能"""
    client = BailianClient()
    try:
        result = await client.create_embeddings(["test text"])
        print("测试成功！结果:", result)
    except Exception as e:
        print("测试失败！错误:", e)

# 运行测试
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_embeddings())

# ----------------- 简单测试 -----------------
