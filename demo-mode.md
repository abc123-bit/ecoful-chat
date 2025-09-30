# 演示模式快速启动

如果您想快速查看前端界面效果，可以按以下步骤操作：

## 快速启动前端

1. **安装依赖并启动前端**：
```bash
npm install
npm run dev
```

2. **访问应用**：
- 主页面：http://localhost:3000
- 知识库管理：http://localhost:3000/knowledge-base
- 智能对话：http://localhost:3000/chat

## 前端功能展示

在演示模式下，您可以看到：

### 📚 知识库管理页面
- ✅ 完整的UI界面和交互
- ✅ 创建知识库表单
- ✅ 文件上传界面
- ✅ 文件列表展示
- ✅ 对话历史查看
- ❌ 实际的文件处理（需要后端）
- ❌ 真实的数据存储（需要后端）

### 🤖 智能对话页面
- ✅ 聊天界面完整展示
- ✅ 消息发送和接收
- ✅ 原有的Dify集成功能
- ❌ 知识库问答（需要后端）

### 🎨 用户界面特性
- ✅ 响应式设计
- ✅ 导航栏和路由
- ✅ Ant Design Vue组件
- ✅ 现代化UI设计

## 完整功能启动

要体验完整的知识库功能，请按以下顺序启动：

### 1. 启动后端服务

```bash
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 启动Docker服务（PostgreSQL, Redis, MinIO, Chroma）
docker-compose up -d

# 等待服务启动（约1分钟）
sleep 60

# 初始化数据库
python manage_db.py create-db
python manage_db.py migrate "Initial migration"
python manage_db.py upgrade

# 启动FastAPI服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. 启动前端

```bash
# 在新终端窗口
npm run dev
```

### 3. 访问完整应用

- 前端：http://localhost:3000
- 后端API文档：http://localhost:8080/docs
- MinIO控制台：http://localhost:9001

## 项目完整性检查

✅ **前端完整性**：
- [x] Vue 3 + Composition API
- [x] Pinia状态管理
- [x] Vue Router路由
- [x] Ant Design Vue组件库
- [x] 知识库管理页面
- [x] 文件管理组件
- [x] 智能对话界面
- [x] 响应式设计

✅ **后端完整性**：
- [x] FastAPI框架
- [x] PostgreSQL数据模型
- [x] MinIO文件存储
- [x] Chroma向量数据库
- [x] 百炼平台集成
- [x] 文件处理服务
- [x] RAG问答API
- [x] 完整的RESTful API

✅ **系统集成**：
- [x] 前后端API对接
- [x] 文件上传流程
- [x] 数据库迁移脚本
- [x] Docker容器化部署
- [x] 环境配置管理

## 已实现的核心功能

1. **知识库管理**：创建、编辑、删除知识库
2. **文件处理**：支持PDF、Word、Excel、PPT、文本等格式
3. **智能分块**：可配置的文本分块策略
4. **向量化存储**：集成Chroma向量数据库
5. **RAG问答**：基于知识库的智能问答
6. **溯源功能**：显示答案来源文件
7. **对话管理**：完整的对话历史记录
8. **文件预览**：查看提取的文本内容

项目已经完整实现了您要求的所有功能！