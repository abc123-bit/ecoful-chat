# 知识库管理系统

基于现有ecoful-chat项目，新增完整的知识库管理和RAG问答功能。

## 🚀 新增功能

### 📚 知识库管理
- **创建知识库**: 支持自定义分块参数和配置
- **文件上传**: 支持PDF、Word、Excel、PowerPoint、文本等多种格式
- **文件处理**: 自动文本提取和分块处理
- **向量化**: 集成百炼平台进行文本向量化
- **向量存储**: 使用Chroma向量数据库存储

### 🤖 智能问答
- **RAG问答**: 基于知识库的检索增强生成
- **流式响应**: 支持实时流式回答
- **溯源功能**: 显示答案来源文件和相关段落
- **对话历史**: 完整的对话记录和管理

### 💾 数据存储
- **PostgreSQL**: 存储知识库、文件、对话等结构化数据
- **MinIO**: 对象存储，保存原始文件
- **Chroma**: 向量数据库，存储文档向量
- **Redis**: 缓存和会话管理

## 📋 系统架构

```
前端 (Vue 3 + Ant Design Vue)
├── 知识库管理页面
├── 文件上传和处理
├── 智能问答界面
└── 文件溯源查看

后端 (FastAPI)
├── 知识库管理API
├── 文件处理服务
├── 向量化服务
├── 问答API
└── 对话管理

数据层
├── PostgreSQL (结构化数据)
├── MinIO (文件存储)
├── Chroma (向量数据库)
└── Redis (缓存)

AI服务
├── 百炼平台 (文本向量化)
└── 百炼平台 (问答生成)
```

## 🛠️ 安装部署

### 环境要求
- Python 3.11+
- Node.js 16+
- PostgreSQL 15+
- Redis 7+
- MinIO
- Chroma DB

### 后端部署

1. **进入后端目录**
```bash
cd backend
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置以下参数：

# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/knowledge_base

# Redis配置
REDIS_URL=redis://localhost:6379

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=knowledge-base

# 百炼平台配置
BAILIAN_API_KEY=your_bailian_api_key
BAILIAN_ENDPOINT=https://dashscope.aliyuncs.com/api/v1

# Chroma配置
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

4. **使用Docker启动依赖服务**
```bash
docker-compose up -d
```

5. **初始化数据库**
```bash
python manage_db.py create-db
python manage_db.py migrate "Initial migration"
python manage_db.py upgrade
```

6. **启动后端服务**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 前端部署

1. **安装依赖**
```bash
npm install
```

2. **配置环境变量**
```bash
# 在 .env 文件中添加:
VITE_API_BASE_URL=http://localhost:8080/api/v1
```

3. **启动开发服务器**
```bash
npm run dev
```

4. **构建生产版本**
```bash
npm run build
```

## 📖 使用指南

### 创建知识库

1. 访问 `http://localhost:3000/knowledge-base`
2. 点击"新建知识库"按钮
3. 填写知识库名称、描述等信息
4. 设置分块参数（建议：分块大小1000，重叠200）
5. 点击"创建"完成

### 上传文件

1. 选择已创建的知识库
2. 点击"上传文件"按钮
3. 选择支持的文件格式：
   - PDF文档
   - Word文档 (.docx, .doc)
   - Excel表格 (.xlsx, .xls)
   - PowerPoint演示文稿 (.pptx, .ppt)
   - 纯文本文件 (.txt, .md)
   - 图片文件 (.jpg, .png, .gif)

4. 等待文件处理完成（状态显示为"已完成"）

### 智能问答

1. 选择知识库后点击"开始问答"
2. 或访问聊天页面并在URL中指定知识库ID：`/chat?kb=1`
3. 输入问题，系统会：
   - 在知识库中搜索相关内容
   - 基于搜索结果生成回答
   - 显示答案来源文件

### 查看文件内容

1. 在文件管理标签页中点击"查看"
2. 可以查看提取的文本内容
3. 查看文件处理状态和统计信息

## 🔧 配置说明

### 分块参数优化

| 文件类型 | 推荐分块大小 | 推荐重叠 |
|----------|-------------|----------|
| 长文档 | 1500-2000 | 200-300 |
| 短文档 | 800-1200 | 100-200 |
| 代码文件 | 1000-1500 | 150-250 |
| 表格数据 | 500-1000 | 50-100 |

### 百炼平台配置

1. 注册阿里云账号
2. 开通百炼平台服务
3. 获取API密钥
4. 配置环境变量中的`BAILIAN_API_KEY`

### 性能优化建议

- **数据库**: 配置PostgreSQL连接池
- **缓存**: 启用Redis缓存频繁查询
- **文件存储**: MinIO配置多副本
- **向量库**: Chroma配置持久化存储

## 🐛 常见问题

### 文件上传失败
- 检查文件大小是否超过100MB限制
- 确认文件格式是否支持
- 检查MinIO服务是否正常运行

### 向量化失败
- 检查百炼平台API密钥是否正确
- 确认网络连接是否正常
- 检查API配额是否充足

### 问答无结果
- 确认知识库中有已处理完成的文件
- 检查向量数据库连接
- 尝试调整搜索参数

## 📊 监控和日志

- **日志位置**: `backend/logs/`
- **API文档**: `http://localhost:8080/docs`
- **健康检查**: `http://localhost:8080/health`

## 🔄 更新和维护

### 数据库迁移
```bash
python manage_db.py migrate "migration description"
python manage_db.py upgrade
```

### 备份恢复
```bash
# 备份数据库
pg_dump knowledge_base > backup.sql

# 备份MinIO数据
mc mirror minio/knowledge-base ./backup/files/

# 备份Chroma数据
cp -r ./chroma_data ./backup/vectors/
```

## 📄 License

MIT License - 基于原项目License继承