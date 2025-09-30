# 仓库指南

## 项目结构与模块组织
- 前端（Vue 3）位于 `src/`：可复用组件在 `src/components`，视图壳在 `src/views`，Pinia 仓库在 `src/stores`，API 助手在 `src/services`，静态资源在 `src/assets`。应用入口为 `src/main.js`；Vite 构建产物输出到 `dist/`。
- 后端（FastAPI）位于 `backend/app`：路由在 `api/`，配置在 `core/`，数据库会话在 `db/`，ORM `models/` 与 Pydantic `schemas/`。
- 数据库迁移在 `backend/migrations`；测试在 `backend/tests`；Docker 与辅助脚本位于仓库根目录。

## 构建、测试与开发命令
- 安装前端依赖：`npm install`
- 启动开发服务器：`npm run dev`（Vite 于 http://localhost:3000）
- 构建/预览：`npm run build` → `dist/`；`npm run preview`
- 代码检查/格式化：`npm run lint`（ESLint 使用 `@vue/standard`）；`npm run format`（对 `src/` 运行 Prettier）
- 准备后端环境：`python -m venv venv && pip install -r backend/requirements.txt`
- 运行 API（在 `backend/` 下）：`uvicorn app.main:app --reload --port 8080`
- 轻量模拟服务：`python backend/start_simple.py`
- 运行测试：`pytest backend/tests`

## 代码风格与命名约定
- Vue：两个空格缩进、无分号、单引号。组件文件用 PascalCase（如 `ChatSidebar.vue`）。Pinia 仓库使用 camelCase（如 `useChatStore`）。功能工具放在 `src/utils`。
- Python：遵循 PEP 8，四空格缩进，文件名用 snake_case。必要处添加类型标注。优先使用 `loguru` 进行结构化日志，而非 `print`。

## 测试指南
- 后端使用 pytest 与 FastAPI `TestClient`；参考 `backend/tests/test_knowledge_base.py` 的异步用法。
- 使用具描述性的测试名（如 `test_create_knowledge_base`），通过夹具隔离临时数据。
- 提交前运行：`pytest backend/tests`。

## 提交与拉取请求规范
- 采用 Conventional Commits：`feat:`、`fix:`、`chore:`（scope 可选）。
- PR 应包含：变更摘要、影响包（`frontend`、`backend`）、关联 issue、UI 改动的前/后截图、所需 `.env` 变量，以及迁移说明（执行 `alembic upgrade head`）。

## 配置说明
- 将 `.env.example` 复制为前端 `.env`，将 `backend/.env.example` 复制为后端 `backend/.env`。
- 切勿提交真实密钥；通过团队金库共享。
- 容器：全栈使用根目录 `docker-compose.yml`；仅 API 使用 `backend/docker-compose.yml`。

