
# Ecoful Chat Platform

    生态化的一体化聊天与知识库系统，整合 Vue 3 前端、FastAPI 后端，以及基于百炼平台的检索增强问答能力，同时兼容 Dify 工作流聊 
        天入口。

    ## 功能亮点
    - 统一聊天工作台：在一个界面内切换百炼 RAG 知识库与 Dify 智能体。
    - 知识库管理：创建知识库、上传文档、自动分块、向量化与溯源展示。
    - 实时流式问答：Server-Sent Events 逐字渲染，并即时写入对话历史。                                                         
    - 多数据后端：PostgreSQL、Redis、MinIO、Chroma 协同提供结构化与向量存储。                                                 
    - 部署灵活：可选本地开发、Docker Compose 或自定义服务器部署方案。                                                         
                                                                                                                              
    ## 系统架构概览                                                                                                           
    - 前端 (Vite + Vue 3 + Ant Design Vue)                                                                                    
      - `views/UnifiedChat.vue`：统一聊天入口，聚合 RAG 与 Dify                                                               
      - `views/KnowledgeBase.vue`：知识库与文件管理                                                                           
      - `providers/`：抽象 provider 层 (ragProvider, difyProvider)                                                            
      - `services/`：REST/SSE 封装 (knowledgeBase.js, dify.js 等)                                                             
    - 后端 (FastAPI + SQLAlchemy)                                                                                             
      - `api/v1/endpoints/`：知识库、聊天、文件相关接口                                                                       
      - `services/`：百炼客户端、向量库管理、文件处理                                                                         
      - `models/`、`schemas/`：数据库 ORM 与 Pydantic 模型                                                                    
    - 数据与 AI 依赖                                                                                                          
      - PostgreSQL：结构化数据 (知识库、文件、会话)                                                                           
      - Redis：缓存与任务辅助                                                                                                 
      - MinIO：对象存储原始文件                                                                                               
      - Chroma DB：文档向量库                                                                                                 
      - 百炼平台：文本嵌入、问答模型                                                                                          
      - Dify：可选对话代理服务                                                                                                
                                                                                                                              
    ## 代码结构                                                                                                               
    ```                                                                                                                       
    ├─ src/                                                                                                                   
    │  ├─ components/        # 公共组件 (Sidebar、MainChat 等)                                                                
    │  ├─ providers/         # Provider 适配层 (rag/dify)                                                                     
    │  ├─ services/          # API 帮助类                                                                                     
    │  ├─ stores/            # Pinia 状态                                                                                     
    │  └─ views/             # 页面组件 (UnifiedChat、KnowledgeBase...)                                                       
    ├─ backend/                                                                                                               
    │  ├─ app/                                                                                                                
    │  │  ├─ api/            # FastAPI 路由                                                                                   
    │  │  ├─ core/           # 配置加载 (config.py)                                                                           
    │  │  ├─ models/         # SQLAlchemy ORM                                                                                 
    │  │  ├─ schemas/        # Pydantic 模型                                                                                  
    │  │  └─ services/       # 向量、百炼、文件处理模块                                                                       
    │  ├─ migrations/        # Alembic 迁移脚本                                                                               
    │  ├─ Dockerfile                                                                                                          
    │  └─ docker-compose.yml # 后端服务栈 (API + 依赖)                                                                        
    ├─ docker-compose.yml    # 数据服务 (Postgres/Redis/MinIO/Chroma)                                                         
    └─ README.md                                                                                                              
    ```                                                                                                                       
                                                                                                                              
    ## 环境准备                                                                                                               
    - Node.js >= 16                                                                                                           
    - Python >= 3.11                                                                                                          
    - PostgreSQL 15                                                                                                           
    - Redis 7                                                                                                                 
    - MinIO (或兼容 S3 对象存储)                                                                                              
    - Chroma DB (HTTP 服务模式)                                                                                               
    - 百炼平台 API Key (嵌入与问答)                                                                                           
    - Dify API Key (可选)                                                                                                     
                                                                                                                              
    ## 配置环境变量                                                                                                           
                                                                                                                              
    ### 前端 `.env`                                                                                                           
    ```                                                                                                                       
    cp .env.example .env                                                                                                      
    ```                                                                                                                       
    示例键值：                                                                                                                
    ```                                                                                                                       
    VITE_API_BASE_URL=http://localhost:8080/api/v1                                                                            
    VITE_DIFY_API_URL=https://your-dify-host/v1                                                                               
    VITE_DIFY_API_KEY=your_dify_api_key                                                                                       
    ```                                                                                                                       
                                                                                                                              
    ### 后端 `backend/.env`                                                                                                   
    ```                                                                                                                       
    cd backend                                                                                                                
    cp .env.example .env                                                                                                      
    ```                                                                                                                       
    关键变量包括：                                                                                                            
    - DATABASE_URL：PostgreSQL 连接串                                                                                         
    - REDIS_URL：Redis 地址 (例如 `redis://localhost:6379/0`)                                                                 
    - MINIO_ENDPOINT / ACCESS_KEY / SECRET_KEY / BUCKET_NAME                                                                  
    - BAILIAN_API_KEY、BAILIAN_ENDPOINT、BAILIAN_EMBEDDING_MODEL、BAILIAN_CHAT_MODEL                                          
    - CHROMA_HOST、CHROMA_PORT                                                                                                
    - SECRET_KEY：生成 JWT 或签名所用密钥                                                                                     
                                                                                                                              
    > 建议将 `.env` 与 `backend/.env` 加入 `.gitignore`，保证密钥不被提交。                                                   
                                                                                                                              
    ## 后端启动流程                                                                                                           
    ```                                                                                                                       
    cd backend                                                                                                                
    python -m venv venv                                                                                                       
    source venv/bin/activate      # Windows: venv\Scripts\activate                                                            
    pip install -r requirements.txt                                                                                           
                                                                                                                              
    # 可选：使用 Docker Compose 启动依赖服务                                                                                  
    docker compose up -d          # backend/docker-compose.yml 或根目录 docker-compose.yml                                    
                                                                                                                              
    # 初始化数据库 (需已配置好 DATABASE_URL)                                                                                  
    alembic upgrade head          # 或 python manage_db.py upgrade                                                            
                                                                                                                              
    # 启动 FastAPI (默认 8080)                                                                                                
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload                                                                  
                                                                                                                              
    # 运行测试                                                                                                                
    pytest backend/tests                                                                                                      
    ```                                                                                                                       
                                                                                                                              
    ## 前端启动流程                                                                                                           
    ```                                                                                                                       
    npm install                                                                                                               
    npm run dev        # http://localhost:3000                                                                                
                                                                                                                              
    # 生产构建与预览                                                                                                          
    npm run build                                                                                                             
    npm run preview                                                                                                           
                                                                                                                              
    # 质量工具                                                                                                                
    npm run lint                                                                                                              
    npm run format                                                                                                            
    ```                                                                                                                       
                                                                                                                              
    ## 典型使用步骤                                                                                                           
    1. 启动数据库、Redis、MinIO、Chroma 等依赖服务。                                                                          
    2. 运行 FastAPI 后端，确保百炼和存储配置正确。                                                                            
    3. 启动前端，访问 `http://localhost:3000`。                                                                               
    4. 在知识库页面创建知识库，上传文档等待处理完成。                                                                         
    5. 切换到统一聊天页：                                                                                                     
       - 选择 RAG provider 并指定知识库 ID，即可针对文档提问（回答同时展示参考来源）。                                        
       - 切换到 Dify provider，填写对应智能体信息后即可对话。                                                                 
                                                                                                                              
    ## 部署与运维建议                                                                                                         
    - 生产环境建议将前端打包后的 `dist/` 部署到 Nginx 或静态托管服务，后端使用 Gunicorn/Uvicorn + Supervisor 或容器编排。     
    - 若服务器已运行其他 Postgres/Redis/MinIO，请调整 `.env` 端口或直连既有服务，避免冲突。                                   
    - 上传文件体积较大时，请配置 MinIO/对象存储生命周期与备份策略。                                                           
    - 百炼与 Dify API Key 属敏感信息，推荐通过环境变量或密钥服务注入，不直接写入代码。                                        
                                                                                                                              
    ## 常用命令速查                                                                                                           
    - `docker compose up -d`：启动根目录数据服务栈 (5432/6379/9000/8001)。                                                    
    - `npm run lint -- --fix`：自动修复前端 lint 问题。                                                                       
    - `pytest backend/tests -k test_chat`：运行聊天相关后端测试。                                                             
    - `python manage_db.py`：查看数据库初始化、迁移等辅助命令。                                                               
                                                                                                                              
    ## 疑难排查                                                                                                               
    - **首条对话未出现在历史中**：统一聊天入口已实现临时会话占位，若仍缺失，请检查后端 SSE 是否返回 `conversation_id`。       
    - **百炼请求报错**：确认选择的模型与账号权限匹配，必要时在日志中查看具体响应。                                            
    - **MinIO 预览失败**：确认 `MINIO_PUBLIC_ENDPOINT` 或使用 `KnowledgeBaseService.enrichSourcesWithUrls` 获得预签名链接。   
    - **端口被占用**：编辑两个 `docker-compose.yml` 将宿主机端口改为不冲突的值，或直接连接已有服务。      
