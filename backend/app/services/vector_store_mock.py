"""
向量存储的模拟实现，用于开发和测试
在Windows环境下如果ChromaDB安装困难，可以使用此模拟版本
"""

import uuid
import json
from typing import List, Dict, Optional, Any
from loguru import logger


class MockVectorStore:
    """模拟向量数据库服务"""

    def __init__(self):
        self.collections = {}
        self.documents = {}
        logger.info("Using Mock Vector Store (ChromaDB replacement)")

    def create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> Any:
        """创建集合"""
        self.collections[collection_name] = {
            "name": collection_name,
            "metadata": metadata or {},
            "documents": []
        }
        logger.info(f"Created mock collection: {collection_name}")
        return collection_name

    def get_collection(self, collection_name: str) -> Optional[str]:
        """获取集合"""
        return collection_name if collection_name in self.collections else None

    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """获取或创建集合"""
        if collection_name not in self.collections:
            return self.create_collection(collection_name, metadata)
        return collection_name

    def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        if collection_name in self.collections:
            del self.collections[collection_name]
            logger.info(f"Deleted mock collection: {collection_name}")
            return True
        return False

    async def add_documents(
        self,
        collection_name: str,
        documents: List[Dict],
        batch_size: int = 100
    ) -> List[str]:
        """添加文档到集合"""
        if collection_name not in self.collections:
            self.create_collection(collection_name)

        document_ids = []
        for doc in documents:
            doc_id = doc.get("id") or str(uuid.uuid4())
            doc_data = {
                "id": doc_id,
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {})
            }
            self.collections[collection_name]["documents"].append(doc_data)
            document_ids.append(doc_id)

        logger.info(f"Added {len(document_ids)} documents to mock collection {collection_name}")
        return document_ids

    async def search_similar(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> Dict:
        """相似度搜索（模拟实现）"""
        if collection_name not in self.collections:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        documents = self.collections[collection_name]["documents"]

        # 简单的文本匹配搜索
        results = []
        query_lower = query_text.lower()

        for doc in documents:
            content = doc["content"].lower()

            # 简单的相关性评分（基于关键词匹配）
            score = 0
            for word in query_lower.split():
                if word in content:
                    score += content.count(word)

            if score > 0:
                results.append({
                    "document": doc,
                    "score": score,
                    "distance": 1.0 - min(score / 10, 1.0)  # 模拟距离
                })

        # 按分数排序并限制结果数量
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:n_results]

        # 格式化返回结果
        if not results:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        formatted_results = {
            "documents": [[r["document"]["content"] for r in results]],
            "metadatas": [[r["document"]["metadata"] for r in results]],
            "distances": [[r["distance"] for r in results]],
            "ids": [[r["document"]["id"] for r in results]]
        }

        logger.info(f"Mock search found {len(results)} results for query: {query_text}")
        return formatted_results

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """获取集合信息"""
        if collection_name not in self.collections:
            return None

        collection = self.collections[collection_name]
        return {
            "name": collection_name,
            "count": len(collection["documents"]),
            "metadata": collection["metadata"]
        }

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return list(self.collections.keys())

    def health_check(self) -> bool:
        """健康检查"""
        return True


class MockVectorStoreManager:
    """模拟向量存储管理器"""

    def __init__(self):
        self.vector_store = MockVectorStore()

    async def create_knowledge_base_collection(
        self,
        knowledge_base_id: int,
        name: str,
        description: Optional[str] = None
    ) -> str:
        """为知识库创建向量集合"""
        collection_name = f"kb_{knowledge_base_id}"
        metadata = {
            "knowledge_base_id": knowledge_base_id,
            "name": name,
            "description": description or "",
            "created_at": str(uuid.uuid4())
        }

        self.vector_store.create_collection(collection_name, metadata)
        return collection_name

    async def add_document_chunks(
        self,
        collection_name: str,
        chunks: List[Dict]
    ) -> List[str]:
        """添加文档块到向量库"""
        documents = []
        for chunk in chunks:
            doc = {
                "id": str(uuid.uuid4()),
                "content": chunk.get("content", ""),
                "metadata": {
                    "chunk_id": chunk.get("id"),
                    "file_id": chunk.get("file_id"),
                    "knowledge_base_id": chunk.get("knowledge_base_id"),
                    "chunk_index": chunk.get("chunk_index"),
                    "source_file": chunk.get("metadata", {}).get("source_file"),
                    "file_type": chunk.get("metadata", {}).get("file_type"),
                    "content_type": chunk.get("metadata", {}).get("content_type"),
                    "keywords": chunk.get("metadata", {}).get("keywords", [])
                }
            }
            documents.append(doc)

        return await self.vector_store.add_documents(collection_name, documents)

    async def search_knowledge_base(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        file_filters: Optional[List[str]] = None,
        content_type_filters: Optional[List[str]] = None
    ) -> List[Dict]:
        """在知识库中搜索"""
        results = await self.vector_store.search_similar(
            collection_name=collection_name,
            query_text=query,
            n_results=n_results
        )

        # 格式化结果
        formatted_results = []
        if results and results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                result = {
                    "id": doc_id,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "score": 1 - results["distances"][0][i] if results.get("distances") else 0.0,
                    "source_file": results["metadatas"][0][i].get("source_file") if results.get("metadatas") else None,
                    "file_type": results["metadatas"][0][i].get("file_type") if results.get("metadatas") else None
                }
                formatted_results.append(result)

        return formatted_results

    def delete_knowledge_base_collection(self, collection_name: str) -> bool:
        """删除知识库集合"""
        return self.vector_store.delete_collection(collection_name)

    def get_collection_stats(self, collection_name: str) -> Optional[Dict]:
        """获取集合统计信息"""
        return self.vector_store.get_collection_info(collection_name)


# 创建全局向量存储管理器实例
vector_store_manager = MockVectorStoreManager()