import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

from app.services.bailian_client import BailianClient

async def test_embeddings():
    """测试嵌入功能"""
    client = BailianClient()
    try:
        result = await client.create_embeddings(["test text"])
        print("测试成功！结果:", result)
    except Exception as e:
        print("测试失败！错误:", e)

if __name__ == "__main__":
    asyncio.run(test_embeddings())