# Vue Dify Chat

基于 Vue 3 的类 OpenAI 聊天界面，集成 Dify 对话工作流 API，提供完整的 AI 对话体验。

> **版本：v1.1.0** - 已修复 CSS 语法错误，优化部署配置

## ✨ 功能特性

### 🎨 用户界面
- **类 ChatGPT 布局**：左侧边栏 + 右侧主聊天区
- **响应式设计**：完美适配桌面端和移动端
- **优雅的 UI**：基于 Ant Design Vue 组件库
- **暗色侧边栏**：现代化的视觉设计

### 💬 对话功能
- **实时流式响应**：基于 Server-Sent Events 的逐字输出
- **停止生成**：可随时中断AI回答的生成过程
- **Markdown 渲染**：支持代码高亮、表格、链接等
- **思考过程显示**：特殊处理 `<think></think>` 标签，用灰色小字体显示AI思考过程
- **消息操作**：一键复制、点赞、点踩功能
- **响应统计**：显示消息数量和状态信息

### 📱 交互体验
- **新建对话**：快速创建新的聊天会话
- **历史管理**：自动加载和浏览Dify服务器的历史对话记录
- **会话恢复**：点击历史会话可完整恢复对话内容并继续提问
- **错误处理**：友好的错误提示和重试机制
- **加载状态**：清晰的加载动画和状态指示

### 🔧 技术特性
- **Vue 3 Composition API**：现代化的 Vue 开发方式
- **Pinia 状态管理**：轻量级的状态管理方案
- **TypeScript 支持**：更好的类型安全
- **Vite 构建**：快速的开发和构建体验

## 🚀 快速开始

### 环境要求
- Node.js >= 16.0.0
- npm >= 7.0.0 或 yarn >= 1.22.0

### 安装依赖
```bash
# 下载项目
cd ecoful-chat

# 安装依赖
npm install
# 或
yarn install
```

### 环境配置
1. 复制环境变量配置文件：
```bash
cp .env.example .env
```

2. 配置 Dify API 参数：
```env
# Dify API 配置
VITE_DIFY_API_URL=your Dify host address (https://api.dify.ai/v1)
VITE_DIFY_API_KEY=your_dify_api_key_here
```

### 获取 Dify API 密钥
1. 登录 [Dify 控制台](https://dify.ai)
2. 创建或选择一个ChatFlow应用
3. 在应用设置中获取 API Key

### 启动开发服务器
```bash
npm run dev
# 或
yarn dev
```

访问 http://localhost:3000 即可使用应用。

### 构建生产版本
```bash
npm run build
# 或
yarn build
```

## 📁 项目结构

```
ecoful-chat/
├── public/                 # 静态资源
├── src/
│   ├── assets/            # 样式和资源文件
│   │   └── style.css      # 全局样式
│   ├── components/        # Vue 组件
│   │   ├── Sidebar.vue    # 侧边栏组件
│   │   ├── MainChat.vue   # 主聊天区组件
│   │   └── Message.vue    # 消息组件
│   ├── services/          # API 服务
│   │   └── dify.js        # Dify API 集成
│   ├── stores/            # Pinia 状态管理
│   │   └── chat.js        # 聊天状态管理
│   ├── utils/             # 工具函数
│   │   └── helpers.js     # 辅助函数
│   ├── views/             # 页面组件
│   │   └── Chat.vue       # 聊天页面
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── .env.example           # 环境变量示例
├── .gitignore            # Git 忽略文件
├── index.html            # HTML 模板
├── package.json          # 项目配置
├── vite.config.js        # Vite 配置
└── README.md             # 项目文档
```

## 🔌 Dify API 集成

### 支持的 API 功能
- **对话消息发送**：`/chat-messages` 接口
- **流式响应**：Server-Sent Events 实时流
- **历史对话**：`/conversations` 管理
- **消息反馈**：点赞/点踩功能
- **对话删除**：清理历史记录

### API 配置说明
```javascript
// src/services/dify.js
const difyService = {
  baseURL: 'https://api.dify.ai/v1',
  apiKey: 'your_api_key',
}
```

### 流式响应处理
应用使用 Fetch API 和 ReadableStream 处理 Dify 的流式响应：

```javascript
// 处理流式数据
const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  // 解析 SSE 数据
  const chunk = decoder.decode(value)
  // 处理增量消息...
}
```

## 🧠 AI思考过程显示

### 功能说明
当AI的回复包含 `<think></think>` 标签时，系统会自动将思考过程用特殊样式显示：

- **视觉区分**：灰色背景和较小字体
- **思考标识**：自动添加 💭 图标和"思考过程"标签
- **独立区域**：与正式回答内容明确分离

### 示例效果
```
💭 思考过程：
用户问了一个关于编程的问题，我需要提供清晰的解释...

正式回答：
JavaScript 是一种动态编程语言...
```

### 技术实现
- 使用正则表达式预处理内容
- 自动转换为带样式的HTML元素
- 保持Markdown渲染的完整性

## 🛑 停止生成功能

### 功能说明
在AI回答生成过程中，用户可以随时停止回答的生成：

- **红色停止按钮**：在AI生成时，发送按钮变为红色停止按钮
- **即时中断**：点击停止按钮立即中断API请求和流式响应
- **友好提示**：停止后显示"已停止生成"的提示信息
- **状态恢复**：停止后自动恢复到可发送新消息的状态

### 使用场景
- AI回答太长，想要提前结束
- AI回答方向不对，需要重新提问
- 网络状况不佳，响应太慢
- 误触发送，想要撤回

### 技术实现
- 使用 `AbortController` 控制HTTP请求
- 在流式响应循环中检查中止信号
- 优雅处理中断异常，避免错误提示
- 支持演示模式和真实API模式

## 📚 历史会话管理

### 功能说明
系统会自动从Dify服务器加载用户的历史会话，实现跨设备、跨会话的对话连续性：

- **自动加载**：页面启动时自动获取历史会话列表
- **分类显示**：侧边栏分别显示"当前会话"和"历史会话"
- **完整恢复**：点击历史会话可完整加载所有消息记录
- **继续对话**：在历史会话基础上可以继续提问
- **实时同步**：支持手动刷新获取最新历史记录

### 界面布局
```
侧边栏结构:
├── 新的对话 (按钮)
├── 刷新历史 (按钮)
└── 会话列表 (按时间倒序)
    ├── 今天的讨论 (刚刚) [删除]
    ├── JavaScript 问题 (2小时前) [删除]  
    ├── 关于Vue的讨论 (昨天) [📖历史]
    ├── API设计方案 (3天前) [📖历史]
    └── 算法优化思路 (1周前) [📖历史]
```

### 会话标识
- **当前会话**：显示删除按钮，可以删除
- **历史会话**：显示历史图标(📖)，不能删除但可以加载

### 使用方式
1. **查看所有会话**：侧边栏按时间顺序显示所有会话（当前+历史）
2. **加载历史会话**：点击带历史图标的会话，自动加载完整对话内容
3. **继续对话**：在任何会话中都可以继续发送新消息
4. **刷新历史**：点击"刷新历史"按钮获取最新的历史会话
5. **避免重复**：已加载的历史会话不会在列表中重复显示

### 技术实现
- 使用Dify的 `/conversations` API获取会话列表
- 使用Dify的 `/messages` API获取具体会话的消息记录
- 智能转换Dify消息格式为本地显示格式
- 保持会话ID映射，支持在历史会话中继续对话

## 🎯 核心功能详解

### 对话管理
- **会话创建**：自动生成唯一 ID 的新对话
- **智能清理**：自动清理没有消息的空会话，避免重复
- **历史同步**：自动从Dify服务器加载历史会话列表
- **会话恢复**：完整加载历史对话的消息记录，支持继续对话
- **双重列表**：区分显示当前会话和历史会话
- **标题生成**：基于首条用户消息自动生成标题
- **状态持久化**：使用 Pinia 管理对话状态
- **消息历史**：完整的消息记录和时间戳

### 消息渲染
- **Markdown 支持**：使用 markdown-it 解析
- **代码高亮**：集成 highlight.js 语法高亮
- **思考过程**：自动识别和美化显示 `<think></think>` 标签内容
- **安全渲染**：防止 XSS 攻击的内容过滤
- **响应式布局**：移动端友好的消息显示

### 用户交互
- **实时输入**：支持多行输入和快捷键发送
- **停止控制**：AI生成过程中可随时点击停止按钮中断
- **操作反馈**：点赞、点踩、复制等交互
- **错误处理**：网络错误、API 限流等异常提示
- **加载状态**：流式响应时的实时加载动画

## 📱 移动端适配

### 响应式断点
- **桌面端**：≥ 768px，显示固定侧边栏
- **移动端**：< 768px，侧边栏变为抽屉模式

### 移动端优化
- **触摸友好**：适合手指操作的按钮大小
- **滑动操作**：支持手势打开/关闭侧边栏
- **输入体验**：移动端键盘适配
- **性能优化**：减少不必要的重渲染

## 🛠️ 开发指南

### 自定义主题
修改 `src/assets/style.css` 中的 CSS 变量：

```css
:root {
  --primary-color: #1677ff;
  --sidebar-bg: #171717;
  --message-bg: #f7f7f8;
  /* 更多主题变量... */
}
```

### 扩展 API 服务
在 `src/services/dify.js` 中添加新的 API 方法：

```javascript
class DifyService {
  async customMethod(params) {
    // 自定义 API 调用
  }
}
```

### 添加新组件
1. 在 `src/components/` 创建新组件
2. 在 `src/views/Chat.vue` 中引入和使用
3. 通过 props 和 events 进行数据传递

### 状态管理扩展
在 `src/stores/chat.js` 中添加新的状态和操作：

```javascript
export const useChatStore = defineStore('chat', () => {
  const newState = ref(initialValue)
  
  const newAction = () => {
    // 状态操作逻辑
  }
  
  return { newState, newAction }
})
```

## 🔧 配置选项

### Vite 配置
`vite.config.js` 支持的配置项：
- **路径别名**：`@` 指向 `src` 目录
- **开发端口**：默认 3000
- **构建输出**：`dist` 目录

### 环境变量
支持的环境变量：
- `VITE_DIFY_API_URL`：Dify API 地址
- `VITE_DIFY_API_KEY`：API 密钥
- `VITE_DIFY_APP_TOKEN`：应用令牌

## 🚀 部署指南

### 静态部署
1. 构建生产版本：`npm run build`
2. 将 `dist` 目录部署到静态服务器
3. 配置服务器支持 SPA 路由

### Docker 部署
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### 环境配置
- **开发环境**：使用 `.env.development`
- **生产环境**：使用 `.env.production`
- **服务器环境变量**：直接设置系统环境变量

## 🔒 安全考虑

### API 密钥安全
- 使用环境变量存储敏感信息
- 不要在客户端代码中硬编码 API 密钥
- 考虑使用代理服务器隐藏真实 API 地址

### 内容安全
- Markdown 渲染已配置 XSS 防护
- 用户输入经过适当的转义处理
- 限制文件上传和外部链接访问

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

### 开发规范
- 使用 ESLint 和 Prettier 格式化代码
- 遵循 Vue 3 组合式 API 最佳实践
- 编写清晰的提交信息
- 添加必要的注释和文档


## 🆘 常见问题

### Q: 如何解决 CORS 跨域问题？
A: 在 `vite.config.js` 中配置代理：
```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

### Q: 流式响应中断怎么办？
A: 检查网络连接和 Dify API 状态，应用会自动重试失败的请求。

### Q: 如何自定义 Markdown 渲染？
A: 修改 `src/utils/helpers.js` 中的 `markdown-it` 配置：
```javascript
const md = new MarkdownIt({
  // 自定义配置选项
})
```

### Q: 移动端侧边栏不显示？
A: 检查 CSS 媒体查询和 JavaScript 事件绑定，确保移动端适配正常工作。

## 📞 技术支持

如果你在使用过程中遇到问题：

1. 查看本文档的常见问题部分
2. 提供详细的错误信息和复现步骤

---

**享受与 AI 的对话体验！** 🎉