# 前端统一改造落地指南

本包包含：
- `styles/theme.css`：统一 Design Token（颜色、圆角、间距、阴影、排版）+ 可复用样式（IconButton / ChatBubble / Markdown）
- `components/chat/ChatBubble.vue`：左右两类气泡
- `components/chat/MarkdownRenderer.vue`：Markdown + sanitize + 代码高亮 + 复制按钮 + KaTeX + Mermaid（按需加载）
- `components/chat/ThinkingSection.vue`：思考过程折叠区（可展示耗时）
- `components/chat/FilePreviewList.vue`：统一文件预览卡片

## 1. 安装依赖（若项目未安装）
```bash
npm i marked highlight.js dompurify mermaid katex
# or
pnpm add marked highlight.js dompurify mermaid katex
```

## 2. 引入全局样式
在 `main.ts` 或 `App.vue` 里引入：
```ts
import '@/styles/theme.css'
```

（可选）Ant Design Vue 统一 Token：
```vue
<a-config-provider
  :theme="{ token: { colorPrimary: 'var(--brand)', borderRadius: 10, colorText: 'var(--text-1)', colorBgLayout: 'var(--bg-1)' } }"
>
  <router-view />
</a-config-provider>
```

## 3. 替换 Message 渲染路径
将原 `Message.vue` 内的 Markdown 解析/表格/代码高亮/mermaid 逻辑，替换为：
```vue
<ChatBubble :role="msg.role">
  <MarkdownRenderer :content="msg.content" />
  <ThinkingSection v-if="msg.thinking" :durationMs="msg.durationMs">
    <MarkdownRenderer :content="msg.thinking" />
  </ThinkingSection>
  <FilePreviewList :files="msg.files" @preview="onPreview" />
</ChatBubble>
```
> 其余点赞/复制/再生成等操作按钮保持不变。

## 4. 统一输入区与滚动到底按钮
- 输入框、主按钮高度 40px，采用 `--radius-md`
- “滚动到底”按钮使用 `.icon-btn`，相对消息容器 `position:absolute; right:16px; bottom:16px;`

## 5. 启用暗黑模式
在根元素切换：
```js
document.documentElement.setAttribute('data-theme', 'dark') // or 'light'
```

## 6. 可选性能优化
- 聊天消息使用虚拟列表（如 vue-virtual-scroller）
- mermaid 懒渲染已内建；图片使用懒加载 `loading="lazy"`

## 7. 可访问性
- `.icon-btn` 可聚焦；为纯图标按钮添加 `aria-label`
- 图片加 `alt`；弹层聚焦回退

## 8. 渐进式改造顺序（建议）
1) 引入 `theme.css`（不破坏功能，立刻统一大部分视觉）
2) 把 `Message.vue` 的 markdown 渲染换成 `MarkdownRenderer`
3) 引入 `ChatBubble` 和 `ThinkingSection`
4) 统一 Sidebar 选中态/空状态/按钮样式
5) 替换知识库 & 文件页的卡片和表格样式（复用 token）

完成以上步骤后，整体观感将显著一致，同时保留你现有的业务逻辑。
