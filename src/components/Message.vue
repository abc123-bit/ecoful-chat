<template>
  <div :class="['message', message.role]">
    <div class="message-avatar">
      <UserOutlined v-if="message.role === 'user'" />
      <RobotOutlined v-else />
    </div>

    <div class="message-content">
      <!-- 用户消息部分 -->
      <div v-if="message.role === 'user'" class="user-content">
        <div class="user-message-display">
          <div class="user-text">
            {{ message.content }}
          </div>

          <!-- 文件预览部分 -->
          <div v-if="message.files && message.files.length > 0" class="message-files">
            <div v-for="(file, index) in message.files" :key="index" class="file-preview">
              <div v-if="isImage(file)" class="image-preview">
                <img :src="getObjectURL(file)" :alt="file.name" @load="revokeObjectURL($event.target.src)" />
                <span class="file-name">{{ file.name }}</span>
              </div>
              <div v-else class="file-info">
                <FileOutlined />
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">({{ formatFileSize(file.size) }})</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮放在消息下方 -->
        <div class="message-actions-bottom">
          <a-tooltip title="复制">
            <button class="action-btn" @click="handleCopy">
              <CopyOutlined />
            </button>
          </a-tooltip>

        <a-tooltip title="编辑并重新发送">
            <button class="action-btn" @click="handleEdit">
              <EditOutlined />
            </button>
          </a-tooltip>
        </div>
      </div>

      <!-- AI助手消息部分 -->
      <div v-else class="assistant-content">
        <!--加载中且无内容时显示加载动画 -->
        <div v-if="message.role === 'assistant' && message.isStreaming && !message.content" class="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>

        <div v-else>
          <!-- 正常回答内容 -->

          <!-- 添加公式、流程图和表单的渲染（已做基础净化） -->
          <div class="markdown-content" v-html="renderedContent"></div>

          <!-- 思考过程部分 -->
          <div v-if="message.thinking" class="thinking-section">
            <div class="thinking-header" @click="toggleThinking">
              <span class="thinking-title">已深度思考（用时 {{ thinkingTime }} 秒）</span>
              <span class="thinking-toggle">
                {{ showThinking ? '收起' : '展开' }}
                <CaretDownOutlined :class="['toggle-icon', { rotated: showThinking }]" />
              </span>
            </div>

            <transition name="slide">
              <div v-if="showThinking" class="thinking-content">
                <div class="thinking-text">{{ message.thinking }}</div>
              </div>
            </transition>
          </div>
        </div>

        <!-- 操作按钮放在消息下方 -->
        <div v-if="message.role === 'assistant' && message.content && feedbackEnabled" class="message-actions-bottom">
          <a-tooltip title="复制">
            <button class="action-btn" @click="handleCopy">
              <CopyOutlined />
            </button>
          </a-tooltip>

          <a-tooltip title="点赞">
            <button :class="['action-btn', { active: message.liked }]" @click="handleLike">
              <LikeOutlined />
            </button>
          </a-tooltip>

          <a-tooltip title="点踩">
            <button :class="['action-btn', { active: message.disliked }]" @click="handleDislike">
              <DislikeOutlined />
            </button>
          </a-tooltip>
        </div>
      </div>

      <div class="message-time">
        {{ formattedTime }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import mermaid from 'mermaid'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  UserOutlined,
  RobotOutlined,
  CopyOutlined,
  LikeOutlined,
  DislikeOutlined,
  EditOutlined,
  CaretDownOutlined,
  FileOutlined
} from '@ant-design/icons-vue'
import { renderMarkdown, formatTime, sanitizeHtml } from '@/utils/helpers'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  // 是否启用点赞/点踩按钮（由 Provider 能力控制）
  feedbackEnabled: { type: Boolean, default: true },
})

// 事件定义
const emit = defineEmits(['copy', 'like', 'dislike', 'edit-message'])
const showThinking = ref(false)
const objectURLs = ref([]) // 用于存储生成的URL对象

const renderedContent = computed(() => {
  if (props.message.role === 'assistant' && props.message.content) {
    // 使用增强的Markdown渲染函数
    return renderEnhancedMarkdown(props.message.content)
  }
  return ''
})

const formattedTime = computed(() => {
  const ts = props.message?.timestamp
  if (!ts) return ''
  const date = ts instanceof Date ? ts : new Date(ts)
  if (Number.isNaN(date.getTime())) return ''
  return formatTime(date)
})

// 添加渲染增强Markdown的函数
const renderEnhancedMarkdown = (content) => {
  let html = renderMarkdown(content); // 第一步：Markdown → HTML（内部已做基础净化）
  html = renderLatex(html);           // 第二步：渲染所有 LaTeX（包括表格内）
  html = renderForms(html);           // 第三步：为表格添加样式类
  html = renderMermaid(html);         // 第四步：渲染流程图（若有）
  // 兜底再净化一次，尽量降低 XSS 风险
  return sanitizeHtml(html);
}

// 渲染LaTeX公式
const renderLatex = (html) => {
  // 1. 优先处理「块级公式」$$...$$（避免与行内公式 $ 冲突）
  html = html.replace(/\$(.*?)\$/g, (match, formula) => {
    try {
      return katex.renderToString(formula.trim(), {
        throwOnError: false, // 容忍语法小错误
        displayMode: false,  // 行内公式（与文字同行）
        strict: "ignore",    // 支持非严格 LaTeX 语法
        output: "html"       // 输出 HTML 格式
      });
    } catch (e) {
      console.error('KaTeX 行内公式错误:', e);
      return match; // 渲染失败时保留原内容
    }
  });

  // 2. 处理「行内公式」$...$
  html = html.replace(/\$(.*?)\$/g, (match, formula) => {
    try {
      return katex.renderToString(formula.trim(), {
        throwOnError: false,
        displayMode: false,  // 行内公式（与文字同行）
        strict: "ignore",
        output: "html"
      });
    } catch (e) {
      console.error('KaTeX 行内公式错误:', e);
      return match;
    }
  });

  // 3. 兼容「[] 格式公式」（若仍有需求，可选保留；建议逐步迁移为 $/$$ 格式）
  html = html.replace(/\[([\s\S]*?)\]/g, (match, formula) => {
    try {
      const isBlock = formula.includes('\n');
      return katex.renderToString(formula.trim(), {
        throwOnError: false,
        displayMode: isBlock,
        strict: "ignore",
        output: "html"
      });
    } catch (e) {
      console.error('KaTeX [] 格式公式错误:', e);
      return match;
    }
  });

  // 4. 再次处理「块级公式」$$...$$（确保所有块级公式均被渲染）
  html = html.replace(/\$\$(.*?)\$\$/gs, (match, formula) => {
    try {
      return katex.renderToString(formula.trim(), {
        throwOnError: false, // 容忍小语法错误
        displayMode: true,   // 块级公式（居中、大尺寸）
        strict: "ignore"     // 支持非严格 LaTeX 语法
      });
    } catch (e) {
      console.error('KaTeX 块级公式错误:', e);
      return match; // 渲染失败时保留原内容
    }
  });

  return html;
}

// 渲染Mermaid流程图
const renderMermaid = (html) => {
  // 查找所有mermaid代码块
  const mermaidRegex = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g
  html = html.replace(mermaidRegex, (match, diagramCode) => {
    const id = 'mermaid-' + Math.random().toString(36).substr(2, 9)
    return `<div class="mermaid-diagram" id="${id}" data-code="${encodeURIComponent(diagramCode)}">正在渲染图表...</div>`
  })

  return html
}

// 渲染表单（如果需要特殊样式）
const renderForms = (html) => {
  // 为所有 <table> 标签添加「自定义样式类」
  html = html.replace(/<table>/gi, '<table class="styled-table">');

  // 修复简易表格结构，生成 <thead>（表头）和 <tbody>（内容）
  html = html.replace(
    /(\|.*?\|.*?)\n\|[-–]+(?:\|[-–]+)*\n([\s\S]*?)(?=\n|$)/gs,
    (match, headerRow, contentRows) => {
      if (!match.includes('<table>')) {
        // 解析表头
        const headers = headerRow
          .trim()
          .split('|')
          .filter(h => h.trim() !== '');
        const headerHtml = headers
          .map(h => `<th>${h.trim()}</th>`)
          .join('');

        // 解析表内容行
        const rows = contentRows
          .trim()
          .split('\n')
          .filter(row => row.trim() !== '')
          .map(row => {
            const cells = row
              .trim()
              .split('|')
              .filter(c => c.trim() !== '');
            return `<td>${cells.map(c => c.trim()).join('</td><td>')}</td>`;
          })
          .map(cellHtml => `<tr>${cellHtml}</tr>`)
          .join('');

        // 生成标准表格结构
        return `
          <table class="styled-table">
            <thead>
              <tr>${headerHtml}</tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        `;
      }
      return match;
    }
  );

  return html;
}

// 初始化Mermaid配置
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  flowchart: {
    useMaxWidth: false,
    htmlLabels: true,
    curve: 'basis'
  }
})

// 渲染所有Mermaid图表
const renderMermaidDiagrams = () => {
  nextTick(() => {
    const diagrams = document.querySelectorAll('.mermaid-diagram')
    diagrams.forEach(diagram => {
      const code = decodeURIComponent(diagram.getAttribute('data-code'))
      try {
        mermaid.render(
          diagram.id,
          code,
          (svgCode) => {
            diagram.innerHTML = svgCode
          }
        )
      } catch (e) {
        console.error('Mermaid rendering error:', e)
        diagram.innerHTML = `<div class="mermaid-error">图表渲染失败: ${e.message}</div>`
      }
    })
  })
}

// 计算思考时间（假设消息对象中有thinkingTime字段）
const thinkingTime = computed(() => {
  return props.message.thinkingTime || 0
})

// 切换思考过程显示
const toggleThinking = () => {
  showThinking.value = !showThinking.value
}

// 复制用户消息
const handleCopy = () => {
  emit('copy', props.message.content)
}

// 编辑消息（将内容放入主输入框）
const handleEdit = () => {
  emit('edit-message', {
    content: props.message.content,
    files: props.message.files || []
  })
}

const handleLike = () => {
  emit('like')
}

const handleDislike = () => {
  emit('dislike')
}

// 检查文件是否为图片
const isImage = (file) => {
  return file.type.startsWith('image/')
}

// 生成对象URL
const getObjectURL = (file) => {
  const url = URL.createObjectURL(file)
  objectURLs.value.push(url)
  return url
}

// 释放对象URL
const revokeObjectURL = (url) => {
  URL.revokeObjectURL(url)
  objectURLs.value = objectURLs.value.filter(u => u !== url)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 监听消息内容变化以重新渲染图表
watch(renderedContent, () => {
  renderMermaidDiagrams()
})

// 组件挂载时渲染图表
onMounted(() => {
  renderMermaidDiagrams()
})

// 组件卸载时释放所有对象URL（现有代码保持不变）
onUnmounted(() => {
  objectURLs.value.forEach(url => URL.revokeObjectURL(url))
  objectURLs.value = []
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 12px;
  position: relative;
}

.message.user .message-content {
  background-color: #CED3F7;
  color: rgb(0, 0, 0);
  order: 1;
}

.message.user {
  margin-left: 60px;
}

.message.assistant {
  background: white;
  border: 1px solid #e5e7eb;
  margin-right: 60px;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #1677ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.message.assistant .message-avatar {
  background: #10A37F;
}

.message-content {
  min-width: 0;
}

.user-content {
  position: relative;
  width: 100%;
}

.user-message-display {
  width: 100%;
}

.user-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.5;
  font-size: 14px;
  margin-bottom: 8px;
}

/* 文件预览样式 */
.message-files {
  margin-top: 8px;
}

.file-preview {
  margin-bottom: 8px;
  padding: 8px;
  background-color: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
  display: block;
  margin-bottom: 4px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-size: 12px;
  color: #666;
}

.file-size {
  font-size: 11px;
  color: #999;
}

/* 操作按钮放在底部 */
.message-actions-bottom {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  justify-content: flex-end;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  color: #666;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.action-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #1890ff;
}

.action-btn.active {
  color: #1677ff;
  background: rgba(22, 119, 255, 0.1);
}

.assistant-content {
  position: relative;
  width: 100%;
}

.loading-dots {
  padding: 12px 0;
}

.loading-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
  margin: 0 3px;
  animation: loading 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loading {

  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}

/* 思考过程样式 */
.thinking-section {
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  cursor: pointer;
  transition: background-color 0.2s;
}

.thinking-header:hover {
  background: #e9ecef;
}

.thinking-title {
  font-weight: 600;
  color: #495057;
  font-size: 14px;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6c757d;
  font-size: 12px;
}

.toggle-icon {
  transition: transform 0.3s ease;
  font-size: 12px;
}

.toggle-icon.rotated {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 16px;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.thinking-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
  color: #6c757d;
  font-size: 13px;
  font-style: italic;
}

/* 展开收起动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.markdown-content {
  line-height: 1.6;
}

.message-time {
  font-size: 12px;
  color: #8e8ea0;
  margin-top: 8px;
  text-align: right;
}

/* Markdown 内容样式 */
.markdown-content :deep(p) {
  margin: 8px 0;
}

.markdown-content :deep(pre) {
  background: #f6f8fa;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(code) {
  background: #f6f8fa;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #d0d7de;
  padding-left: 16px;
  margin: 12px 0;
  color: #656d76;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 24px;
  margin: 8px 0;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin: 16px 0 8px 0;
  font-weight: 600;
}

.markdown-content :deep(a) {
  color: #1677ff;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 12px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  margin: 12px 0;
  width: 100%;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #d0d7de;
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f6f8fa;
  font-weight: 600;
}

.mermaid-diagram {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  overflow: auto;
  border: 1px solid #e5e7eb;
}

.mermaid-error {
  color: #dc2626;
  padding: 16px;
  background: #fef2f2;
  border-radius: 6px;
  font-size: 14px;
}

/* 增强Markdown内容样式 */
.enhanced-markdown-content {
  line-height: 1.6;
}

/* 公式样式 */
.enhanced-markdown-content :deep(.katex) {
  font-size: 1.1em;
}

.enhanced-markdown-content :deep(.katex-display) {
  margin: 1em 0;
  overflow: auto hidden;
}

.enhanced-markdown-content :deep(.katex-display > .katex) {
  display: inline-block;
  text-align: center;
}

/* 表格样式 */
.enhanced-markdown-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.enhanced-markdown-content :deep(.markdown-table th) {
  background: #f8f9fa;
  font-weight: 600;
  text-align: left;
}

.enhanced-markdown-content :deep(.markdown-table th),
.enhanced-markdown-content :deep(.markdown-table td) {
  padding: 12px;
  border: 1px solid #e5e7eb;
}

.enhanced-markdown-content :deep(.markdown-table tr:nth-child(even)) {
  background: #f9fafb;
}

/* ========== KaTeX 公式样式 ========== */
.katex {
  font-size: 1.05em !important;
  /* 公式整体大小（根据设计调整） */
  color: #333;
  /* 公式文字颜色 */
}

.katex-display {
  text-align: center !important;
  /* 块级公式居中 */
  margin: 16px 0;
  /* 块级公式上下间距 */
}


/* ========== 表格样式 ========== */
.styled-table {
  width: 100%;
  border-collapse: separate;
  /* 分离边框，用于实现圆角 */
  border-spacing: 0;
  border: 1px solid #eaeaea;
  /* 表格外边框 */
  border-radius: 8px;
  /* 表格整体圆角 */
  overflow: hidden;
  /* 确保圆角生效（隐藏内部溢出） */
  margin: 16px 0;
  /* 表格上下间距 */
  font-size: 14px;
}

.styled-table th,
.styled-table td {
  padding: 10px 12px;
  /* 单元格内边距 */
  text-align: left;
  /* 文字左对齐 */
  border-bottom: 1px solid #eaeaea;
  /* 单元格底部分隔线 */
}

.styled-table th {
  background-color: #f7f7f7;
  /* 表头背景色 */
  font-weight: 600;
  /* 表头字体加粗 */
  border-top: none;
  /* 取消表头顶边框（与外边框合并） */
}

.styled-table td {
  border-top: none;
  /* 取消单元格顶边框（与外边框合并） */
}

.styled-table tr:last-child td {
  border-bottom: none;
  /* 取消最后一行的底边框 */
}

.styled-table tr:hover {
  background-color: #fafafa;
  /* 鼠标悬浮时，行背景色变化 */
}
</style>
