// UTF-8
// 说明：Markdown 渲染、代码高亮、流程图与公式渲染等工具函数
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import python from 'highlight.js/lib/languages/python'
import xml from 'highlight.js/lib/languages/xml'
import 'highlight.js/styles/github.css'
import mermaid from 'mermaid'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// 极简 HTML 净化函数（建议后续引入 DOMPurify 做全面净化）
// 目的：移除 <script> 与内联事件处理器 on*，降低 XSS 风险
const sanitizeHtml = (html = '') => {
  try {
    return html
      .replace(/<\s*script[^>]*>[\s\S]*?<\s*\/\s*script\s*>/gi, '') // 去掉 script 标签
      .replace(/on[a-zA-Z]+\s*=\s*"[^"]*"/g, '') // 去掉 on*="..."
      .replace(/on[a-zA-Z]+\s*=\s*'[^']*'/g, '') // 去掉 on*='...'
      .replace(/on[a-zA-Z]+\s*=\s*[^\s>]+/g, '') // 去掉 on*=无引号
  } catch { return html }
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

// register a minimal set of languages for highlight.js
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('python', python)
hljs.registerLanguage('xml', xml)

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (__) {}
    }
    return ''
  }
})

// 渲染Markdown内容的函数（含基本净化）
export const renderMarkdown = (content) => {
  // 预处理：处理思考标签 <think></think>
  const processedContent = content.replace(
    /<think>([\s\S]*?)<\/think>/gi,
    '<div class="ai-thinking">💭 <strong>思考过程：</strong><br>$1</div>'
  )
  
  // 渲染Markdown
  let renderedHTML = md.render(processedContent)
  
  // 后处理：修复图片链接
  // 从环境变量获取Dify API URL并提取基础URL（不包含/v1）
  const difyApiUrl = import.meta.env.VITE_DIFY_API_URL || 'https://api.dify.ai/v1'
  const difyBaseUrl = difyApiUrl.replace(/\/v1$/, '') // 移除末尾的/v1
  
  // 替换所有以/files/开头的相对路径图片链接
  renderedHTML = renderedHTML.replace(
    /src="\/files\//g,
    `src="${difyBaseUrl}/files/`
  )
  
  // 渲染LaTeX公式
  renderedHTML = renderLatex(renderedHTML)
  
  // 渲染Mermaid流程图
  renderedHTML = renderMermaid(renderedHTML)
  
  // 增强表格样式
  renderedHTML = renderForms(renderedHTML)

  // 基本净化
  renderedHTML = sanitizeHtml(renderedHTML)

  return renderedHTML
}

// 渲染LaTeX公式
const renderLatex = (html) => {
  // 处理行内公式：$...$
  html = html.replace(/\$(.*?)\$/g, (match, formula) => {
    try {
      return katex.renderToString(formula, {
        throwOnError: false,
        displayMode: false
      })
    } catch (e) {
      console.error('KaTeX error:', e)
      return match
    }
  })
  
  // 处理块级公式：$$...$$
  html = html.replace(/\$\$(.*?)\$\$/gs, (match, formula) => {
    try {
      return katex.renderToString(formula, {
        throwOnError: false,
        displayMode: true
      })
    } catch (e) {
      console.error('KaTeX error:', e)
      return match
    }
  })
  
  return html
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

// 渲染表单（增强表格样式）
const renderForms = (html) => {
  // 为表格添加特殊样式类
  html = html.replace(/<table>/g, '<table class="markdown-table">')
  return html
}

// 渲染所有Mermaid图表（需要在组件中调用）
export const renderMermaidDiagrams = () => {
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
}

export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    console.error('Failed to copy text: ', err)
    return false
  }
}

// 导出净化工具，供其它组件二次防护
export { sanitizeHtml }

export const formatTime = (date) => {
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export const generateId = () => {
  return Math.random().toString(36).substr(2, 9)
}

export const debounce = (func, wait) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}
