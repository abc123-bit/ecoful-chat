#!/usr/bin/env python3
"""
简化版后端启动脚本
用于快速启动和测试基础功能
"""

import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 启动知识库管理系统 (简化模式)")
    print("📍 前端地址: http://localhost:3000")
    print("📍 后端地址: http://localhost:8080")
    print("📍 API文档: http://localhost:8080/docs")
    print("⚠️  当前为简化模式，部分功能为模拟实现")
    print("-" * 50)

    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )