<template>
  <a-layout class="rag-chat-container">
    <!-- 左侧边栏（桌面/中屏：固定列；小屏：用 Drawer 展示） -->
    <a-layout-sider width="300" class="kbq-sider" theme="light">
      <div class="sidebar-header">
        <div class="app-logo">
          <robot-outlined />
          <h2>智能知识库</h2>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-title">
          <span class="title-text">知识库选择</span>
        </div>
        <a-select v-model:value="state.kbId" :options="kbOptions" :disabled="!!props.kbId" show-search
          placeholder="请选择知识库" class="kb-selector" size="large" @change="onKbChange">
          <template #suffixIcon><search-outlined /></template>
        </a-select>
        <div v-if="props.kbId" class="locked-tip">
          <info-circle-outlined />
          <span>当前知识库已锁定</span>
        </div>
      </div>

      <a-divider class="sidebar-divider" />

      <div class="sidebar-section">
        <div class="section-title">
          <span class="title-text">会话列表</span>
          <a-tooltip title="刷新列表">
            <a-button type="text" shape="circle" size="small" @click="reloadConversations" class="refresh-btn">
              <sync-outlined :spin="loading.conversations" />
            </a-button>
          </a-tooltip>
        </div>

        <div class="conversations-list">
          <a-list :data-source="conversations" :loading="loading.conversations" class="conv-list"
            :locale="{ emptyText: '暂无会话历史' }">
            <template #renderItem="{ item }">
              <a-list-item class="conv-item" :class="{ 'active': item.session_id === state.conversationId }"
                @click="openConversation(item)">
                <a-list-item-meta>
                  <template #title>
                    <div class="conv-title">
                      <message-outlined />
                      {{ item.title || `会话 ${item.session_id?.slice(0, 8)}` }}
                    </div>
                  </template>
                  <template #description>
                    <div class="conv-time">
                      {{ formatTime(item.updated_at || item.created_at) }}
                    </div>
                  </template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </div>

        <a-button type="primary" block @click="newConversation" class="new-chat-btn" size="large">
          <template #icon><plus-outlined /></template>
          新建对话
        </a-button>
      </div>
    </a-layout-sider>
    <!-- 小屏抽屉（替代侧栏，不占位） -->
    <a-drawer
      placement="left"
      :open="mobileSidebarOpen"
      :width="drawerWidth"
      :bodyStyle="{ padding: '0' }"
      :maskClosable="true"
      @close="mobileSidebarOpen=false"
    >
      <div class="kbq-drawer">
        <div class="sidebar-header">
          <div class="app-logo">
            <robot-outlined />
            <h2>智能知识库</h2>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="section-title">
            <span class="title-text">知识库选择</span>
          </div>
          <a-select v-model:value="state.kbId" :options="kbOptions" :disabled="!!props.kbId" show-search
            placeholder="请选择知识库" class="kb-selector" size="large" @change="onKbChange">
            <template #suffixIcon><search-outlined /></template>
          </a-select>
          <div v-if="props.kbId" class="locked-tip">
            <info-circle-outlined />
            <span>当前知识库已锁定</span>
          </div>
        </div>

        <a-divider class="sidebar-divider" />

        <div class="sidebar-section">
          <div class="section-title">
            <span class="title-text">会话列表</span>
            <a-tooltip title="刷新列表">
              <a-button type="text" shape="circle" size="small" @click="reloadConversations" class="refresh-btn">
                <sync-outlined :spin="loading.conversations" />
              </a-button>
            </a-tooltip>
          </div>

          <div class="conversations-list">
            <a-list :data-source="conversations" :loading="loading.conversations" class="conv-list"
              :locale="{ emptyText: '暂无会话历史' }">
              <template #renderItem="{ item }">
                <a-list-item class="conv-item" :class="{ 'active': item.session_id === state.conversationId }"
                  @click="openConversation(item)">
                  <a-list-item-meta>
                    <template #title>
                      <div class="conv-title">
                        <message-outlined />
                        {{ item.title || `会话 ${item.session_id?.slice(0, 8)}` }}
                      </div>
                    </template>
                    <template #description>
                      <div class="conv-time">
                        {{ formatTime(item.updated_at || item.created_at) }}
                      </div>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </div>

          <a-button type="primary" block @click="newConversation" class="new-chat-btn" size="large">
            <template #icon><plus-outlined /></template>
            新建对话
          </a-button>
        </div>
      </div>
    </a-drawer>

    <!-- 中间聊天区域 -->
    <a-layout class="chat-area">
      <div class="chat-header">
        <div class="header-left">
          <!-- 移动端打开侧栏按钮 -->
          
          <div class="chat-title">
            <h2 v-if="currentKb">{{ currentKb.name }}</h2>
            <h2 v-else>知识库对话</h2>
            <a-tag v-if="currentKb" color="blue" class="kb-tag">
              <database-outlined />
              {{ currentKb.file_count || 0 }} 个文档
            </a-tag>
          </div>
        </div>

        <div class="header-actions">
          <div class="retrieval-config">
            <span class="config-label">召回数量:</span>
            <a-select v-model:value="state.maxChunks" size="small" class="chunk-selector">
              <a-select-option :value="4">4</a-select-option>
              <a-select-option :value="6">6</a-select-option>
              <a-select-option :value="8">8</a-select-option>
              <a-select-option :value="12">12</a-select-option>
            </a-select>
          </div>

          <a-button @click="newConversation" class="action-btn primary">
            <template #icon><plus-outlined /></template>新会话
          </a-button>
          <a-button danger :disabled="!abortController" @click="stop" class="action-btn">
            <template #icon><pause-outlined /></template>停止生成
          </a-button>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-container" ref="messagesEl">
        <a-empty v-if="!messages.length && !loading.messages" description="开始一段对话吧！" class="empty-chat">
          <template #image>
            <div class="empty-icon">
              <comment-outlined />
            </div>
          </template>
          <div class="empty-tips">
            <p>选择知识库后即可开始对话</p>
            <p class="tip-small">您可以提问关于知识库内容的任何问题</p>
          </div>
        </a-empty>

        <div v-else class="messages-list">
          <div v-for="(m, idx) in messages" :key="idx" class="message" :class="'message--' + m.role">
            <div class="message-avatar">
              <div v-if="m.role === 'user'" class="avatar-user">
                <user-outlined />
              </div>
              <div v-else class="avatar-ai">
                <robot-outlined />
              </div>
            </div>

            <div class="message-content">
              <div class="message-bubble" :class="'bubble--' + m.role">
                <div class="message-text" v-html="renderMarkdown(m.content)"></div>

                <div v-if="m.role === 'assistant' && Array.isArray(m.sources) && m.sources.length"
                  class="sources-section">
                  <a-collapse :bordered="false" ghost>
                    <a-collapse-panel :header="`参考来源 (${m.sources.length})`" key="1" class="sources-header">
                      <a-list :data-source="m.sources" size="small">
                        <template #renderItem="{ item, index }">
                          <a-list-item class="source-item">
                            <file-text-outlined />
                            <a class="source-name" href="javascript:void(0)" @click.prevent="openSource(item)"
                              :title="item.filename || item.title || item.source_file || item.url || `来源 ${index + 1}`">
                              {{ item.filename || item.title || item.source_file || item.url || `来源 ${index + 1}` }}
                            </a>
                          </a-list-item>
                        </template>
                      </a-list>
                    </a-collapse-panel>
                  </a-collapse>
                </div>
              </div>
            </div>
          </div>

          <!-- 加载指示器 -->
          <div v-if="loading.stream" class="typing-indicator">
            <div class="typing-avatar">
              <robot-outlined />
            </div>
            <div class="typing-bubble">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span class="typing-text">AI正在思考...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-container">
        <div class="input-box">
          <a-textarea v-model:value="state.input" :auto-size="{ minRows: 1, maxRows: 4 }"
            :disabled="!state.kbId || loading.stream" placeholder="输入您的问题..." @keydown.enter.exact.prevent="send"
            class="chat-input" />
          <a-button type="primary" @click="send" :disabled="!state.kbId || !state.input.trim() || loading.stream"
            class="send-btn" size="large">
            <template #icon><send-outlined /></template>
          </a-button>
        </div>
        <div class="input-tips">
          <span>按 Enter 发送，Shift + Enter 换行</span>
        </div>
      </div>
    </a-layout>

    <!-- 右侧预览 Sider -->
    <a-layout-sider :width="preview.visible ? 520 : 0" class="preview-sider" theme="light" collapsible
      :collapsed="!preview.visible" :collapsedWidth="0">
      <div class="preview-header">
        <div class="preview-title">
          <file-text-outlined />
          <span class="title-text">{{ preview.filename || '参考来源预览' }}</span>
          <a-tag v-if="preview.viewer" class="viewer-tag" color="geekblue">{{ preview.viewer }}</a-tag>
        </div>
        <div class="preview-actions">
          <a-button type="link" size="small" @click="openInNewTab" :disabled="!preview.url" class="action-link">
            新窗口打开
          </a-button>
          <a-button type="text" size="small" @click="closePreview" class="close-btn">
            关闭
          </a-button>
        </div>
      </div>

      <div class="preview-body">
        <div v-if="!preview.url" class="preview-placeholder">
          <file-text-outlined class="placeholder-icon" />
          <p>点击左侧"参考来源"以在此预览</p>
        </div>

        <!-- 图片 -->
        <div v-else-if="preview.viewer === 'image'" class="preview-content image-wrapper">
          <img :src="preview.objectUrl || preview.url" alt="预览图片" />
        </div>

        <!-- Markdown -->
        <div v-else-if="preview.viewer === 'markdown'" class="preview-content md-wrapper" v-html="preview.html"></div>

        <!-- JSON / 文本 -->
        <pre v-else-if="preview.viewer === 'json' || preview.viewer === 'text'"
          class="preview-content code-block">{{ preview.text }}</pre>

        <!-- Excel：多表预览 -->
        <div v-else-if="preview.viewer === 'excel'" class="preview-content excel-wrapper">
          <a-tabs type="card" size="small">
            <a-tab-pane v-for="(sheet, i) in preview.sheets" :key="i" :tab="sheet.name || ('Sheet' + (i + 1))">
              <div class="sheet-html" v-html="sheet.html"></div>
            </a-tab-pane>
          </a-tabs>
        </div>

        <!-- Word：docx-preview 渲染容器 -->
        <div v-else-if="preview.viewer === 'word'" ref="docxEl" class="preview-content docx-wrapper"></div>

        <!-- HTML 文件 -->
        <div v-else-if="preview.viewer === 'html'" class="preview-content html-wrapper" v-html="preview.html"></div>

        <!-- PDF / 其它兜底（iframe） -->
        <iframe v-else :src="preview.url" class="preview-iframe" referrerpolicy="no-referrer"></iframe>
      </div>
    </a-layout-sider>
  </a-layout>
</template>

<script setup>
// 原有JavaScript代码完全保持不变
import {
  SearchOutlined, InfoCircleOutlined, SyncOutlined, MessageOutlined, PlusOutlined,
  DatabaseOutlined, PauseOutlined, CommentOutlined, UserOutlined, RobotOutlined,
  FileTextOutlined, SendOutlined, MenuOutlined
} from '@ant-design/icons-vue'

import { onMounted, onBeforeUnmount, ref, reactive, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import KnowledgeBaseService from '@/services/knowledgeBase'

// 新增依赖：docx-preview、xlsx、markdown-it
import { renderAsync as renderDocx } from 'docx-preview'
import * as XLSX from 'xlsx'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, breaks: true, linkify: true })
// 小屏抽屉宽度计算（避免直接在模板用 window）
const drawerWidth = ref(320)

const props = defineProps({ kbId: { type: Number, default: null } })
import { useRoute } from 'vue-router'
const route = useRoute()
const routeConversationId = ref(null)
const kbOptions = ref([])
const currentKb = ref(null)
const conversations = ref([])
const messages = ref([])
const messagesEl = ref(null)

const loading = reactive({ kbs: false, conversations: false, messages: false, stream: false })

// 组件状态
const state = reactive({
  kbId: props.kbId || null,
  conversationId: null,
  input: '',
  maxChunks: 6
})
// 移动端侧栏开关
const mobileSidebarOpen = ref(false)

let abortController = null

// 右侧预览（扩展字段）
const docxEl = ref(null)
const preview = reactive({
  visible: false,
  url: '',
  filename: '',
  mime: '',
  ext: '',
  viewer: '',      // 'pdf' | 'image' | 'markdown' | 'json' | 'text' | 'excel' | 'word' | 'html' | 'iframe'
  objectUrl: '',   // blob 本地 URL
  text: '',        // 文本/JSON 原文
  html: '',        // 渲染后的 HTML（md/html/xlsx表格）
  sheets: []       // Excel 多表
})

// 监听 kbId 变化（外部传入时）
watch(() => props.kbId, (v) => {
  if (v && v !== state.kbId) {
    state.kbId = v
    onKbChange()
  }
})

// 初始化
onMounted(async () => {
  await initKbOptions()
  if (state.kbId) {
    await loadKbDetail(state.kbId)
    await reloadConversations()
  }
  // 如果路由中带有会话 ID，则直接加载该会话
  try {
    const conv = route?.query?.conversation
    if (conv) {
      state.conversationId = String(conv)
      await loadMessages(state.conversationId)
    }
  } catch {}
  // 初始化抽屉宽度（小屏为 84vw，最大 360px）
  const w = typeof window !== 'undefined' ? window.innerWidth : 1200
  drawerWidth.value = Math.min(Math.round(w * 0.84), 360)
})

// 卸载时清理
onBeforeUnmount(() => {
  if (abortController) abortController.abort()
  revokeObjectUrl()
})

// 清理 blob URL
function revokeObjectUrl() {
  if (preview.objectUrl) {
    URL.revokeObjectURL(preview.objectUrl)
    preview.objectUrl = ''
  }
}

// 初始化知识库列表
async function initKbOptions() {
  try {
    loading.kbs = true
    const list = await KnowledgeBaseService.getKnowledgeBases()
    kbOptions.value = (list || []).map(k => ({ label: k.name, value: k.id }))
  } catch (e) { message.error('加载知识库列表失败') }
  finally { loading.kbs = false }
}

// 加载知识库详情
async function loadKbDetail(kbId) {
  try { currentKb.value = await KnowledgeBaseService.getKnowledgeBase(kbId) }
  catch { currentKb.value = null }
}

// 知识库切换
async function onKbChange() {
  state.conversationId = null
  messages.value = []
  closePreview()
  await loadKbDetail(state.kbId)
  await reloadConversations()
  mobileSidebarOpen.value = false
}

// 格式化时间
function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString()
}

// 标准化来源字段（兼容不同接口返回的字段差异） 
function normalizeSources(x) {
  if (!x) return []
  if (Array.isArray(x.sources_file_detail) && x.sources_file_detail.length) return x.sources_file_detail
  if (Array.isArray(x.source_files) && x.source_files.length) return x.source_files
  if (Array.isArray(x.sources) && x.sources.length && x.sources[0]?.file_id != null) return x.sources
  return []
}

// 重新加载会话列表
async function reloadConversations() {
  if (!state.kbId) return
  try {
    loading.conversations = true
    conversations.value = await KnowledgeBaseService.getConversations(state.kbId)
  } catch (e) { message.error('加载会话列表失败') }
  finally { loading.conversations = false }
}

// 打开会话，加载历史消息
async function openConversation(conv) {
  state.conversationId = conv.session_id || conv.id
  await loadMessages(state.conversationId)
  mobileSidebarOpen.value = false
}

// 加载历史消息
async function loadMessages(conversationId) {
  try {
    loading.messages = true
    const list = await KnowledgeBaseService.getConversationMessages(conversationId)
    messages.value = (list || []).map(m => ({
      role: m.role,
      content: m.content,
      sources: Array.isArray(m.source_files) ? m.source_files : []
    }))
    await nextTick(); scrollToBottom()
  } catch (e) { message.error('加载历史消息失败') }
  finally { loading.messages = false }
}

// 新建会话
function newConversation() {
  state.conversationId = null
  messages.value = []
  closePreview()
  mobileSidebarOpen.value = false
}

// 简单的 Markdown 渲染（支持代码块和换行）
function renderMarkdown(text = '') {
  return text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>').replace(/\n/g, '<br/>')
}

/* ------------ 预览相关：打开来源并选择 viewer ------------ */
// 打开参考来源
async function openSource(s) {
  try {
    if (!s?.file_id) {
      if (s?.url) return preparePreview({ url: s.url, filename: s.filename || s.title || s.source_file || '' })
      return message.warning('该来源缺少 file_id，无法打开原文件')
    }
    const { url, filename, mime_type } = await KnowledgeBaseService.getFilePreviewUrl(s.file_id)
    await preparePreview({ url, filename: filename || s.filename || '', mime: mime_type })
  } catch (e) {
    console.error(e)
    message.error('打开原文件失败')
  }
}

// 关闭文件预览
function closePreview() {
  preview.visible = false
  preview.url = ''
  preview.filename = ''
  preview.mime = ''
  preview.ext = ''
  preview.viewer = ''
  preview.html = ''
  preview.text = ''
  preview.sheets = []
  revokeObjectUrl()
}

// 新窗口打开文件
function openInNewTab() {
  if (preview.url) window.open(preview.url, '_blank')
}

// 根据文件名获取扩展名
function getExt(name = '') {
  const m = name.toLowerCase().match(/\.([a-z0-9]+)(?:\?.*)?$/)
  return m ? m[1] : ''
}

// 通过 HEAD 请求获取 MIME 类型
async function sniffMime(url) {
  try {
    const res = await fetch(url, { method: 'HEAD' })
    return res.headers.get('content-type') || ''
  } catch { return '' }
}

// 根据扩展名和 MIME 类型选择合适的 viewer
function chooseViewer({ ext, mime }) {
  const e = ext
  const m = (mime || '').toLowerCase()

  if (m.includes('pdf') || e === 'pdf') return 'pdf'
  if (m.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(e)) return 'image'
  if (e === 'md' || m.includes('text/markdown')) return 'markdown'
  if (e === 'json' || m.includes('application/json')) return 'json'
  if (['txt', 'log', 'csv', 'tsv', 'py', 'js', 'ts', 'yml', 'yaml', 'ini', 'cfg'].includes(e) || m.startsWith('text/')) return 'text'
  if (['xlsx', 'xls'].includes(e) || m.includes('spreadsheet')) return 'excel'
  if (e === 'docx' || m.includes('wordprocessingml')) return 'word'
  if (e === 'html' || e === 'htm' || m.includes('text/html')) return 'html'
  // 其它一律交给 iframe（可能是可内联的预签名链接）
  return 'iframe'
}

// 准备预览（选择 viewer 并加载渲染）
async function preparePreview({ url, filename, mime }) {
  closePreview()
  preview.url = url
  preview.filename = filename
  preview.ext = getExt(filename || url)
  preview.mime = mime || await sniffMime(url)
  preview.viewer = chooseViewer({ ext: preview.ext, mime: preview.mime })


  // PDF 默认按宽度适配并隐藏工具栏，提升可读性
  if (preview.viewer === 'pdf') {
    const hasHash = preview.url.includes('#')
    const pdfParams = 'toolbar=0&navpanes=0&view=FitH'
    preview.url = hasHash ? `${preview.url}&${pdfParams}` : `${preview.url}#${pdfParams}`
  }
  // 针对不同 viewer 拉取并渲染
  try {
    switch (preview.viewer) {
      case 'image': {
        // 直接用原 URL（如需隐藏真实地址，可改用 blob）
        // const blob = await (await fetch(url)).blob(); preview.objectUrl = URL.createObjectURL(blob)
        break
      }
      case 'markdown': {
        const text = await (await fetch(url)).text()
        preview.html = md.render(text || '')
        break
      }
      case 'json': {
        const text = await (await fetch(url)).text()
        try {
          preview.text = JSON.stringify(JSON.parse(text), null, 2)
        } catch {
          preview.text = text  // 非严格 JSON 时退化为原文
        }
        break
      }
      case 'text': {
        preview.text = await (await fetch(url)).text()
        break
      }
      case 'excel': {
        const buf = await (await fetch(url)).arrayBuffer()
        const wb = XLSX.read(buf, { type: 'array' })
        preview.sheets = wb.SheetNames.map(name => {
          const ws = wb.Sheets[name]
          const html = XLSX.utils.sheet_to_html(ws, { id: name, editable: false, header: '', footer: '' })
          return { name, html }
        })
        break
      }
      case 'word': {
        const blob = await (await fetch(url)).blob()
        // docx-preview 需要容器元素
        await nextTick()
        if (docxEl.value) {
          await renderDocx(blob, docxEl.value, undefined, { className: 'docx' })
        }
        break
      }
      case 'html': {
        preview.html = await (await fetch(url)).text()
        break
      }
      // pdf / iframe 直接走 <iframe :src="url">
    }
  } catch (err) {
    console.error('预览渲染失败，回退 iframe：', err)
    preview.viewer = 'iframe'
  }

  preview.visible = true
}

/* ------------------ 对话流逻辑 ------------------ */
// 发送问题并处理流式回答
async function send() {
  const question = (state.input || '').trim()
  if (!state.kbId) return message.warning('请先选择知识库')
  if (!question) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: question })
  const aiMsg = reactive({ role: 'assistant', content: '', sources: [] })
  messages.value.push(aiMsg)
  let renderQueue = '';
  let draining = false;

  // 流式渲染函数
  function drain() {
    if (draining) return;
    draining = true;
    const tick = () => {
      if (!renderQueue.length) { draining = false; return; }
      // 每帧写入 N 个字符；可根据机器性能调整
      const N = 1;
      aiMsg.content += renderQueue.slice(0, N);

      //检验输出
      //console.log('aiMsg:', aiMsg);
      //console.log('len=', aiMsg.content.length, 'snap=', JSON.stringify(aiMsg.content))
      renderQueue = renderQueue.slice(N);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // 清空输入框
  state.input = ''
  await nextTick(); scrollToBottom()

  loading.stream = true
  abortController = new AbortController()
  const payload = {
    knowledge_base_id: state.kbId,
    question,
    conversation_id: state.conversationId || null,
    max_chunks: state.maxChunks
  }

  try {
    await KnowledgeBaseService.askQuestionStream(
      payload,
      (evt) => {
        if (evt?.type === 'start') {
          if (evt.conversation_id) state.conversationId = evt.conversation_id
        } else if (evt?.type === 'content' && typeof evt.content === 'string') {
          renderQueue += evt.content
          drain()
        } else if (evt?.type === 'end') {
          // flush 残留，防止最后几字符卡在 renderQueue 里
          if (renderQueue && renderQueue.length) {
            aiMsg.content += renderQueue
            renderQueue = ''
          }
          aiMsg.sources = normalizeSources(evt)
          loading.stream = false
          abortController = null
        }
        nextTick().then(scrollToBottom)
      },
      abortController
    )
  } catch (e) {
    if (String(e).includes('AbortError')) {
      message.info('已停止生成')
    } else {
      console.error(e)
      try {
        const resp = await KnowledgeBaseService.askQuestion({ ...payload, stream: false })
        aiMsg.content = resp?.answer || '(无内容)'
        aiMsg.sources = normalizeSources(resp)
      } catch (e2) {
        console.error('同步问答也失败:', e2)
        message.error('生成失败')
        messages.value.pop()
      }
    }
    loading.stream = false
    abortController = null
  } finally {
    await nextTick(); scrollToBottom()
  }
}

function stop() {
  if (abortController) {
    abortController.abort()
    abortController = null
    loading.stream = false
  }
}
function scrollToBottom() {
  const el = messagesEl.value
  if (el) el.scrollTop = el.scrollHeight
}
</script>

<style scoped>
/* 全局样式重置和基础变量 */
.rag-chat-container {
  min-height: 100dvh; /* 使用动态视口，改善移动端高度 */
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 左侧边栏样式优化（改用 kbq-sider，避免与全局样式冲突） */
.kbq-sider {
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
  border-right: 1px solid #e1e8ed;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0;
}

.sidebar-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
  background: white;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-logo :deep(svg) {
  font-size: 24px;
  color: #1890ff;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.app-logo h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  background: linear-gradient(135deg, #1f2937 0%, #1890ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar-section {
  padding: 20px 24px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title-text {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.refresh-btn {
  color: #6b7280;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  color: #1890ff;
  background: #f0f7ff;
}

.kb-selector {
  width: 100%;
}

.kb-selector :deep(.ant-select-selector) {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
}

.kb-selector :deep(.ant-select-selector:hover) {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.locked-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.sidebar-divider {
  margin: 0;
  border-color: #f0f0f0;
}

.conversations-list {
  flex: 1;
  overflow: auto;
  margin-bottom: 16px;
}

.conv-list :deep(.ant-list-item) {
  padding: 0;
  border: none;
}

.conv-item {
  padding: 12px 16px;
  margin: 4px 0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.conv-item:hover {
  background: #f8f9fa;
  border-color: #e5e7eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.conv-item.active {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border-color: #1890ff;
}

.conv-item.active .conv-title,
.conv-item.active .conv-time {
  color: white;
}

.conv-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #1f2937;
  transition: color 0.3s ease;
}

.conv-time {
  font-size: 12px;
  color: #6b7280;
  transition: color 0.3s ease;
}

.new-chat-btn {
  border-radius: 12px;
  height: 48px;
  font-weight: 500;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
  transition: all 0.3s ease;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
}

/* 聊天区域样式优化 */
.chat-area {
  background: white;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.chat-header {
  padding: 16px 32px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  flex: 0 0 auto;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.kb-tag {
  border-radius: 6px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.retrieval-config {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.config-label {
  font-weight: 500;
}

.chunk-selector {
  width: 80px;
}

.chunk-selector :deep(.ant-select-selector) {
  border-radius: 6px;
}

.action-btn {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.action-btn.primary {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border: none;
  color: white;
}

.action-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

/* 消息区域样式优化 */
.messages-container {
  flex: 1 1 auto;
  min-height: 0;
  padding: 24px 32px;
  overflow: auto;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.empty-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 24px;
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon :deep(svg) {
  font-size: 32px;
  color: #94a3b8;
}

.empty-tips {
  text-align: center;
}

.empty-tips p {
  margin: 0;
  color: #64748b;
}

.tip-small {
  font-size: 12px;
  margin-top: 8px !important;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 900px;
  margin: 0 auto;
}

/* —— 移动端抽屉化侧栏支持 —— */
@media (max-width: 992px) {
  .kbq-sider { display: none !important; }
  .chat-header .mobile-menu-btn { display: inline-flex; margin-right: 8px; }
  /* 小屏隐藏右侧预览侧栏，避免压缩消息区 */
  .preview-sider { display: none !important; }
}

.message {
  display: flex;
  gap: 16px;
  min-width: 0;
  animation: fadeInUp 0.3s ease;
}

.message--user {
  flex-direction: row-reverse;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-user,
.avatar-ai {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.avatar-user {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  color: white;
}

.avatar-ai {
  background: linear-gradient(135deg, #ff6b6b 0%, #ffa726 100%);
  color: white;
}

.message-content {
  max-width: 70%;
  min-width: 0;
}

.message-bubble {
  padding: 16px 20px;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  position: relative;
  transition: all 0.3s ease;
}

.message-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.bubble--user {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble--assistant {
  background: white;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  border: 1px solid #f1f5f9;
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
}

.message-text :deep(pre) {
  background: rgba(255, 255, 255, 0.1);
  padding: 12px;
  border-radius: 8px;
  overflow: auto;
  margin: 12px 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.message-text :deep(code) {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.9em;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.bubble--assistant .message-text :deep(pre) {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.bubble--assistant .message-text :deep(code) {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #dc2626;
}

.sources-section {
  margin-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding-top: 12px;
}

.bubble--assistant .sources-section {
  border-top-color: #e2e8f0;
}

.sources-header :deep(.ant-collapse-header) {
  padding: 8px 0 !important;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.bubble--assistant .sources-header :deep(.ant-collapse-header) {
  color: #64748b;
}

.source-item {
  padding: 6px 0 !important;
  font-size: 13px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.bubble--assistant .source-item {
  border-bottom-color: #f1f5f9;
}

.source-name {
  margin-left: 8px;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  transition: color 0.3s ease;
}

.source-name:hover {
  color: white;
  text-decoration: underline;
}

.bubble--assistant .source-name {
  color: #475569;
}

.bubble--assistant .source-name:hover {
  color: #1890ff;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  animation: fadeInUp 0.3s ease;
}

.typing-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff6b6b 0%, #ffa726 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.typing-bubble {
  background: white;
  padding: 16px 20px;
  border-radius: 20px;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typingBounce {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
}

/* 输入区域样式优化 */
.input-container {
  padding: 20px 32px;
  border-top: 1px solid #f0f0f0;
  background: white;
  flex: 0 0 auto;
}

.input-box {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  border-radius: 24px;
  min-width: 0;
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
}

.chat-input:focus-within {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.chat-input :deep(textarea) {
  border-radius: 24px;
  padding: 12px 20px;
  font-size: 14px;
  line-height: 1.5;
  border: none;
  resize: none;
}

.chat-input :deep(textarea:focus) {
  box-shadow: none;
}

.send-btn {
  border-radius: 50%;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
  transition: all 0.3s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px) scale(1.05);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
}

.send-btn:disabled {
  background: #d1d5db;
  box-shadow: none;
  transform: none;
}

.input-tips {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
}

/* 预览侧栏样式优化 */
.preview-sider {
  background: white;
  border-left: 1px solid #e1e8ed;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: white;
  flex: 0 0 auto;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1f2937;
}

.preview-title :deep(svg) {
  color: #1890ff;
}

.viewer-tag {
  border-radius: 4px;
  font-size: 11px;
  height: 20px;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.action-link {
  color: #1890ff;
  font-weight: 500;
}

.close-btn {
  color: #6b7280;
}

.close-btn:hover {
  color: #ef4444;
}

.preview-body {
  flex: 1 1 auto;
  min-height: 0;
  background: #f8fafc;
  overflow: auto;
  padding: 0;
}

.preview-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  gap: 16px;
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.5;
}

.preview-content {
  height: 100%;
  background: white;
}

.image-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.image-wrapper img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.md-wrapper,
.html-wrapper {
  padding: 24px;
  line-height: 1.6;
}

.code-block {
  background: #1f2937;
  color: #e5e7eb;
  padding: 24px;
  margin: 0;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.excel-wrapper {
  background: white;
}

.docx-wrapper {
  background: white;
  padding: 24px;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: 0;
  background: white;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .rag-chat-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100% !important;
    max-height: 40vh;
  }
  
  .messages-list {
    max-width: 100%;
  }
  
  .message-content {
    max-width: 85%;
  }
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
